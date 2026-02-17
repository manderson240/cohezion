#!/usr/bin/env python3
"""
Generate self-signed SSL/TLS certificates for development and testing.

Production certificates should be obtained from a trusted Certificate Authority (CA).
This script is for development, testing, and demo purposes only.

Usage:
    python scripts/generate_certificates.py [--output-dir DIR] [--key-size SIZE]
"""

import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


logger = logging.getLogger(__name__)


def generate_private_key(key_size: int = 2048):
    """
    Generate an RSA private key.

    Args:
        key_size: RSA key size in bits (default: 2048)

    Returns:
        RSA private key
    """
    logger.info("Generating %d-bit RSA private key...", key_size)
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )


def generate_certificate(
    private_key,
    common_name: str = "localhost",
    organization: str = "Cohezion Development",
    country: str = "US",
    days_valid: int = 365,
):
    """
    Generate a self-signed X.509 certificate.

    Args:
        private_key: RSA private key
        common_name: Common name (CN) for the certificate
        organization: Organization name
        country: Country code
        days_valid: Number of days the certificate is valid

    Returns:
        X.509 certificate
    """
    logger.info("Generating self-signed certificate for CN=%s", common_name)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Build certificate
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=days_valid))
    )

    # Add Subject Alternative Names (SANs)
    san_list = [
        x509.DNSName(common_name),
        x509.DNSName("*.localhost"),
        x509.DNSName("127.0.0.1"),
        x509.DNSName("localhost"),
    ]
    cert_builder = cert_builder.add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    )

    # Add Key Usage
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_agreement=True,
            content_commitment=False,
            data_encipherment=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )

    # Add Extended Key Usage
    cert_builder = cert_builder.add_extension(
        x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=True,
    )

    # Add Basic Constraints
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )

    # Sign the certificate
    certificate = cert_builder.sign(private_key, hashes.SHA256(), default_backend())

    logger.info(
        "Certificate generated (valid for %d days, expires %s)",
        days_valid,
        certificate.not_valid_after_utc.isoformat(),
    )

    return certificate


def save_certificate(certificate, output_path: Path):
    """
    Save certificate to PEM file.

    Args:
        certificate: X.509 certificate
        output_path: Output file path
    """
    pem_data = certificate.public_bytes(serialization.Encoding.PEM)
    output_path.write_bytes(pem_data)
    output_path.chmod(0o644)
    logger.info("Certificate saved to %s", output_path)


def save_private_key(private_key, output_path: Path):
    """
    Save private key to PEM file.

    Args:
        private_key: RSA private key
        output_path: Output file path
    """
    pem_data = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    output_path.write_bytes(pem_data)
    output_path.chmod(0o600)  # Restrictive permissions for private key
    logger.info("Private key saved to %s (chmod 600)", output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate self-signed SSL/TLS certificates for development")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/certificates"),
        help="Output directory for certificates (default: ./data/certificates)",
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        help="RSA key size in bits (default: 2048)",
    )
    parser.add_argument(
        "--common-name",
        default="localhost",
        help="Common name for the certificate (default: localhost)",
    )
    parser.add_argument(
        "--days-valid",
        type=int,
        default=365,
        help="Days the certificate is valid (default: 365)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    try:
        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Using output directory: %s", args.output_dir)

        # Generate private key
        private_key = generate_private_key(args.key_size)

        # Generate certificate
        certificate = generate_certificate(
            private_key,
            common_name=args.common_name,
            days_valid=args.days_valid,
        )

        # Save files
        cert_path = args.output_dir / "server.crt"
        key_path = args.output_dir / "server.key"

        save_certificate(certificate, cert_path)
        save_private_key(private_key, key_path)

        logger.info("")
        logger.info("Certificates generated successfully!")
        logger.info("")
        logger.info("Certificate: %s", cert_path)
        logger.info("Private Key: %s", key_path)
        logger.info("")
        logger.info("To use with uvicorn:")
        logger.info(
            "  uvicorn app:app --ssl-keyfile=%s --ssl-certfile=%s",
            key_path,
            cert_path,
        )
        logger.info("")
        logger.info("To use with environment variables:")
        logger.info("  export TLS_CERT_PATH=%s TLS_KEY_PATH=%s", cert_path, key_path)
        logger.info("")

        return 0

    except Exception as e:
        logger.error("Error generating certificates: %s", e)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
