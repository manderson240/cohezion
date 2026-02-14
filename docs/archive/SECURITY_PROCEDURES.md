# Security Procedures for Phase 5B

**Status**: CRITICAL - IMPLEMENTATION REQUIRED
**Priority**: BLOCKING for production deployment
**Phase 1-2 Duration**: 6 hours total
**Target**: Complete before Phase 5B.1 rollout

---

## Critical Security Issues Found

During Phase 5B audit (Session 40), 8 exposed credentials were identified in `.env` file with world-readable permissions (644).

### Exposed Credentials Inventory

1. **GOOGLE_EMAIL** & **GOOGLE_SHEETS_TOKEN_JSON**
   - **Type**: OAuth credentials
   - **Risk**: CRITICAL - Can access Google Sheets API
   - **Action**: Regenerate OAuth token

2. **NOTIFICATION_PASSWORD** (`avgakwqibilnssie`)
   - **Type**: Email password
   - **Risk**: CRITICAL - Can send emails from system account
   - **Action**: Change email password

3. **KEPLER_WALLET_KEY** (e404...90e16)
   - **Type**: Cryptocurrency private key
   - **Risk**: CRITICAL - Direct financial asset exposure
   - **Action**: Transfer funds, generate new wallet

4. **DUCKDNS_TOKEN** (2329a549-3d0f-...)
   - **Type**: DNS API token
   - **Risk**: HIGH - Can modify DNS records
   - **Action**: Revoke and regenerate

5. **SURREAL_USER/SURREAL_PASS** (root/root)
   - **Type**: Database credentials
   - **Risk**: CRITICAL - Full database access
   - **Action**: Change immediately

6. **SUDO_PASSWORD** (@Orionmax23)
   - **Type**: System root password
   - **Risk**: CRITICAL - Full system access
   - **Action**: Change system password

7. **BLUEQUBIT_API_TOKEN** (Wq0MRh8lQbTVSeFz...)
   - **Type**: API token
   - **Risk**: HIGH - Unauthorized API usage
   - **Action**: Revoke and regenerate

8. **HUGGING_FACE_API_TOKEN** (hf_wekLvlBwQmOkYca...)
   - **Type**: ML API token
   - **Risk**: HIGH - Unauthorized model access
   - **Action**: Revoke and regenerate

---

## Phase 1: Emergency Credential Rotation (2 Hours - BLOCKING)

### 1.1 Secure the .env File (15 minutes)

```bash
# Change file permissions to 600 (owner read/write only)
chmod 600 .env
chmod 600 cloud-vault-mcp/.env
chmod 600 cloud-vault-mcp/.env.example

# Verify permissions
ls -la .env cloud-vault-mcp/.env

# Check git history for exposure
git log --all --source --full-history -S "NOTIFICATION_PASSWORD" -- .env
```

### 1.2 Rotate Each Credential (2 Hours)

**Google Credentials** (30 minutes)
```bash
# 1. Go to https://myaccount.google.com/security
# 2. Revoke current OAuth token
# 3. Generate new OAuth token
# 4. Update GOOGLE_EMAIL and GOOGLE_SHEETS_TOKEN_JSON
# 5. Test connection: 
#    python -c "from clients import google; google.test_connection()"
```

**Email Credentials** (20 minutes)
```bash
# 1. Go to email provider security settings
# 2. Change password to strong 20+ character random
# 3. If 2FA, generate new app password
# 4. Update NOTIFICATION_PASSWORD in .env
# 5. Test: python -c "from clients import email; email.test_send()"
```

**Database Credentials** (20 minutes)
```bash
# 1. Connect to SurrealDB with current creds
# 2. Create new admin user
# 3. Delete old root password from memory
# 4. Update SURREAL_USER and SURREAL_PASS
# 5. Test: 
#    uv run pytest tests/integration/test_database.py::test_connection
```

**System Root Password** (20 minutes)
```bash
# 1. Login as current user
# 2. Change sudo password:
sudo passwd
# 3. Update SUDO_PASSWORD in .env
# 4. Test: sudo -l (should work with new password)
```

**API Tokens** (40 minutes)
```bash
# For each: DUCKDNS, BLUEQUBIT, HUGGING_FACE
# 1. Go to respective provider dashboard
# 2. Revoke current token
# 3. Generate new token
# 4. Update in .env
# 5. Run integration tests

# Test each:
uv run pytest tests/integration/test_external_apis.py -v
```

**Cryptocurrency** (30 minutes)
```bash
# 1. Transfer all funds from exposed wallet to new wallet
# 2. Generate new wallet key pair
# 3. Update KEPLER_WALLET_KEY
# 4. Verify transfer completed
# 5. Do NOT keep crypto private keys in .env (better: hardware wallet or KMS)
```

### 1.3 Verify All Changes (15 minutes)

```bash
# Run security tests
uv run pytest tests/security/test_credentials.py -v

# Verify no secrets in git
git log -p -- .env | grep -i "password\|api_key\|token" | wc -l
# Expected: 0

# Check .gitignore
cat .gitignore | grep -E "\.env|secrets"
```

---

## Phase 2: Infrastructure Hardening (4 Hours - BLOCKING)

### 2.1 Apply APIKeyAuth Middleware (1 Hour)

```bash
# 1. Install middleware
uv add fastapi-apikeys

# 2. Update MCP server
# File: cloud-vault-mcp/src/mcp_server/main.py
# Add:
from fastapi_apikeys import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# 3. Add to all endpoints
@app.get("/health")
async def health(api_key: str = Depends(api_key_header)):
    # Validate key before processing
    if not validate_api_key(api_key):
        raise HTTPException(status_code=403)
    return {"status": "ok"}

# 4. Test authentication
curl -H "X-API-Key: invalid" http://localhost:8360/health
# Expected: 403 Forbidden
```

