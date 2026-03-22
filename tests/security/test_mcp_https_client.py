"""Tests for MCP HTTPS client."""

import ssl
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from cohezion.security.mcp_https_client import MCPHTTPSClient


class TestMCPHTTPSClient:
    """Test MCP HTTPS client."""

    def test_client_initialization_defaults(self):
        """Test client initialization with defaults."""
        client = MCPHTTPSClient()

        assert client.host == "localhost"
        assert client.port == 8360
        assert client.use_https is True
        assert client.verify_ssl is True

    def test_client_initialization_custom_values(self):
        """Test client initialization with custom values."""
        client = MCPHTTPSClient(
            host="example.com",
            port=9000,
            use_https=False,
            verify_ssl=False,
        )

        assert client.host == "example.com"
        assert client.port == 9000
        assert client.use_https is False
        assert client.verify_ssl is False

    def test_base_url_https(self):
        """Test base URL generation with HTTPS."""
        client = MCPHTTPSClient(use_https=True)
        assert client.base_url == "https://localhost:8360"

    def test_base_url_http(self):
        """Test base URL generation with HTTP."""
        client = MCPHTTPSClient(use_https=False)
        assert client.base_url == "http://localhost:8360"

    def test_get_ssl_context_disabled(self):
        """Test SSL context when HTTPS is disabled."""
        client = MCPHTTPSClient(use_https=False)
        context = client.get_ssl_context()

        assert context is None

    def test_get_ssl_context_enabled(self):
        """Test SSL context when HTTPS is enabled."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=False)
        context = client.get_ssl_context()

        assert context is not None
        assert isinstance(context, ssl.SSLContext)

    def test_get_ssl_context_with_ca_cert(self):
        """Test SSL context with custom CA certificate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ca_cert_path = Path(tmpdir) / "ca.pem"
            ca_cert_path.write_text("CERTIFICATE")

            client = MCPHTTPSClient(
                use_https=True,
                ca_cert_path=str(ca_cert_path),
                verify_ssl=True,
            )

            # Mock the load_verify_locations to avoid SSL parsing errors
            with patch.object(ssl.SSLContext, "load_verify_locations"):
                context = client.get_ssl_context()
                assert context is not None

    def test_get_ssl_context_missing_ca_cert(self):
        """Test SSL context with missing CA certificate."""
        client = MCPHTTPSClient(
            use_https=True,
            ca_cert_path="/nonexistent/ca.pem",
            verify_ssl=True,
        )

        # Should still return a context, just without custom CA
        context = client.get_ssl_context()
        assert context is not None

    def test_get_ssl_context_verify_disabled(self):
        """Test SSL context with verification disabled."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=False)
        context = client.get_ssl_context()

        assert context is not None
        assert context.check_hostname is False
        assert context.verify_mode == ssl.CERT_NONE

    def test_get_ssl_context_verify_enabled(self):
        """Test SSL context with verification enabled."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=True)
        context = client.get_ssl_context()

        assert context is not None
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_get_ssl_context_caching(self):
        """Test SSL context caching."""
        client = MCPHTTPSClient(use_https=True)
        context1 = client.get_ssl_context()
        context2 = client.get_ssl_context()

        assert context1 is context2  # Same object

    def test_get_headers(self):
        """Test header generation."""
        client = MCPHTTPSClient()
        headers = client.get_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_validate_connection_https_success(self):
        """Test successful HTTPS connection validation."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=False)

        # Mock successful connection
        with patch("socket.create_connection") as mock_socket:
            with patch.object(ssl.SSLContext, "wrap_socket") as mock_wrap:
                mock_sock = MagicMock()
                mock_socket.return_value = mock_sock
                mock_wrap.return_value = mock_sock

                result = client.validate_connection()

                assert result is True
                mock_socket.assert_called_once()
                mock_sock.close.assert_called_once()

    def test_validate_connection_http_success(self):
        """Test successful HTTP connection validation."""
        client = MCPHTTPSClient(use_https=False)

        with patch("socket.create_connection") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            result = client.validate_connection()

            assert result is True
            mock_socket.assert_called_once()
            mock_sock.close.assert_called_once()

    def test_validate_connection_failure(self):
        """Test connection validation failure."""
        client = MCPHTTPSClient()

        with patch("socket.create_connection", side_effect=OSError):
            result = client.validate_connection()

            assert result is False

    def test_validate_connection_ssl_error(self):
        """Test connection validation with SSL error."""
        client = MCPHTTPSClient(use_https=True)

        with patch("socket.create_connection") as mock_socket:
            with patch.object(ssl.SSLContext, "wrap_socket", side_effect=ssl.SSLError):
                mock_sock = MagicMock()
                mock_socket.return_value = mock_sock

                result = client.validate_connection()

                # SSL error during wrap_socket should be caught
                assert result is False

    def test_configure_urllib_https(self):
        """Test urllib configuration with HTTPS."""
        client = MCPHTTPSClient(use_https=True)
        context = client.configure_urllib()

        assert context is not None
        assert isinstance(context, ssl.SSLContext)

    def test_configure_urllib_http(self):
        """Test urllib configuration with HTTP."""
        client = MCPHTTPSClient(use_https=False)
        context = client.configure_urllib()

        assert context is None

    def test_configure_httpx_https(self):
        """Test httpx configuration with HTTPS."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=True)
        params = client.configure_httpx()

        assert "base_url" in params
        assert "headers" in params
        assert "verify" in params
        assert params["base_url"] == "https://localhost:8360"

    def test_configure_httpx_http(self):
        """Test httpx configuration with HTTP."""
        client = MCPHTTPSClient(use_https=False)
        params = client.configure_httpx()

        assert params["base_url"] == "http://localhost:8360"
        assert "verify" not in params or params.get("verify") is None

    def test_configure_httpx_custom_ca(self):
        """Test httpx configuration with custom CA."""
        client = MCPHTTPSClient(
            use_https=True,
            ca_cert_path="/path/to/ca.pem",
        )

        params = client.configure_httpx()

        assert params.get("verify") == "/path/to/ca.pem"

    def test_configure_aiohttp_https(self):
        """Test aiohttp configuration with HTTPS."""
        client = MCPHTTPSClient(use_https=True, verify_ssl=True)
        params = client.configure_aiohttp()

        assert "headers" in params
        # When verify_ssl=True and use_https=True, no connector override
        if "connector" in params:
            assert params["connector"] is not None

    def test_configure_aiohttp_http(self):
        """Test aiohttp configuration with HTTP."""
        client = MCPHTTPSClient(use_https=False)
        params = client.configure_aiohttp()

        assert "headers" in params
        assert "connector" not in params

    def test_configure_aiohttp_verify_disabled(self):
        """Test aiohttp configuration with verification disabled."""
        with patch("aiohttp.TCPConnector") as mock_connector:
            client = MCPHTTPSClient(use_https=True, verify_ssl=False)
            params = client.configure_aiohttp()

            if "connector" in params:
                mock_connector.assert_called_with(verify_ssl=False)

    def test_client_host_port_configuration(self):
        """Test client with custom host and port."""
        client = MCPHTTPSClient(host="api.example.com", port=443)

        assert client.host == "api.example.com"
        assert client.port == 443
        assert client.base_url == "https://api.example.com:443"

    def test_client_with_self_signed_cert(self):
        """Test client configured for self-signed certificates."""
        client = MCPHTTPSClient(
            use_https=True,
            verify_ssl=False,  # Allow self-signed
        )

        context = client.get_ssl_context()
        assert context is not None
        assert context.verify_mode == ssl.CERT_NONE

    def test_client_minimum_tls_version(self):
        """Test that minimum TLS version is enforced."""
        client = MCPHTTPSClient(use_https=True)
        context = client.get_ssl_context()

        assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
