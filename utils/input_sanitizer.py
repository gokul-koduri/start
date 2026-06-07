"""Input sanitization utilities for user-facing endpoints."""

import html
import logging
import re
from typing import Any

_logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 10000
MAX_EMAIL_LENGTH = 255

_DANGEROUS_PATTERNS = [
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]


def sanitize_string(value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Sanitize a string input.

    Strips whitespace, removes null bytes, escapes HTML entities,
    enforces maximum length, and rejects dangerous patterns.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    cleaned = value.strip()
    cleaned = cleaned.replace("\x00", "")

    if len(cleaned) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")

    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError("Input contains potentially dangerous content")

    cleaned = html.escape(cleaned, quote=True)
    return cleaned


def sanitize_dict(data: dict, max_length: int = MAX_INPUT_LENGTH) -> dict:
    """Recursively sanitize all string values in a dictionary."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            try:
                sanitized[key] = sanitize_string(value, max_length)
            except ValueError as e:
                _logger.warning("Sanitization rejected field '%s': %s", key, e)
                sanitized[key] = html.escape(value[:max_length], quote=True)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_length)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_string(item, max_length) if isinstance(item, str)
                else sanitize_dict(item, max_length) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def sanitize_email(email: str) -> str:
    """Sanitize and validate an email address."""
    if not email or not isinstance(email, str):
        raise ValueError("Email is required")

    cleaned = email.strip().lower()

    if len(cleaned) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email exceeds maximum length of {MAX_EMAIL_LENGTH}")

    email_pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(cleaned):
        raise ValueError("Invalid email format")

    return cleaned
