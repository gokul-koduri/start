"""Password hashing and verification using bcrypt."""

import logging

_logger = logging.getLogger(__name__)

try:
    import bcrypt

    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    _logger.warning(
        "bcrypt not installed — password hashing will use mock implementation"
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain-text password string

    Returns:
        Bcrypt hash as a string
    """
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    else:
        # Mock implementation for testing
        import hashlib

        return f"mock_bcrypt_{hashlib.sha256(password.encode()).hexdigest()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash.

    Args:
        plain_password: Plain-text password to verify
        hashed_password: Stored bcrypt hash

    Returns:
        True if password matches, False otherwise
    """
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False
    else:
        # Mock verification
        import hashlib

        expected = f"mock_bcrypt_{hashlib.sha256(plain_password.encode()).hexdigest()}"
        return expected == hashed_password


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets minimum strength requirements.

    Requirements: 8+ chars, at least one uppercase, one lowercase, one digit.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""
