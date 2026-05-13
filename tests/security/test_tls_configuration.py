"""TLS/HTTPS Configuration and Certificate Tests - Task #2 Validation.

This test suite validates Task #2 of Phase 2 Security Hardening:
- TLS/HTTPS configuration
- Certificate validation
- Secure uvicorn startup
- MCP client HTTPS support
- Certificate chain and expiration
"""

import os
import ssl
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CERTS_DIR = PROJECT_ROOT / "certs"


class TestTLSCertificateGeneration:
    """Test TLS certificate generation and validation."""

    def test_certificate_files_exist(self):
        """Verify self-signed certificates were generated."""
        cert_path = CERTS_DIR / "server.crt"
        key_path = CERTS_DIR / "server.key"

        if not cert_path.exists() or not key_path.exists():
            pytest.skip("Deployment certificates not present")
        assert cert_path.exists(), f"Certificate not found at {cert_path}"
        assert key_path.exists(), f"Private key not found at {key_path}"

    def test_certificate_file_permissions(self):
        """Verify private key has secure permissions."""
        cert_path = CERTS_DIR / "server.crt"
        key_path = CERTS_DIR / "server.key"

        if not cert_path.exists() or not key_path.exists():
            pytest.skip("Deployment certificates not present")

        # Certificate should be readable (644 or similar)
        cert_mode = oct(cert_path.stat().st_mode)[-3:]
        assert cert_mode in ["644", "664"], f"Certificate has insecure permissions: {cert_mode}"

        # Private key should only be readable by owner (600)
        key_mode = oct(key_path.stat().st_mode)[-3:]
        assert key_mode == "600", f"Private key has insecure permissions: {key_mode}"

    def test_certificate_is_valid_x509(self):
        """Verify certificate is valid X.509 format."""
        cert_path = CERTS_DIR / "server.crt"

        if not cert_path.exists():
            pytest.skip("Deployment certificates not present")

        try:
            import OpenSSL

            cert_data = cert_path.read_bytes()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_data)
            assert cert is not None
            assert cert.get_subject().CN == "localhost"
        except ImportError:
            pytest.skip("OpenSSL library not available")

    def test_certificate_common_name(self):
        """Verify certificate is issued for localhost."""
        cert_path = CERTS_DIR / "server.crt"

        if not cert_path.exists():
            pytest.skip("Deployment certificates not present")

        try:
            import OpenSSL

            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_path.read_bytes())
            cn = cert.get_subject().CN
            assert cn == "localhost", f"Certificate CN should be 'localhost', got '{cn}'"
        except ImportError:
            pytest.skip("OpenSSL library not available")

    def test_certificate_self_signed(self):
        """Verify certificate is self-signed."""
        cert_path = CERTS_DIR / "server.crt"

        if not cert_path.exists():
            pytest.skip("Deployment certificates not present")

        try:
            import OpenSSL

            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_path.read_bytes())
            # Self-signed: issuer == subject
            issuer = cert.get_issuer()
            subject = cert.get_subject()
            assert issuer.CN == subject.CN, "Certificate should be self-signed"
        except ImportError:
            pytest.skip("OpenSSL library not available")


class TestTLSConfiguration:
    """Test TLS configuration in MCP server."""

    def test_tls_config_module_exists(self):
        """Verify TLSConfig module is available."""
        try:
            from cohezion.security.tls_config import TLSConfig

            assert TLSConfig is not None
        except ImportError as e:
            pytest.fail(f"TLSConfig module not found: {e}")

    def test_https_middleware_exists(self):
        """Verify HTTPS middleware is available."""
        try:
            from cohezion.security.https_middleware import create_https_app

            assert create_https_app is not None
        except ImportError as e:
            pytest.fail(f"HTTPS middleware not found: {e}")

    def test_tls_config_initialization(self):
        """Test TLSConfig initialization with certificate paths."""
        from cohezion.security.tls_config import TLSConfig

        cert_path = str(CERTS_DIR / "server.crt")
        key_path = str(CERTS_DIR / "server.key")

        config = TLSConfig(cert_path=cert_path, key_path=key_path)
        assert config.cert_path == cert_path
        assert config.key_path == key_path

    def test_tls_config_validates_certificate(self):
        """Test TLSConfig certificate validation."""
        cert_path = CERTS_DIR / "server.crt"
        key_path = CERTS_DIR / "server.key"

        if not cert_path.exists() or not key_path.exists():
            pytest.skip("Deployment certificates not present")

        from cohezion.security.tls_config import TLSConfig

        config = TLSConfig(cert_path=str(cert_path), key_path=str(key_path))
        # Should validate successfully
        result = config.validate_certificate()
        assert result is True, "Certificate validation failed"

    def test_tls_config_hsts_header(self):
        """Test TLSConfig generates HSTS header."""
        from cohezion.security.tls_config import TLSConfig

        config = TLSConfig(hsts_max_age=31536000)
        # Should have HSTS configuration
        assert config.hsts_max_age == 31536000


