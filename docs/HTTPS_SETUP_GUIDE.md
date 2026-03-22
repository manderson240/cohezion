# HTTPS/TLS Configuration Guide

This guide explains how to set up and configure HTTPS/TLS security for the Cloud Vault MCP Server.

## Overview

The Cohezion MCP server supports three deployment modes:

1. **Development (HTTP)** - Local testing without certificates
2. **Development with Self-Signed HTTPS** - Local testing with TLS/SSL
3. **Production (HTTPS)** - Production deployment with valid certificates

## Prerequisites

- OpenSSL installed (for certificate generation)
- Python 3.13+
- `uv` package manager

## Development Setup (Self-Signed Certificates)

### 1. Generate Self-Signed Certificates

```bash
python scripts/setup_tls_certificates.py dev
```

This will:
- Generate a self-signed certificate in `.certs/server.crt`
- Generate a private key in `.certs/server.key`
- Set appropriate file permissions

### 2. Configure Environment Variables

```bash
export TLS_ENABLED=true
export TLS_CERT_PATH=/absolute/path/to/.certs/server.crt
export TLS_KEY_PATH=/absolute/path/to/.certs/server.key
```

Or add to `.env` file:

```env
TLS_ENABLED=true
TLS_CERT_PATH=/home/user/dev/cohezion/.certs/server.crt
TLS_KEY_PATH=/home/user/dev/cohezion/.certs/server.key
TLS_HSTS_MAX_AGE=31536000
TLS_ALLOWED_ORIGINS=https://localhost,https://127.0.0.1
```

### 3. Start the Server

```bash
python -m cohezion.cloud_vault_mcp.src.mcp_server.main
```

The server will now run on `https://localhost:8360`

### 4. Test HTTPS Connection

```bash
curl --insecure https://localhost:8360/
```

Or with Python:

```python
from cohezion.security.mcp_https_client import MCPHTTPSClient

client = MCPHTTPSClient(
    host="localhost",
    port=8360,
    use_https=True,
    verify_ssl=False  # For self-signed certs
)

if client.validate_connection():
    print("✓ HTTPS connection successful")
else:
    print("✗ HTTPS connection failed")
```

## Production Setup (Valid Certificates)

### 1. Obtain Certificates

For production, use certificates from a trusted Certificate Authority (CA):

**Option A: Let's Encrypt (Free)**
```bash
# Using certbot
sudo certbot certonly --standalone -d your-domain.com
# Certificates will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem (cert)
# /etc/letsencrypt/live/your-domain.com/privkey.pem (key)
```

**Option B: Commercial CA**
- Follow your CA's certificate issuance process
- Download both certificate and private key files

### 2. Validate Certificates

```bash
python scripts/setup_tls_certificates.py validate \
  --cert /path/to/certificate.pem \
  --key /path/to/private.key
```

### 3. Configure for Production

```bash
export TLS_ENABLED=true
export TLS_CERT_PATH=/path/to/certificate.pem
export TLS_KEY_PATH=/path/to/private.key
export TLS_HSTS_MAX_AGE=31536000
export TLS_ALLOWED_ORIGINS=https://your-domain.com,https://api.your-domain.com
```

### 4. Deploy

```bash
python -m cohezion.cloud_vault_mcp.src.mcp_server.main
```

### 5. Verify Production Setup

```bash
python scripts/setup_tls_certificates.py validate \
  --cert /path/to/certificate.pem \
  --key /path/to/private.key
```

## Configuration Options

### TLS Configuration Parameters

| Environment Variable | Default | Description |
|---|---|---|
| `TLS_ENABLED` | `false` | Enable HTTPS/TLS enforcement |
| `TLS_CERT_PATH` | `` | Path to SSL certificate file |
| `TLS_KEY_PATH` | `` | Path to SSL private key file |
| `TLS_HSTS_MAX_AGE` | `31536000` | HSTS max-age in seconds (default: 1 year) |
| `TLS_ALLOWED_ORIGINS` | `https://localhost,https://127.0.0.1` | Allowed CORS origins (comma-separated) |

### Security Headers Applied

When TLS is enabled, the following security headers are automatically added:

