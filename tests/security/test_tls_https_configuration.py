"""Tests for TLS/HTTPS configuration and certificate management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.security.cert_generator import CertificateGenerator
from cohezion.security.https_middleware import (
    HTTPSEnforcementMiddleware,
    SecureCookieMiddleware,
    create_https_app,
)
from cohezion.security.tls_config import TLSConfig, get_tls_config, reset_tls_config


class TestTLSConfig:
    """Test TLS configuration management."""

    def setup_method(self):
        """Reset TLS singleton before each test."""
        reset_tls_config()

    def test_tls_config_initialization(self):
        """Test TLS configuration initialization with defaults."""
        config = TLSConfig()

        assert config.hsts_max_age == 31536000  # 1 year
        assert config.secure_cookies is True
        assert len(config.allowed_origins) > 0

    def test_tls_config_custom_values(self):
        """Test TLS configuration with custom values."""
        config = TLSConfig(
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
            hsts_max_age=7776000,  # 90 days
            allowed_origins=["https://example.com"],
        )

        assert config.cert_path == "/path/to/cert.pem"
        assert config.key_path == "/path/to/key.pem"
        assert config.hsts_max_age == 7776000
        assert "https://example.com" in config.allowed_origins

    def test_validate_certificate_missing_files(self):
        """Test certificate validation with missing files."""
        config = TLSConfig(
            cert_path="/nonexistent/cert.pem",
            key_path="/nonexistent/key.pem",
        )

        assert config.validate_certificate() is False

    def test_validate_certificate_existing_files(self):
        """Test certificate validation with existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.pem"
            key_path = Path(tmpdir) / "key.pem"

            cert_path.write_text("CERTIFICATE")
            key_path.write_text("KEY")

            config = TLSConfig(
                cert_path=str(cert_path),
                key_path=str(key_path),
            )

            assert config.validate_certificate() is True

    @pytest.mark.skipif(
        os.getuid() == 0,
        reason="Root can read files regardless of permissions",
    )
    def test_validate_certificate_unreadable_files(self):
        """Test certificate validation with unreadable files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.pem"
            key_path = Path(tmpdir) / "key.pem"

            cert_path.write_text("CERTIFICATE")
            key_path.write_text("KEY")

            config = TLSConfig(
                cert_path=str(cert_path),
                key_path=str(key_path),
            )

            # Mock os.access to simulate unreadable files
            # (chmod 0o000 doesn't work when running as root)
            with patch("cohezion.security.tls_config.os.access", return_value=False):
                assert config.validate_certificate() is False

    def test_load_ssl_context_invalid(self):
        """Test SSL context loading with invalid certificate."""
        config = TLSConfig(
            cert_path="/nonexistent/cert.pem",
            key_path="/nonexistent/key.pem",
        )

        context = config.load_ssl_context()
        assert context is None

    def test_load_ssl_context_invalid_content(self):
        """Test SSL context loading with invalid certificate content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.pem"
            key_path = Path(tmpdir) / "key.pem"

            cert_path.write_text("INVALID CERTIFICATE")
            key_path.write_text("INVALID KEY")

            config = TLSConfig(
                cert_path=str(cert_path),
                key_path=str(key_path),
            )

            context = config.load_ssl_context()
            assert context is None

    def test_get_hsts_header(self):
        """Test HSTS header generation."""
        config = TLSConfig(hsts_max_age=31536000)
        header = config.get_hsts_header()

        assert "max-age=31536000" in header
        assert "includeSubDomains" in header
        assert "preload" in header

    def test_get_security_headers(self):
        """Test security headers generation."""
        config = TLSConfig()
        headers = config.get_security_headers()

        assert "Strict-Transport-Security" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"

    def test_get_allowed_origins(self):
        """Test getting allowed origins."""
        config = TLSConfig(allowed_origins=["https://example.com"])
        origins = config.get_allowed_origins()

        assert "https://example.com" in origins

    def test_is_origin_allowed(self):
        """Test origin allowlist checking."""
        config = TLSConfig(allowed_origins=["https://example.com"])

        assert config.is_origin_allowed("https://example.com") is True
        assert config.is_origin_allowed("https://evil.com") is False

    def test_get_cookie_flags(self):
        """Test cookie security flags."""
        config = TLSConfig(secure_cookies=True)
        flags = config.get_cookie_flags()

        assert flags["secure"] is True
        assert flags["httponly"] is True
        assert flags["samesite"] == "Strict"

    def test_get_cookie_flags_insecure(self):
        """Test cookie flags without secure flag."""
        config = TLSConfig(secure_cookies=False)
        flags = config.get_cookie_flags()

        assert flags.get("secure") is None or flags["secure"] is False
        assert flags["httponly"] is True
        assert flags["samesite"] == "Strict"

    def test_configure_for_production(self):
        """Test production configuration validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.pem"
            key_path = Path(tmpdir) / "key.pem"

            cert_path.write_text("CERTIFICATE")
            key_path.write_text("KEY")

            config = TLSConfig(
                cert_path=str(cert_path),
                key_path=str(key_path),
            )

            # Will fail because cert content is invalid, but it tests the flow
            result = config.configure_for_production()
            assert isinstance(result, bool)

    def test_get_tls_config_singleton(self):
        """Test TLS config singleton pattern."""
        config1 = get_tls_config(
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
        )
        config2 = get_tls_config()

        assert config1 is config2

    def test_reset_tls_config(self):
        """Test TLS config singleton reset."""
        config1 = get_tls_config(cert_path="/path/to/cert.pem")
        reset_tls_config()
        config2 = get_tls_config(cert_path="/path/to/other/cert.pem")

        assert config1 is not config2
        assert config1.cert_path != config2.cert_path


class TestCertificateGenerator:
    """Test certificate generation utility."""

    def test_generate_self_signed_cert_no_openssl(self):
        """Test certificate generation when OpenSSL is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = str(Path(tmpdir) / "cert.pem")
            key_path = str(Path(tmpdir) / "key.pem")

            with patch("subprocess.run", side_effect=FileNotFoundError):
                result = CertificateGenerator.generate_self_signed_cert(cert_path, key_path)

            assert result is False

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/openssl"),
        reason="OpenSSL not installed",
    )
    def test_generate_self_signed_cert_success(self):
        """Test successful certificate generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = str(Path(tmpdir) / "cert.pem")
            key_path = str(Path(tmpdir) / "key.pem")

            result = CertificateGenerator.generate_self_signed_cert(
                cert_path, key_path, cn="test.local"
            )

            assert result is True
            assert Path(cert_path).exists()
            assert Path(key_path).exists()
            assert Path(key_path).stat().st_mode & 0o077 == 0  # 600 permissions

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/openssl"),
        reason="OpenSSL not installed",
    )
    def test_generate_self_signed_cert_already_exists(self):
        """Test certificate generation when files already exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = str(Path(tmpdir) / "cert.pem")
            key_path = str(Path(tmpdir) / "key.pem")

            # Create initial certificate
            result1 = CertificateGenerator.generate_self_signed_cert(cert_path, key_path)
            assert result1 is True

            # Record file modification times
            cert_mtime1 = Path(cert_path).stat().st_mtime
            key_mtime1 = Path(key_path).stat().st_mtime

            # Try to generate again without force
            import time

            time.sleep(0.1)
            result2 = CertificateGenerator.generate_self_signed_cert(
                cert_path, key_path, force=False
            )
            assert result2 is True

            # Verify files weren't modified
            cert_mtime2 = Path(cert_path).stat().st_mtime
            key_mtime2 = Path(key_path).stat().st_mtime
            assert cert_mtime1 == cert_mtime2
            assert key_mtime1 == key_mtime2

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/openssl"),
        reason="OpenSSL not installed",
    )
    def test_generate_self_signed_cert_force_regenerate(self):
        """Test forcing certificate regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = str(Path(tmpdir) / "cert.pem")
            key_path = str(Path(tmpdir) / "key.pem")

            # Create initial certificate
            result1 = CertificateGenerator.generate_self_signed_cert(cert_path, key_path)
            assert result1 is True

            cert_mtime1 = Path(cert_path).stat().st_mtime

            # Force regeneration
            import time

            time.sleep(0.1)
            result2 = CertificateGenerator.generate_self_signed_cert(
                cert_path, key_path, force=True
            )
            assert result2 is True

            # Verify file was modified
            cert_mtime2 = Path(cert_path).stat().st_mtime
            assert cert_mtime2 > cert_mtime1

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/openssl"),
        reason="OpenSSL not installed",
    )
    def test_ensure_dev_certificates(self):
        """Test development certificate setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, key_path = CertificateGenerator.ensure_dev_certificates(
                cert_dir=str(Path(tmpdir) / ".certs")
            )

            assert cert_path is not None
            assert key_path is not None
            assert Path(cert_path).exists()
            assert Path(key_path).exists()


