"""HTTPS-capable MCP client with certificate validation."""

import logging
import ssl
from pathlib import Path


logger = logging.getLogger(__name__)


class MCPHTTPSClient:
    """MCP client with HTTPS/TLS support."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8360,
        use_https: bool = True,
        ca_cert_path: str | None = None,
        verify_ssl: bool = True,
    ):
        """
        Initialize MCP HTTPS client.

        Args:
            host: Server hostname
            port: Server port
            use_https: Use HTTPS protocol (default: True)
            ca_cert_path: Path to CA certificate for validation
            verify_ssl: Verify SSL certificate (default: True)
        """
        self.host = host
        self.port = port
        self.use_https = use_https
        self.ca_cert_path = ca_cert_path
        self.verify_ssl = verify_ssl
        self._ssl_context = None

    @property
    def base_url(self) -> str:
        """Get base URL for MCP server."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def get_ssl_context(self) -> ssl.SSLContext | None:
        """
        Get SSL context for HTTPS connections.

        Returns:
            Configured ssl.SSLContext or None if HTTPS not enabled
        """
        if not self.use_https:
            return None

        if self._ssl_context is not None:
            return self._ssl_context

        # Create SSL context
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        # Configure certificate verification
        if self.verify_ssl:
            self._ssl_context.check_hostname = True
            self._ssl_context.verify_mode = ssl.CERT_REQUIRED

            if self.ca_cert_path:
                ca_path = Path(self.ca_cert_path)
                if ca_path.exists():
                    self._ssl_context.load_verify_locations(self.ca_cert_path)
                    logger.info("Loaded CA certificate: %s", self.ca_cert_path)
                else:
                    logger.warning("CA certificate not found: %s", self.ca_cert_path)
            else:
                # Use system CA bundle
                self._ssl_context.load_default_certs()
        else:
            # Disable certificate verification (not recommended for production)
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL certificate verification disabled")

        # Enforce strong TLS versions — explicitly disable insecure protocols
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._ssl_context.options |= (
            ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        )

        return self._ssl_context

    def get_headers(self) -> dict[str, str]:
        """
        Get headers for MCP requests.

        Returns:
            Dictionary of headers
        """
        return {
            "User-Agent": "Cohezion-MCP-Client/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def validate_connection(self) -> bool:
        """
        Validate connection to MCP server.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            import socket

            # Try to establish connection
            sock = socket.create_connection((self.host, self.port), timeout=5)

            if self.use_https:
                ssl_context = self.get_ssl_context()
                if ssl_context:
                    sock = ssl_context.wrap_socket(sock, server_hostname=self.host)

            sock.close()
            logger.info("✓ Connection to %s:%d validated", self.host, self.port)
            return True

        except (OSError, ssl.SSLError) as e:
            logger.error(
                "✗ Connection to %s:%s failed: %s",
                self.host,
                self.port,
                str(e),
            )
            return False

    def configure_urllib(self) -> ssl.SSLContext | None:
        """
        Configure urllib for HTTPS connections.

        Returns:
            SSL context for urllib usage
        """
        if not self.use_https:
            return None

        return self.get_ssl_context()

    def configure_httpx(self) -> dict:
        """
        Configure httpx client parameters.

        Returns:
            Dictionary of httpx client parameters
        """
        params = {
            "base_url": self.base_url,
            "headers": self.get_headers(),
            "timeout": 30.0,
        }

        if self.use_https:
            params["verify"] = self.verify_ssl
            if self.ca_cert_path:
                params["verify"] = self.ca_cert_path

        return params

    def configure_aiohttp(self) -> dict:
        """
        Configure aiohttp session parameters.

        Returns:
            Dictionary of aiohttp client session parameters
        """
        params = {
            "headers": self.get_headers(),
            "timeout": 30.0,
        }

        if self.use_https and not self.verify_ssl:
            import aiohttp

            connector = aiohttp.TCPConnector(verify_ssl=False)
            params["connector"] = connector

        return params
