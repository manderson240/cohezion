#!/bin/bash
#
# Generate self-signed TLS certificates for development and testing.
# For production, use properly signed certificates from a certificate authority.
#
# Usage:
#   ./scripts/setup/generate_tls_certificates.sh [--force] [--key-size 2048]
#
# Options:
#   --force       : Regenerate certificates even if they exist
#   --key-size    : RSA key size in bits (default: 2048, production: 4096)
#

set -e

# Configuration
CERTS_DIR="${CERTS_DIR:-.}/certs"
CERT_FILE="$CERTS_DIR/server.crt"
KEY_FILE="$CERTS_DIR/server.key"
KEY_SIZE=${KEY_SIZE:-2048}
DAYS_VALID=${DAYS_VALID:-365}
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --force)
      FORCE=true
      shift
      ;;
    --key-size)
      KEY_SIZE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${YELLOW}TLS Certificate Generation Script${NC}"
echo "=================================="
echo "Certificates Directory: $CERTS_DIR"
echo "Key Size: $KEY_SIZE bits"
echo "Validity: $DAYS_VALID days"
echo ""

# Check if certificates already exist
if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
  if [[ "$FORCE" != true ]]; then
    echo -e "${GREEN}✓ TLS certificates already exist${NC}"
    echo "  Certificate: $CERT_FILE"
    echo "  Private Key: $KEY_FILE"
    echo ""
    echo "To regenerate, use: --force"
    exit 0
  else
    echo -e "${YELLOW}⚠ Regenerating existing certificates (--force flag used)${NC}"
    rm -f "$CERT_FILE" "$KEY_FILE"
  fi
fi

# Create certificates directory
if [[ ! -d "$CERTS_DIR" ]]; then
  echo "Creating certificates directory: $CERTS_DIR"
  mkdir -p "$CERTS_DIR"
fi

# Generate private key and self-signed certificate
echo "Generating private key ($KEY_SIZE bits)..."
openssl genrsa -out "$KEY_FILE" "$KEY_SIZE" 2>/dev/null

echo "Generating self-signed certificate ($DAYS_VALID days validity)..."
openssl req -new -x509 \
  -key "$KEY_FILE" \
  -out "$CERT_FILE" \
  -days "$DAYS_VALID" \
  -subj "/C=US/ST=State/L=City/O=Cohezion/CN=localhost" \
  2>/dev/null

# Verify the certificate
if openssl x509 -in "$CERT_FILE" -noout 2>/dev/null; then
  echo -e "${GREEN}✓ Certificate generated successfully${NC}"
  echo ""
  echo "Certificate Details:"
  openssl x509 -in "$CERT_FILE" -noout -text | grep -E "Subject:|Issuer:|Not Before|Not After|Public-Key" | sed 's/^/  /'
  echo ""
  echo -e "${GREEN}✓ Both files created:${NC}"
  echo "  Certificate: $CERT_FILE"
  echo "  Private Key: $KEY_FILE"
  echo ""

  # Set secure permissions on private key
  chmod 600 "$KEY_FILE"
  echo "Private key permissions set to 600 (secure)"
  echo ""

  # Print environment variable usage
  echo -e "${YELLOW}To use these certificates, set environment variables:${NC}"
  echo "  export TLS_CERT_PATH=\"$CERT_FILE\""
  echo "  export TLS_KEY_PATH=\"$KEY_FILE\""
  echo "  export MCP_TLS_ENABLED=true"
  echo ""

  # For production warning
  if [[ "$KEY_SIZE" -lt 4096 ]]; then
    echo -e "${YELLOW}⚠ WARNING: Using $KEY_SIZE-bit key${NC}"
    echo "  For production, use 4096-bit keys:"
    echo "    ./scripts/setup/generate_tls_certificates.sh --key-size 4096"
  fi

  exit 0
else
  echo -e "${RED}✗ Certificate generation failed${NC}"
  exit 1
fi
