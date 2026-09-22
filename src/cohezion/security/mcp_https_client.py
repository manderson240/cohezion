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
            verify_ssl: Must be True. Certificate verification is always enforced
                on every transport; ``False`` raises ``ValueError``. (Before
                2026-09-21 ``False`` disabled verification for httpx/aiohttp but
                was silently overridden for ``get_ssl_context`` by bccb006af.)
                Use ``ca_cert_path`` to trust a private/self-signed CA instead.

        Raises:
            TypeError: if ``verify_ssl`` is not a bool (``"false"`` is truthy and
                would otherwise read as True).
            ValueError: if ``verify_ssl`` is False.
        """
        if not isinstance(verify_ssl, bool):
            raise TypeError(
                f"MCPHTTPSClient: verify_ssl must be a bool, got {type(verify_ssl).__name__} "
                f"{verify_ssl!r} (a string like 'false' is truthy)"
            )
        if not verify_ssl:
            raise ValueError(
                "MCPHTTPSClient: verify_ssl=False is not supported -- certificate "
                "verification is always enforced. To trust a self-signed server, "
                "pass ca_cert_path=<path to its CA certificate> instead."
            )
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

        Raises:
            FileNotFoundError: if ``ca_cert_path`` is set but does not exist.
        """
        if not self.use_https:
            return None

        if self._ssl_context is not None:
            return self._ssl_context

        # create_default_context() builds a PROTOCOL_TLS_CLIENT context with
        # minimum_version=TLSv1.2 enforced from construction (CodeQL
        # py/insecure-protocol) and hostname checking enabled.
        self._ssl_context = ssl.create_default_context()

        # Certificate verification is unconditional (verify_ssl=False is rejected
        # in __init__).
        self._ssl_context.check_hostname = True
        self._ssl_context.verify_mode = ssl.CERT_REQUIRED

        if self.ca_cert_path:
            ca_path = Path(self.ca_cert_path)
            if not ca_path.exists():
                # Same error type httpx raises for this path (configure_httpx passes it
                # through). Falling back to the system bundle would silently trust every
                # public CA in place of the private one that was asked for.
                self._ssl_context = None
                raise FileNotFoundError(f"CA certificate not found: {self.ca_cert_path}")
            self._ssl_context.load_verify_locations(self.ca_cert_path)
            logger.info("Loaded CA certificate: %s", self.ca_cert_path)
        else:
            # Use system CA bundle
            self._ssl_context.load_default_certs()

        # Enforce strong TLS versions — minimum_version=TLSv1_2 disables all older protocols
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._ssl_context.check_hostname = True

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

        except OSError as e:
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
            # Always verifying: True (system CA bundle) or the configured CA path.
            params["verify"] = self.ca_cert_path or True

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

        # No custom connector: aiohttp's default connector verifies certificates.
        # (An insecure TCPConnector(verify_ssl=False) used to be injected here.)
        return params