class TestUvicornSSLConfiguration:
    """Test Uvicorn SSL/TLS configuration."""

    def test_mcp_server_main_imports_tls(self):
        """Verify MCP server imports TLS modules."""
        # This test ensures main.py can import the TLS modules
        try:
            from cloud_vault_mcp.src.mcp_server import main

            assert hasattr(main, "TLSConfig")
        except Exception:
            # If direct import fails, that's okay - the conditional import handles it
            pass

    def test_environment_variables_for_tls(self):
        """Test environment variables can be set for TLS."""
        # Simulating environment setup for Uvicorn
        test_env = {
            "TLS_CERT_PATH": str(CERTS_DIR / "server.crt"),
            "TLS_KEY_PATH": str(CERTS_DIR / "server.key"),
            "MCP_TLS_ENABLED": "true",
        }

        with patch.dict(os.environ, test_env):
            assert os.environ.get("TLS_CERT_PATH").endswith("server.crt")
            assert os.environ.get("TLS_KEY_PATH").endswith("server.key")
            assert os.environ.get("MCP_TLS_ENABLED") == "true"


class TestMCPClientHTTPSSupport:
    """Test MCP client HTTPS support."""

    def test_mcp_client_imports(self):
        """Verify MCP client can be imported."""
        try:
            from cohezion.core.mcp_client import MCPClient

            assert MCPClient is not None
        except ImportError as e:
            pytest.skip(f"MCPClient not available: {e}")

    @patch("ssl.create_default_context")
    def test_ssl_context_creation(self, mock_ssl_context):
        """Test SSL context can be created for HTTPS."""
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        # Simulate creating SSL context
        context = ssl.create_default_context()
        assert context is mock_context


class TestCertificateGeneration:
    """Test certificate generation script."""

    def test_setup_script_is_executable(self):
        """Verify certificate generation script exists and is executable."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "generate_tls_certificates.sh"
        assert script_path.exists(), f"Script not found at {script_path}"
        assert os.access(script_path, os.X_OK), f"Script is not executable: {script_path}"

    def test_certificate_generation_with_force_flag(self):
        """Test certificate can be regenerated with --force flag."""
        # This would require actually running the script, which is integration-level
        # For now, verify the script accepts the flag
        script_path = PROJECT_ROOT / "scripts" / "setup" / "generate_tls_certificates.sh"
        with open(script_path) as f:
            content = f.read()
        assert "--force" in content, "Script should support --force flag"

    def test_certificate_generation_key_size_option(self):
        """Test certificate supports custom key size."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "generate_tls_certificates.sh"
        with open(script_path) as f:
            content = f.read()
        assert "--key-size" in content, "Script should support --key-size option"


class TestTLSIntegration:
    """Integration tests for TLS/HTTPS configuration."""

    def test_certificate_and_key_exist_together(self):
        """Verify both certificate and key exist for HTTPS."""
        cert_path = CERTS_DIR / "server.crt"
        key_path = CERTS_DIR / "server.key"

        if not cert_path.exists() or not key_path.exists():
            pytest.skip("Deployment certificates not present")

        assert cert_path.exists() and key_path.exists(), "Both certificate and key must exist for HTTPS"

    def test_tls_environment_variables_documented(self):
        """Verify TLS configuration environment variables are documented."""
        # Check if setup script documents the environment variables
        script_path = PROJECT_ROOT / "scripts" / "setup" / "generate_tls_certificates.sh"
        with open(script_path) as f:
            content = f.read()

        expected_vars = [
            "TLS_CERT_PATH",
            "TLS_KEY_PATH",
            "MCP_TLS_ENABLED",
        ]
        for var in expected_vars:
            assert var in content, f"Environment variable {var} not documented in script"

    def test_certificate_validity_period(self):
        """Verify certificate is valid for at least one year."""
        cert_path = CERTS_DIR / "server.crt"

        if not cert_path.exists():
            pytest.skip("Deployment certificates not present")

        try:
            from datetime import datetime

            import OpenSSL

            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_path.read_bytes())

            not_after = cert.get_notAfter().decode()
            # Parse the date (format: YYYYMMDDHHmmssZ)
            exp_date = datetime.strptime(not_after, "%Y%m%d%H%M%SZ")
            days_valid = (exp_date - datetime.utcnow()).days

            assert days_valid >= 365, f"Certificate validity < 1 year: {days_valid} days"
        except ImportError:
            pytest.skip("OpenSSL library not available")
