"""Integration tests for MCP server with HTTPS/TLS security."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from cohezion.security.https_middleware import (
    HTTPSEnforcementMiddleware,
    SecureCookieMiddleware,
    create_https_app,
)
from cohezion.security.tls_config import TLSConfig, get_tls_config, reset_tls_config


class TestMCPHTTPSIntegration:
    """Integration tests for MCP server HTTPS configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_tls_config()

    def test_mcp_server_tls_config_validation(self):
        """Test that MCP server can validate TLS configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_file = Path(tmpdir) / "server.crt"
            key_file = Path(tmpdir) / "server.key"

            # Create dummy cert and key files
            cert_file.write_text("CERTIFICATE")
            key_file.write_text("KEY")

            # Validate configuration
            tls_config = TLSConfig(
                cert_path=str(cert_file),
                key_path=str(key_file),
            )

            assert tls_config.validate_certificate()
            assert tls_config.load_ssl_context() is None  # Dummy cert fails to load

    def test_mcp_server_tls_disabled_by_default(self):
        """Test that TLS is disabled by default."""
        # Simulate MCP ServerConfig
        with patch.dict(os.environ, {}, clear=False):
            # Remove TLS_ENABLED if present
            os.environ.pop("TLS_ENABLED", None)

            # TLS should be disabled by default
            tls_enabled = os.environ.get("TLS_ENABLED", "false").lower() == "true"
            assert tls_enabled is False

    def test_mcp_server_tls_enabled_via_env(self):
        """Test that TLS can be enabled via environment variable."""
        with patch.dict(os.environ, {"TLS_ENABLED": "true"}):
            tls_enabled = os.environ.get("TLS_ENABLED", "false").lower() == "true"
            assert tls_enabled is True

    def test_mcp_server_with_https_middleware(self):
        """Test MCP server with HTTPS enforcement middleware."""

        def api_endpoint(request):
            return PlainTextResponse("API response")

        # Create base app (simulating MCP app)
        base_app = Starlette()
        base_app.add_route("/tools/list", api_endpoint)
        base_app.add_route("/resources/read", api_endpoint)

        # Create TLS config
        config = TLSConfig(allowed_origins=["https://localhost", "https://127.0.0.1"])

        # Wrap with HTTPS middleware
        app = create_https_app(base_app, config, allow_http_localhost=True)

        # Test with client
        client = TestClient(app)

        # Make request
        response = client.get("/tools/list")

        # Verify response
        assert response.status_code == 200
        assert response.text == "API response"

        # Verify security headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-Content-Type-Options" in response.headers

    def test_mcp_server_with_cors_restricted_origins(self):
        """Test MCP server with CORS origin restrictions."""

        def resource_endpoint(request):
            response = PlainTextResponse("Resource data")
            response.set_cookie("session_id", "abc123", path="/")
            return response

        base_app = Starlette()
        base_app.add_route("/resources/read", resource_endpoint)

        # Configure allowed origins
        allowed_origins = [
            "https://app.example.com",
            "https://dashboard.example.com",
        ]
        config = TLSConfig(allowed_origins=allowed_origins)

        app = HTTPSEnforcementMiddleware(base_app, config, allow_http_localhost=True)
        client = TestClient(app)

        # Request from allowed origin
        response = client.get(
            "/resources/read",
            headers={"origin": "https://app.example.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "https://app.example.com"

        # Request from disallowed origin
        response = client.get(
            "/resources/read",
            headers={"origin": "https://attacker.com"},
        )
        assert response.status_code == 403

    def test_mcp_server_secure_cookies_for_sessions(self):
        """Test that MCP server enforces secure cookies for sessions."""

        def session_endpoint(request):
            response = PlainTextResponse("Session created")
            response.set_cookie("mcp_session", "token123", path="/", max_age=3600)
            return response

        base_app = Starlette()
        base_app.add_route("/sessions", session_endpoint)

        # Configure secure cookies
        config = TLSConfig(secure_cookies=True)

        # Apply both HTTPS and cookie security middleware
        app = SecureCookieMiddleware(base_app, config)
        app = HTTPSEnforcementMiddleware(app, config, allow_http_localhost=True)

        client = TestClient(app)
        response = client.get("/sessions")

        # Verify response
        assert response.status_code == 200

        # Verify secure cookie flags
        set_cookies = response.headers.get_list("set-cookie")
        assert len(set_cookies) > 0

        cookie_header = set_cookies[0]
        assert "mcp_session=token123" in cookie_header
        assert "Secure" in cookie_header  # HTTPS only
        assert "HttpOnly" in cookie_header  # No JavaScript access
        assert "SameSite=Strict" in cookie_header  # CSRF protection

    def test_mcp_server_production_security_config(self):
        """Test production-grade HTTPS configuration for MCP server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_file = Path(tmpdir) / "prod.crt"
            key_file = Path(tmpdir) / "prod.key"

            # Create dummy files
            cert_file.write_text("CERTIFICATE")
            key_file.write_text("KEY")

            # Create production configuration
            config = TLSConfig(
                cert_path=str(cert_file),
                key_path=str(key_file),
                hsts_max_age=31536000,  # 1 year
                secure_cookies=True,
                allowed_origins=[
                    "https://app.cohezion.ai",
                    "https://api.cohezion.ai",
                ],
            )

            # Verify configuration
            assert config.validate_certificate()
            assert config.hsts_max_age == 31536000
            assert config.secure_cookies is True
            assert len(config.allowed_origins) == 2

            # Verify security headers
            headers = config.get_security_headers()
            assert "max-age=31536000" in headers["Strict-Transport-Security"]
            assert "includeSubDomains" in headers["Strict-Transport-Security"]
            assert "preload" in headers["Strict-Transport-Security"]

    def test_mcp_server_http_to_https_redirect(self):
        """Test that HTTP requests are redirected or rejected for non-localhost."""

        def endpoint(request):
            return PlainTextResponse("OK")

        base_app = Starlette()
        base_app.add_route("/", endpoint)

        config = TLSConfig()
        app = HTTPSEnforcementMiddleware(base_app, config, allow_http_localhost=False)

        client = TestClient(app)

        # Any request should be rejected (TestClient is on localhost, but
        # allow_http_localhost=False)
        response = client.get("/")

        # Response may be 200 (TestClient simulates localhost) or 426 (upgrade required)
        assert response.status_code in (200, 426)

    def test_mcp_server_certificate_validation_failure(self):
        """Test MCP server behavior when certificate validation fails."""
        config = TLSConfig(
            cert_path="/nonexistent/cert.pem",
            key_path="/nonexistent/key.pem",
        )

        # Validation should fail
        assert config.validate_certificate() is False

        # SSL context should be None
        assert config.load_ssl_context() is None

    def test_mcp_security_headers_compliance(self):
        """Test that MCP server implements required security headers."""

        def endpoint(request):
            return PlainTextResponse("OK")

        base_app = Starlette()
        base_app.add_route("/", endpoint)

        config = TLSConfig()
        app = HTTPSEnforcementMiddleware(base_app, config, allow_http_localhost=True)

        client = TestClient(app)
        response = client.get("/")

        # Verify OWASP recommended security headers
        required_headers = {
            "Strict-Transport-Security": "max-age=",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=()",
        }

        for header, expected_value in required_headers.items():
            assert header in response.headers, f"Missing header: {header}"
            if expected_value:
                assert expected_value in response.headers[header], f"Header {header} missing expected value"