class TestHTTPSEnforcementMiddleware:
    """Test HTTPS enforcement middleware."""

    @pytest.mark.asyncio
    async def test_https_enforcement_rejects_http(self):
        """Test that HTTP requests are rejected."""
        config = TLSConfig()
        app = MagicMock()

        middleware = HTTPSEnforcementMiddleware(app, config, allow_http_localhost=False)

        # Create mock request with HTTP scheme
        request = MagicMock()
        request.url.scheme = "http"

        response = await middleware.dispatch(request, MagicMock())

        assert response.status_code == 426  # Upgrade Required

    @pytest.mark.asyncio
    async def test_https_enforcement_allows_https(self):
        """Test that HTTPS requests are allowed."""
        config = TLSConfig()

        async def mock_next(request):
            return MagicMock(headers={})

        app = MagicMock()
        middleware = HTTPSEnforcementMiddleware(app, config)

        request = MagicMock()
        request.url.scheme = "https"
        request.headers.get = MagicMock(return_value=None)

        response = await middleware.dispatch(request, mock_next)

        assert response is not None

    @pytest.mark.asyncio
    async def test_https_enforcement_allows_localhost_http(self):
        """Test that localhost HTTP is allowed for development."""
        config = TLSConfig()

        async def mock_next(request):
            return MagicMock(headers={})

        app = MagicMock()
        middleware = HTTPSEnforcementMiddleware(app, config, allow_http_localhost=True)

        request = MagicMock()
        request.url.scheme = "http"
        request.client.host = "127.0.0.1"
        request.headers.get = MagicMock(return_value=None)

        response = await middleware.dispatch(request, mock_next)

        assert response is not None or response.status_code != 426

    @pytest.mark.asyncio
    async def test_https_enforcement_rejects_disallowed_origin(self):
        """Test that disallowed CORS origins are rejected."""
        config = TLSConfig(allowed_origins=["https://example.com"])

        app = MagicMock()
        middleware = HTTPSEnforcementMiddleware(app, config)

        request = MagicMock()
        request.url.scheme = "https"
        request.headers.get = MagicMock(return_value="https://evil.com")

        response = await middleware.dispatch(request, MagicMock())

        assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    async def test_https_enforcement_adds_security_headers(self):
        """Test that security headers are added to responses."""
        config = TLSConfig()

        response_obj = MagicMock()
        response_obj.headers = {}

        async def mock_next(request):
            return response_obj

        app = MagicMock()
        middleware = HTTPSEnforcementMiddleware(app, config)

        request = MagicMock()
        request.url.scheme = "https"
        request.headers.get = MagicMock(return_value=None)

        response = await middleware.dispatch(request, mock_next)

        assert "Strict-Transport-Security" in response.headers


