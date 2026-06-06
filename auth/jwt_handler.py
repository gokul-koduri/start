"""JWT token creation and validation."""

import datetime
import json
import logging
from typing import Any, Dict

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

from config import load_config

_logger = logging.getLogger(__name__)


class JWTHandler:
    """Handle JWT token creation and validation."""

    def __init__(self, config: dict | None = None):
        """Initialize JWT handler with configuration.

        Config options:
            jwt_secret: Secret key for signing (required)
            jwt_expiry_hours: Token expiry in hours (default: 24)
        """
        self.config = config or {}
        full_config = load_config()
        auth_config = full_config.get("auth", {})

        self.secret = self.config.get(
            "jwt_secret",
            auth_config.get("jwt_secret", "change-me-in-production")
        )
        self.expiry_hours = self.config.get(
            "jwt_expiry_hours",
            auth_config.get("jwt_expiry_hours", 24)
        )

        if not HAS_JWT:
            _logger.warning("PyJWT not installed — JWT tokens will use mock implementation")

    def create_token(self, payload: Dict[str, Any]) -> str:
        """Create a JWT token with the given payload.

        Args:
            payload: Dictionary containing user claims (e.g., user_id, role)

        Returns:
            JWT token string
        """
        # Add expiry claim
        payload = payload.copy()
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=self.expiry_hours)
        payload["exp"] = expiry
        payload["iat"] = datetime.datetime.now(datetime.timezone.utc)

        if HAS_JWT:
            token = jwt.encode(payload, self.secret, algorithm="HS256")
            return token
        else:
            # Mock implementation for testing without pyjwt
            mock_payload = {**payload, "exp": expiry.timestamp(), "iat": datetime.datetime.now(datetime.timezone.utc).timestamp()}
            return f"mock_token_{json.dumps(mock_payload)}"

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return the payload.

        Args:
            token: JWT token string

        Returns:
            Dictionary with token payload

        Raises:
            ValueError: If token is invalid or expired
        """
        if HAS_JWT:
            try:
                payload = jwt.decode(token, self.secret, algorithms=["HS256"])
                return payload
            except jwt.ExpiredSignatureError:
                raise ValueError("Token has expired")
            except jwt.InvalidTokenError as e:
                raise ValueError(f"Invalid token: {e}")
        else:
            # Mock implementation
            if not token.startswith("mock_token_"):
                raise ValueError("Invalid token format")
            try:
                mock_payload = json.loads(token[11:])
                # Check expiry
                if mock_payload.get("exp", 0) < datetime.datetime.now(datetime.timezone.utc).timestamp():
                    raise ValueError("Token has expired")
                # Remove timestamp fields for consistency with real JWT
                return {k: v for k, v in mock_payload.items() if k not in ["exp", "iat"]}
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Invalid token: {e}")

    def refresh_token(self, token: str) -> str:
        """Refresh an existing token, extending its expiry.

        Args:
            token: Existing JWT token

        Returns:
            New JWT token with extended expiry
        """
        payload = self.validate_token(token)
        # Remove timestamp claims so they can be regenerated
        payload.pop("exp", None)
        payload.pop("iat", None)
        return self.create_token(payload)
