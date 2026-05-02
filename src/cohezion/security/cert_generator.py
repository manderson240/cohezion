"""Self-signed certificate generation utility for development and testing."""

import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class CertificateGenerator:
    """Generate self-signed SSL certificates for development and testing."""

    @staticmethod
    def generate_self_signed_cert(
        cert_path: str,
        key_path: str,
        cn: str = "localhost",
        valid_days: int = 365,
        key_size: int = 2048,
        force: bool = False,
    ) -> bool:
        """
        Generate a self-signed SSL certificate.

        Args:
            cert_path: Path where certificate should be written
            key_path: Path where private key should be written
            cn: Common Name (CN) for the certificate (default: localhost)
            valid_days: Certificate validity period in days (default: 365)
            key_size: RSA key size in bits (default: 2048)
            force: Force regeneration even if files exist (default: False)

        Returns:
            True if certificate was generated successfully, False otherwise
        """
        cert_file = Path(cert_path)
        key_file = Path(key_path)

        # Check if files already exist
        if cert_file.exists() and key_file.exists() and not force:
            logger.info("Certificate already exists at %s", cert_path)
            return True

        # Ensure parent directories exist
        cert_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Generate self-signed certificate using OpenSSL
            cmd = [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                f"rsa:{key_size}",
                "-keyout",
                str(key_file),
                "-out",
                str(cert_file),
                "-days",
                str(valid_days),
                "-nodes",  # Don't encrypt key
                "-subj",
                f"/C=US/ST=State/L=City/O=Org/CN={cn}",
            ]

            _result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Set proper permissions
            key_file.chmod(0o600)
            cert_file.chmod(0o644)

            logger.info(
                "Generated self-signed certificate: %s, key: %s",
                cert_path,
                key_path,
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(
                "Failed to generate certificate: %s\nstderr: %s",
                e,
                e.stderr,
            )
            return False
        except FileNotFoundError:
            logger.error("OpenSSL not found. Install openssl to generate certificates.")
            return False
        except Exception as e:
            logger.error("Unexpected error generating certificate: %s", e)
            return False

    @staticmethod
    def ensure_dev_certificates(
        cert_dir: str = ".certs",
        cert_name: str = "server",
        force: bool = False,
    ) -> tuple[str | None, str | None]:
        """
        Ensure development certificates exist, generating them if needed.

        Args:
            cert_dir: Directory to store certificates (default: .certs)
            cert_name: Base name for certificate files (default: server)
            force: Force regeneration (default: False)

        Returns:
            Tuple of (cert_path, key_path) if successful, (None, None) otherwise
        """
        cert_path = str(Path(cert_dir) / f"{cert_name}.crt")
        key_path = str(Path(cert_dir) / f"{cert_name}.key")

        success = CertificateGenerator.generate_self_signed_cert(cert_path, key_path, force=force)

        if success:
            return cert_path, key_path

        return None, None