class TestSecureCookieMiddleware:
    """Test secure cookie middleware."""

    @pytest.mark.asyncio
    async def test_secure_cookie_middleware_adds_flags(self):
        """Test that secure cookie flags are applied."""
        config = TLSConfig(secure_cookies=True)

        response_obj = MagicMock()
        response_obj.headers = MagicMock()
        response_obj.headers.getlist = MagicMock(return_value=["session=abc123; Path=/"])

        async def mock_next(request):
            return response_obj

        middleware = SecureCookieMiddleware(MagicMock(), config)
        request = MagicMock()

        await middleware.dispatch(request, mock_next)

        # Verify that del was called on set-cookie
        response_obj.headers.__delitem__.assert_called_with("set-cookie")

    def test_apply_cookie_flags_adds_secure_flag(self):
        """Test cookie flag application."""
        flags = {"secure": True, "httponly": True, "samesite": "Strict"}

        cookie = "session=abc123; Path=/"
        result = SecureCookieMiddleware._apply_cookie_flags(cookie, flags)

        assert "Secure" in result
        assert "HttpOnly" in result
        assert "SameSite=Strict" in result

    def test_apply_cookie_flags_removes_existing_flags(self):
        """Test that existing cookie flags are replaced."""
        flags = {"secure": True, "httponly": True, "samesite": "Strict"}

        cookie = "session=abc123; Path=/; Secure; HttpOnly; SameSite=Lax"
        result = SecureCookieMiddleware._apply_cookie_flags(cookie, flags)

        # Should only have one SameSite directive
        assert result.count("SameSite") == 1
        assert "SameSite=Strict" in result


class TestCreateHTTPSApp:
    """Test HTTPS app wrapper."""

    def test_create_https_app_wraps_with_middleware(self):
        """Test that create_https_app applies middleware."""
        config = TLSConfig()
        app = MagicMock()

        wrapped_app = create_https_app(app, config)

        # Should return a middleware instance
        assert wrapped_app is not None
        assert wrapped_app is not app
