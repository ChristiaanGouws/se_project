"""Configuration and Security Module for IBM Quantum API Token handling (UC4)."""

import re
from typing import Any, Dict, Optional, Tuple
from cryptography.fernet import Fernet


class AuthenticationError(Exception):
    """Raised when an API token is invalid, missing, or fails authentication."""
    pass


class TokenManager:
    """Securely validates, encrypts, and stores IBM Quantum API tokens for session use."""

    def __init__(self, encryption_key: Optional[bytes] = None) -> None:
        self._key = encryption_key or Fernet.generate_key()
        self._cipher = Fernet(self._key)
        self._encrypted_token: Optional[bytes] = None
        self._masked_token: Optional[str] = None

    @staticmethod
    def validate_token_format(token: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate token format: checks non-empty, minimum length (32 chars), and valid characters."""
        if token is None or not token.strip():
            return False, "AuthenticationError: API token cannot be empty or null."

        stripped = token.strip()
        if len(stripped) < 32:
            return (
                False,
                f"AuthenticationError: Malformed API token. Length is {len(stripped)} chars; minimum required is 32 chars.",
            )

        # IBM Quantum tokens are alphanumeric hex or base64url strings (no whitespace or control chars)
        if not re.match(r"^[A-Za-z0-9_\-]+$", stripped):
            return (
                False,
                "AuthenticationError: Malformed API token. Token contains invalid characters.",
            )

        return True, None

    def configure_token(self, token: Optional[str], raise_on_error: bool = False) -> Dict[str, Any]:
        """Validate and encrypt the token for session storage. Rejects invalid tokens without storing."""
        is_valid, error_msg = self.validate_token_format(token)
        if not is_valid:
            # Wipe any previous token and never store plaintext
            self._encrypted_token = None
            self._masked_token = None
            if raise_on_error:
                raise AuthenticationError(error_msg)
            return {
                "status": "error",
                "authenticated": False,
                "error": error_msg,
                "message": error_msg,
            }

        clean_token = token.strip()
        # Encrypt token using symmetric AES Fernet cipher
        self._encrypted_token = self._cipher.encrypt(clean_token.encode("utf-8"))
        self._masked_token = clean_token[:4] + "***" + clean_token[-4:]

        return {
            "status": "success",
            "authenticated": True,
            "masked_token": self._masked_token,
            "encrypted_token": self._encrypted_token.decode("utf-8"),
            "message": "Token successfully validated and encrypted for session use.",
        }

    def get_session_token(self) -> Optional[str]:
        """Decrypt and return the stored session token for QPU dispatch."""
        if self._encrypted_token is None:
            return None
        return self._cipher.decrypt(self._encrypted_token).decode("utf-8")

    @property
    def is_authenticated(self) -> bool:
        """Check if a validated token is present in the session."""
        return self._encrypted_token is not None

    @property
    def masked_token(self) -> Optional[str]:
        """Return masked representation for display without exposing secrets."""
        return self._masked_token

    def clear_token(self) -> None:
        """Purge encrypted credentials from session memory."""
        self._encrypted_token = None
        self._masked_token = None

    def check_backend_availability(
        self, token: Optional[str] = None, backend_name: Optional[str] = None
    ) -> bool:
        """Verify QPU backend availability with IBM Quantum Cloud."""
        active_token = token or self.get_session_token()
        if not active_token:
            return False
        is_valid, _ = self.validate_token_format(active_token)
        if not is_valid:
            return False

        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            service = QiskitRuntimeService(token=active_token)
            if backend_name:
                backend = service.backend(backend_name)
                return backend.status().operational
            backends = service.backends(operational=True, simulator=False)
            return len(backends) > 0
        except Exception:
            # If network or credentials reject connection
            return False

    def __repr__(self) -> str:
        status = f"authenticated ({self._masked_token})" if self.is_authenticated else "unauthenticated"
        return f"<TokenManager status={status}>"
