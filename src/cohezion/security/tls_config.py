"""TLS/HTTPS configuration and enforcement for secure communications."""

import logging
import os
import ssl
from pathlib import Path


logger = logging.getLogger(__name__)


class TLSConfig:
    """
    TLS configuration manager for production-grade HTTPS setup.

    Supports:
    - SSL certificate loading (cert + key files)
    - HSTS (HTTP Strict-Transport-Security) header generation
    - Secure cookie flag enforcement
    - CORS origin restriction
    - TLS version enforcement (TLS 1.2+)
    """

    def __init__(
        self,
        cert_path: str | None = None,
        key_path: str | None = None,
        hsts_max_age: int = 31536000,  # 1 year
        secure_cookies: bool = True,
        allowed_origins: list[str] | None = None,
    ):
        """
        Initialize TLS configuration.

        Args:
            cert_path: Path to SSL certificate file
            key_path: Path to SSL private key file
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            secure_cookies: Whether to set SECURE flag on cookies
            allowed_origins: List of allowed CORS origins (default: localhost only)
        """
        self.cert_path = cert_path or os.environ.get("TLS_CERT_PATH")
        self.key_path = key_path or os.environ.get("TLS_KEY_PATH")
        self.hsts_max_age = hsts_max_age
        self.secure_cookies = secure_cookies
        self.allowed_origins = allowed_origins or [
            "https://localhost",
            "https://127.0.0.1",
        ]

    def validate_certificate(self) -> bool:
        """
        Validate that certificate and key files exist and are readable.

        Returns:
            True if valid, False otherwise
        """
        if not self.cert_path or not self.key_path:
            logger.warning("TLS certificate paths not configured")
            return False

        cert_file = Path(self.cert_path)
        key_file = Path(self.key_path)

        if not cert_file.exists():
            logger.error("Certificate file not found: %s", self.cert_path)
            return False

        if not key_file.exists():
            logger.error("Key file not found: %s", self.key_path)
            return False

        if not os.access(cert_file, os.R_OK):
            logger.error("Certificate file not readable: %s", self.cert_path)
            return False

        if not os.access(key_file, os.R_OK):
            logger.error("Key file not readable: %s", self.key_path)
            return False

        return True

    def load_ssl_context(self) -> ssl.SSLContext | None:
        """
        Load and configure SSL context for HTTPS.

        Returns:
            Configured ssl.SSLContext or None if validation fails
        """
        if not self.validate_certificate():
            return None

        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.cert_path, self.key_path)

            # Enforce strong TLS versions (TLS 1.2+)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1

            logger.info("SSL context loaded successfully")
            return context
        except OSError as e:
            logger.error("Failed to load SSL context: %s", e)
            return None

    def get_hsts_header(self) -> str:
        """
        Generate HSTS (HTTP Strict-Transport-Security) header value.

        Returns:
            HSTS header value
        """
        value = f"max-age={self.hsts_max_age}"
        value += "; includeSubDomains"
        value += "; preload"
        return value

    def get_security_headers(self) -> dict[str, str]:
        """
        Get all security headers for HTTPS enforcement.

        Returns:
            Dictionary of security headers
        """
        return {
            "Strict-Transport-Security": self.get_hsts_header(),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    def get_allowed_origins(self) -> list[str]:
        """
        Get list of allowed CORS origins.

        Returns:
            List of allowed origins
        """
        return self.allowed_origins

    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin is allowed.

        Args:
            origin: Origin header value to check

        Returns:
            True if origin is allowed
        """
        return origin in self.allowed_origins

    def get_cookie_flags(self) -> dict[str, bool]:
        """
        Get cookie security flags.

        Returns:
            Dictionary of cookie flags
        """
        flags = {
            "httponly": True,  # Prevent JavaScript access
            "samesite": "Strict",  # CSRF protection
        }

        if self.secure_cookies:
            flags["secure"] = True  # HTTPS only

        return flags

    def configure_for_production(self) -> bool:
        """
        Perform full production security configuration.

        Returns:
            True if all checks pass, False otherwise
        """
        checks = [
            ("Certificate validation", self.validate_certificate()),
            ("SSL context", self.load_ssl_context() is not None),
        ]

        all_passed = True
        for check_name, result in checks:
            status = "PASS" if result else "FAIL"
            logger.info("Production security check [%s]: %s", check_name, status)
            if not result:
                all_passed = False

        return all_passed


# Singleton instance
_tls_config: TLSConfig | None = None


def get_tls_config(
    cert_path: str | None = None,
    key_path: str | None = None,
    **kwargs,
) -> TLSConfig:
    """
    Get or create TLS configuration singleton.

    Args:
        cert_path: Optional certificate path (uses env var if not provided)
        key_path: Optional key path (uses env var if not provided)
        **kwargs: Additional arguments for TLSConfig constructor

    Returns:
        TLSConfig instance
    """
    global _tls_config
    if _tls_config is None:
        _tls_config = TLSConfig(cert_path=cert_path, key_path=key_path, **kwargs)
    return _tls_config


def reset_tls_config() -> None:
    """Reset the TLS configuration singleton (for testing)."""
    global _tls_config
    _tls_config = None
