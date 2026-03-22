#!/usr/bin/env python
"""Setup TLS/HTTPS certificates for development and production."""

import argparse
import logging
import os
import sys
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.security.cert_generator import CertificateGenerator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_dev_certificates(cert_dir: str = ".certs") -> bool:
    """Setup development certificates."""
    logger.info("Setting up development TLS certificates...")

    cert_path, key_path = CertificateGenerator.ensure_dev_certificates(cert_dir=cert_dir, force=False)

    if cert_path and key_path:
        logger.info("✓ Development certificates ready")
        logger.info("  Certificate: %s", cert_path)
        logger.info("  Private key: %s", key_path)

        # Print environment variables for easy setup
        logger.info("\nSet these environment variables:")
        logger.info("  export TLS_ENABLED=true")
        logger.info("  export TLS_CERT_PATH=%s", os.path.abspath(cert_path))
        logger.info("  export TLS_KEY_PATH=%s", os.path.abspath(key_path))

        return True
    else:
        logger.error("✗ Failed to setup certificates")
        return False


def setup_production_certificates(cert_path: str, key_path: str, validate_only: bool = False) -> bool:
    """Setup or validate production certificates."""
    from cohezion.security.tls_config import TLSConfig

    logger.info("Validating production TLS certificates...")

    if not Path(cert_path).exists():
        logger.error("Certificate file not found: %s", cert_path)
        return False

    if not Path(key_path).exists():
        logger.error("Key file not found: %s", key_path)
        return False

    config = TLSConfig(cert_path=cert_path, key_path=key_path)

    if not config.validate_certificate():
        logger.error("Certificate validation failed")
        return False

    logger.info("✓ Production certificates validated")
    logger.info("  Certificate: %s", cert_path)
    logger.info("  Private key: %s", key_path)

    if config.configure_for_production():
        logger.info("✓ Production security configuration passed")
        return True
    else:
        logger.error("✗ Production security configuration failed")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup TLS/HTTPS certificates for Cohezion")

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["dev", "prod", "validate"],
        default="dev",
        help="Certificate setup mode (default: dev)",
    )

    parser.add_argument(
        "--cert",
        help="Path to certificate file (for prod mode)",
    )

    parser.add_argument(
        "--key",
        help="Path to private key file (for prod mode)",
    )

    parser.add_argument(
        "--cert-dir",
        default=".certs",
        help="Directory for development certificates (default: .certs)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of development certificates",
    )

    args = parser.parse_args()

    if args.mode == "dev":
        success = setup_dev_certificates(cert_dir=args.cert_dir)
    elif args.mode in ("prod", "validate"):
        if not args.cert or not args.key:
            logger.error("--cert and --key required for production mode")
            return 1
        success = setup_production_certificates(args.cert, args.key)
    else:
        logger.error("Unknown mode: %s", args.mode)
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