### 2.2 Enable TLS/HTTPS (1 Hour)

```bash
# 1. Generate self-signed cert (for dev)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# 2. Or: Get valid cert from Let's Encrypt
certbot certonly --standalone -d yourdomain.com

# 3. Update server configuration
# File: cloud-vault-mcp/src/mcp_server/main.py
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain("cert.pem", "key.pem")

# 4. Start with TLS
uvicorn.run(app, host="0.0.0.0", port=8360, ssl_context=ssl_context)

# 5. Test HTTPS
curl -k https://localhost:8360/health
```

### 2.3 Implement Audit Logging (1 Hour)

```bash
# 1. Create audit log module
# File: src/cohezion/security/audit_logger.py
import logging
import json
from datetime import datetime

class AuditLogger:
    def log_access(self, user, endpoint, method, status):
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "endpoint": endpoint,
            "method": method,
            "status": status
        }
        logger.info(json.dumps(log))

# 2. Integrate with MCP server
from cohezion.security.audit_logger import AuditLogger
audit = AuditLogger()

@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    audit.log_access(
        user=request.headers.get("X-User"),
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    )
    return response

# 3. Test logging
curl http://localhost:8360/health -H "X-User: testuser"
# Check logs: tail -f logs/audit.log
```

### 2.4 Fix CORS Configuration (30 minutes)

```bash
# Current issue: ALLOW_ORIGINS set to "*" (insecure)

# File: cloud-vault-mcp/src/mcp_server/config.py
# Update from:
ALLOW_ORIGINS = "*"

# To:
ALLOW_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://api.example.com",
    # Add only trusted domains
]

# Restart server:
python -m mcp_server.main
```

### 2.5 Add Pre-Commit Hooks (30 minutes)

```bash
# 1. Install pre-commit
uv add pre-commit

# 2. Create config
# File: .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.0.3
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

# 3. Install hooks
pre-commit install

# 4. Test detection
echo "password: mysecret123" >> test.py
git add test.py
git commit -m "test"  # Will fail if secret detected

# 5. Clean up
git rm test.py
```

---

## Phase 2 Verification (30 minutes)

```bash
# Run all security tests
uv run pytest tests/security/ -v

# Check no credentials in code
grep -r "password\|api_key\|token" src/ --include="*.py" | grep -v "#.*password"

# Verify environment variables
env | grep -E "PASSWORD|TOKEN|API_KEY|SECRET"
# Expected: Only show non-sensitive env vars

# Test endpoints with auth
curl http://localhost:8360/health
# Expected: 403 Forbidden (missing API key)

curl -H "X-API-Key: valid-key" http://localhost:8360/health
# Expected: 200 OK (with valid key)
```

---

## Phase 3: Ongoing Credential Management

### Rotation Schedule

```
Initial Rotation:  NOW (Phase 1-2, 6 hours)
Monthly Review:    Every 1st of month
Quarterly Rotation: Every 3 months
Annual Audit:      Every 12 months
```

### Best Practices

1. **Never commit credentials to git** ✅ .gitignore enforced
2. **Use environment variables** ✅ .env pattern
3. **Rotate on schedule** ✅ Quarterly minimum
4. **Audit access logs** ✅ Implement logging
5. **Use API keys instead of passwords** ✅ Prefer tokens
6. **Store secrets in KMS** ✅ Future Phase 3 goal
7. **Document all credentials** ✅ Keep inventory

### Inventory Template

```
Credential Type | Location | Last Rotated | Rotation Due | Owner
Google Sheets   | .env     | 2026-02-09   | 2026-05-09   | team-lead
Database        | .env     | 2026-02-09   | 2026-05-09   | devops-specialist
Email           | .env     | 2026-02-09   | 2026-05-09   | devops-specialist
```

---

## Emergency Response Procedures

### If Credentials Are Compromised

```bash
# 1. IMMEDIATE: Stop all services
sudo systemctl stop cohezion-mcp
sudo systemctl stop cohezion-api

# 2. Revoke compromised credential
# (contact provider immediately)

# 3. Rotate new credential
# (follow Phase 1 rotation steps)

# 4. Check logs for unauthorized access
grep "401\|403" logs/audit.log | wc -l

# 5. Restart services with new credentials
sudo systemctl start cohezion-mcp
sudo systemctl start cohezion-api

# 6. Monitor for suspicious activity
tail -f logs/audit.log

# 7. Post-incident review
# Document what happened and how to prevent
```

**Response Time Target**: <15 minutes
**Recovery Time Target**: <30 minutes

---

## Sign-Off Checklist

Before Phase 5B.1 deployment, verify:

- [ ] Phase 1: All 8 credentials rotated
- [ ] Phase 1: File permissions set to 600
- [ ] Phase 1: No secrets in git history
- [ ] Phase 2: APIKeyAuth middleware deployed
- [ ] Phase 2: TLS/HTTPS enabled
- [ ] Phase 2: Audit logging active
- [ ] Phase 2: CORS restricted to trusted domains
- [ ] Phase 2: Pre-commit hooks installed
- [ ] All security tests passing
- [ ] All API tests passing (401 when missing key)
- [ ] Credential inventory documented
- [ ] Team trained on procedures

---

**Status**: READY TO IMPLEMENT
**Owner**: DevOps/Security Team
**Blocking**: YES - Cannot deploy Phase 5B until complete
**Timeline**: 6 hours total (Phase 1-2)
**Next Review**: Post-deployment (Phase 3)