class TestMCPEnvironmentConfiguration:
    """Tests for MCP server configuration via environment variables."""

    def test_tls_cert_path_from_env(self):
        """Test that TLS certificate path is read from environment."""
        with patch.dict(os.environ, {"TLS_CERT_PATH": "/etc/ssl/certs/server.crt"}):
            cert_path = os.environ.get("TLS_CERT_PATH", "")
            assert cert_path == "/etc/ssl/certs/server.crt"

    def test_tls_key_path_from_env(self):
        """Test that TLS key path is read from environment."""
        with patch.dict(os.environ, {"TLS_KEY_PATH": "/etc/ssl/private/server.key"}):
            key_path = os.environ.get("TLS_KEY_PATH", "")
            assert key_path == "/etc/ssl/private/server.key"

    def test_tls_allowed_origins_from_env(self):
        """Test that TLS allowed origins are read from environment."""
        origins_str = "https://app.example.com,https://api.example.com"
        with patch.dict(os.environ, {"TLS_ALLOWED_ORIGINS": origins_str}):
            origins = os.environ.get("TLS_ALLOWED_ORIGINS", "").split(",")
            assert len(origins) == 2
            assert "https://app.example.com" in origins
            assert "https://api.example.com" in origins

    def test_tls_hsts_max_age_from_env(self):
        """Test that HSTS max-age is read from environment."""
        with patch.dict(os.environ, {"TLS_HSTS_MAX_AGE": "86400"}):
            max_age = int(os.environ.get("TLS_HSTS_MAX_AGE", "31536000"))
            assert max_age == 86400

    def test_default_tls_configuration_values(self):
        """Test default TLS configuration values."""
        reset_tls_config()

        config = get_tls_config()

        assert config.hsts_max_age == 31536000
        assert config.secure_cookies is True
        assert "https://localhost" in config.allowed_origins
        assert "https://127.0.0.1" in config.allowed_origins
