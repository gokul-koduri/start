"""API key generation, hashing, and validation."""

import hashlib
import secrets

KEY_PREFIX = "oip_live_"
KEY_LENGTH = 32


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (raw_key, key_prefix, key_hash)
        - raw_key: The full key shown to user once (e.g., "oip_live_abc123...")
        - key_prefix: First 8 chars for display/identification
        - key_hash: SHA-256 hash for storage
    """
    raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(KEY_LENGTH)}"
    key_prefix = raw_key[:8]
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256.

    Args:
        raw_key: The full API key string

    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def validate_api_key_format(key: str) -> bool:
    """Validate the format of an API key string.

    Args:
        key: API key to validate

    Returns:
        True if format is valid
    """
    if not key or not isinstance(key, str):
        return False
    return key.startswith(KEY_PREFIX) and len(key) > len(KEY_PREFIX)