- `Strict-Transport-Security` (HSTS) - Enforce HTTPS
- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Referrer control
- `Permissions-Policy` - Restrict browser features

### Cookie Security Flags

When TLS is enabled, cookies are automatically configured with:

- `Secure` - HTTPS only transmission
- `HttpOnly` - No JavaScript access
- `SameSite=Strict` - CSRF protection

## MCP Client Configuration

### Using HTTPS with Python Client

```python
from cohezion.security.mcp_https_client import MCPHTTPSClient

# Development with self-signed certificates
client = MCPHTTPSClient(
    host="localhost",
    port=8360,
    use_https=True,
    verify_ssl=False  # Accept self-signed
)

# Production with valid certificates
client = MCPHTTPSClient(
    host="your-domain.com",
    port=8360,
    use_https=True,
    verify_ssl=True,  # Verify certificate
    ca_cert_path="/path/to/ca.pem"  # Optional: custom CA
)

# Test connection
if client.validate_connection():
    print("Connected successfully")

# Get HTTPS-compatible parameters for different libraries
httpx_params = client.configure_httpx()
aiohttp_params = client.configure_aiohttp()
urllib_context = client.configure_urllib()
```

## Troubleshooting

### Issue: Certificate file not found

```
Error: Certificate file not found: /path/to/cert.pem
```

**Solution**: Verify the path and ensure the file exists with proper permissions.

### Issue: Permission denied on private key

```
Error: Key file not readable: /path/to/key.pem
```

**Solution**: Ensure the key file has appropriate permissions:
```bash
chmod 600 /path/to/key.pem
```

### Issue: HTTPS connection fails with self-signed certificate

```
Error: CERTIFICATE_VERIFY_FAILED
```

**Solution**: For development, use `verify_ssl=False`:
```python
client = MCPHTTPSClient(verify_ssl=False)
```

### Issue: Port 8360 already in use

```
Error: Address already in use
```

**Solution**: Change the port via environment variable:
```bash
export MCP_PORT=9000
```

### Issue: Browser warns about untrusted certificate

This is normal for self-signed certificates. For production, use valid certificates from a trusted CA.

## Testing HTTPS Configuration

### Run Security Tests

```bash
uv run pytest tests/security/test_tls_https_configuration.py -v
uv run pytest tests/security/test_mcp_https_client.py -v
```

### Full Security Test Suite

```bash
uv run pytest tests/security/ -v
```

Expected: 229+ security tests passing

## Renewal and Updates

### Self-Signed Certificates (Development)

Regenerate when needed:
```bash
python scripts/setup_tls_certificates.py dev --force
```

### Let's Encrypt Certificates (Production)

Set up automatic renewal:
```bash
sudo certbot renew --quiet --no-eff-email
```

### Certificate Validation

Verify certificates are still valid:
```bash
python scripts/setup_tls_certificates.py validate \
  --cert /path/to/certificate.pem \
  --key /path/to/private.key
```

## Best Practices

1. **Always use HTTPS in production** - Set `TLS_ENABLED=true`
2. **Restrict allowed origins** - Use specific domains instead of wildcards
3. **Rotate certificates before expiry** - Set calendar reminders
4. **Use strong key sizes** - Minimum 2048-bit RSA keys
5. **Monitor certificate expiry** - Log rotation events
6. **Enforce HSTS** - Default 1-year max-age prevents downgrade attacks
7. **Keep TLS versions current** - Minimum TLS 1.2 enforced
8. **Regular security audits** - Run full test suite before deployment

## Architecture

The HTTPS implementation consists of:

1. **TLSConfig** (`src/cohezion/security/tls_config.py`) - Configuration management
2. **HTTPSEnforcementMiddleware** - HTTPS enforcement and security headers
3. **SecureCookieMiddleware** - Cookie security flags
4. **CertificateGenerator** - Self-signed certificate generation
5. **MCPHTTPSClient** - HTTPS-compatible MCP client

All components are:
- Fully tested (229+ security tests)
- Production-grade
- Backward compatible
- Non-blocking (graceful fallback to HTTP on localhost)

## References

- [OWASP Transport Layer Protection](https://owasp.org/www-project-cheat-sheets/cheatsheets/Transport_Layer_Protection_Cheat_Sheet)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
