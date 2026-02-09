# Security Remediation Checklist
**Task #18 - Audit Security & Permission Model**
**Status**: IDENTIFIED - Ready for Implementation
**Prepared by**: security-auditor (Agent #20)
**Date**: 2026-02-09

---

## Quick Start: CRITICAL FIXES (Must Do Today)

### Immediate Actions (Next 2 Hours)

These are blocking issues that prevent production deployment:

- [ ] **STOP**: Do NOT run MCP server in production until these are fixed
- [ ] **Secrets**: Rotate ALL secrets in .env files immediately
  - [ ] SUDO_PASSWORD → generate new strong password (openssl rand -base64 32)
  - [ ] KEPLER_WALLET_KEY → rotate in wallet management
  - [ ] DUCKDNS_TOKEN → regenerate in DuckDNS dashboard
  - [ ] BLUEQUBIT_API_TOKEN → request new token
  - [ ] HUGGING_FACE_API_TOKEN → regenerate in HF settings
  - [ ] GOOGLE_SHEETS_TOKEN_JSON → regenerate OAuth token
  - [ ] ANTHROPIC_API_KEY → rotate if used

- [ ] **Authentication**: Apply API key authentication middleware
  - File: `cloud-vault-mcp/src/mcp_server/main.py`
  - Location: Line 39-42 (create_server call)
  - Action: Wrap `mcp_app` with `APIKeyAuth(mcp_app, config.api_key)`
  - Test: Verify Bearer token is required on all endpoints

- [ ] **File Permissions**: Restrict .env files
  - [ ] `chmod 600 /home/mike-anderson/dev/cohezion/.env`
  - [ ] `chmod 600 /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env`
  - Verify: `ls -la` shows `-rw-------`

- [ ] **Git Prevention**: Add pre-commit hook
  - Create: `.git/hooks/pre-commit`
  - Content: Check for patterns like `password=`, `token=`, `key=`
  - Make executable: `chmod +x .git/hooks/pre-commit`

---

## Phase 1: URGENT (2 hours)
**Scope**: Stop bleeding vulnerabilities, enforce minimum security

### 1. Secret Management
- [ ] Generate 20+ character random passwords for all secrets
  ```bash
  openssl rand -base64 32
  ```
- [ ] Update `.env` with new secrets (DO NOT commit)
- [ ] Verify old secrets are revoked:
  - [ ] SUDO_PASSWORD changed in /etc/sudoers
  - [ ] API tokens revoked in services
  - [ ] Wallet key rotated
  - [ ] OAuth tokens refreshed
- [ ] Document secret rotation in vault

### 2. API Authentication
- [ ] Apply APIKeyAuth middleware in main.py
  ```python
  from .auth import APIKeyAuth

  mcp_app = mcp.streamable_http_app
  if config.api_key:
      mcp_app = APIKeyAuth(mcp_app, config.api_key)
  ```
- [ ] Test with curl:
  ```bash
  # Should fail (no auth)
  curl http://localhost:8360/vault_read -H "Content-Type: application/json" -d '{"path":"test"}'

  # Should succeed (with auth)
  curl http://localhost:8360/vault_read \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"path":"test"}'
  ```
- [ ] Update `.env.example` to show Bearer token format
- [ ] Document API key format and generation in README

### 3. File System Security
- [ ] Set .env permissions to 600:
  ```bash
  chmod 600 .env cloud-vault-mcp/.env
  ```
- [ ] Verify no other users can read:
  ```bash
  ls -la .env  # Should show -rw------- or -rw-r----- (owner only)
  ```
- [ ] Check git history for exposed secrets:
  ```bash
  git log -p .env | grep -E "password|token|key" | head -20
  ```
  If found, secrets are already compromised - rotate immediately

### 4. Pre-commit Hook
- [ ] Create `.git/hooks/pre-commit`:
  ```bash
  #!/bin/bash
  # Prevent committing secrets
  git diff --cached | grep -E "(password|api.?key|secret|token.*=)" && {
    echo "ERROR: Potential secret detected in staged changes"
    echo "Do not commit credentials to git"
    exit 1
  }
  exit 0
  ```
- [ ] Make executable: `chmod +x .git/hooks/pre-commit`
- [ ] Test it works:
  ```bash
  echo "TEST_PASSWORD=secret" >> .env
  git add .env
  git commit -m "test"  # Should fail
  ```

### 4. CORS Restriction
- [ ] Update `.env`:
  ```
  CORS_ORIGINS=http://localhost:3000,http://localhost:8360
  ```
- [ ] For production:
  ```
  CORS_ORIGINS=https://vault.example.com
  ```
- [ ] Test CORS headers are set correctly

### 5. Documentation
- [ ] Create `.env.example` with template (no secrets):
  ```
  # API Authentication
  MCP_API_KEY=<generate with: python -c "import hashlib,os; print(hashlib.sha256(os.urandom(32)).hexdigest())">

  # Server Configuration
  MCP_HOST=127.0.0.1
  MCP_PORT=8360
  VAULT_PATH=/path/to/vault

  # Security
  CORS_ORIGINS=http://localhost:3000
  ```
- [ ] Update README with security checklist
- [ ] Add SECURITY.md with vulnerability reporting process

**Estimated Time**: 2 hours
**Risk Reduction**: 🔴 CRITICAL → 🟠 HIGH (API is now authenticated, but other issues remain)

---

## Phase 2: HIGH PRIORITY (4 hours)
**Scope**: Add audit trail, fix encryption, improve access control

### 6. Audit Logging
- [ ] Create audit logging middleware in `mcp_server/audit.py`:
  ```python
  from datetime import datetime
  from starlette.middleware.base import BaseHTTPMiddleware
  import json

  class AuditLoggingMiddleware(BaseHTTPMiddleware):
      def __init__(self, app, logger):
          super().__init__(app)
          self.logger = logger

      async def dispatch(self, request, call_next):
          timestamp = datetime.utcnow().isoformat()
          client_ip = request.client.host if request.client else "unknown"
          path = request.url.path
          method = request.method

          # Log request
          self.logger.info(json.dumps({
              "timestamp": timestamp,
              "event": "request",
              "client_ip": client_ip,
              "method": method,
              "path": path,
          }))

          response = await call_next(request)

          # Log response
          self.logger.info(json.dumps({
              "timestamp": timestamp,
              "event": "response",
              "client_ip": client_ip,
              "status": response.status_code,
              "path": path,
          }))

          return response
  ```
- [ ] Apply middleware in main.py
- [ ] Configure logging to file:
  ```python
  logging.basicConfig(
      filename="/var/log/vault-mcp-audit.log",
      level=logging.INFO,
      format="%(message)s"
  )
  ```
- [ ] Test logs are written:
  ```bash
  curl -X POST http://localhost:8360/vault_read \
    -H "Authorization: Bearer YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"path":"test"}'
  tail -1 /var/log/vault-mcp-audit.log
  ```

### 7. Vault Operation Logging
- [ ] Add logging to each vault tool in `server.py`:
  ```python
  @mcp.tool()
  def vault_read(path: str) -> str:
      logger.info(f"VAULT_OPERATION operation=read path={path}", extra={
          'timestamp': datetime.utcnow().isoformat(),
          'operation': 'read',
          'path': path,
          'type': 'vault_access',
      })
      try:
          return vault.read(path)
      except Exception as e:
          logger.error(f"VAULT_ERROR operation=read path={path} error={e}")
          raise
  ```
- [ ] Test logging captures all operations
- [ ] Verify logs don't contain sensitive data (avoid logging content)

### 8. Path Traversal Fix
- [ ] Update `vault_ops.py` `_resolve()` method:
  ```python
  def _resolve(self, path: str) -> Path:
      """Resolve a vault-relative path safely."""
      # Reject dangerous patterns
      if ".." in path or path.startswith("/"):
          raise ValueError(f"Invalid path: {path}")

      target = self.vault_path / path
      resolved = target.resolve()

      # Use pathlib's relative_to for safe comparison
      try:
          resolved.relative_to(self.vault_path)
      except ValueError:
          raise ValueError(f"Path escapes vault: {path}")

      # Reject symlinks
      if any(part.is_symlink() for part in resolved.parents):
          raise ValueError(f"Symlink traversal not allowed: {path}")

      return resolved
  ```
- [ ] Test with malicious paths:
  ```bash
  # Should fail
  vault_read("../../../etc/passwd")
  vault_read("/etc/passwd")
  vault_read("decision/../../etc/passwd")
  ```

### 9. TLS/HTTPS Configuration
- [ ] Create self-signed certificate (for dev):
  ```bash
  openssl req -x509 -newkey rsa:4096 -nodes \
    -out cert.pem -keyout key.pem -days 365
  ```
- [ ] Update `.env`:
  ```
  SSL_KEYFILE=/path/to/key.pem
  SSL_CERTFILE=/path/to/cert.pem
  ```
- [ ] Update `config.py`:
  ```python
  ssl_keyfile: str = field(default_factory=lambda: os.environ.get("SSL_KEYFILE"))
  ssl_certfile: str = field(default_factory=lambda: os.environ.get("SSL_CERTFILE"))
  ```
- [ ] Update `main.py`:
  ```python
  if config.api_key and not (config.ssl_keyfile and config.ssl_certfile):
      raise RuntimeError("TLS required for production (API key is set)")

  uvicorn.run(
      app,
      host=config.host,
      port=config.port,
      ssl_keyfile=config.ssl_keyfile,
      ssl_certfile=config.ssl_certfile,
  )
  ```
- [ ] Test HTTPS works:
  ```bash
  curl -k --cert cert.pem https://localhost:8360/health
  ```

### 10. CORS & Host Validation
- [ ] Verify TrustedHostMiddleware is applied:
  ```python
  if "*" not in config.allowed_hosts:
      app = TrustedHostMiddleware(app, allowed_hosts=config.allowed_hosts)
  ```
- [ ] Update `.env.example`:
  ```
  CORS_ORIGINS=https://vault.example.com
  ALLOWED_HOSTS=localhost,vault.example.com
  ```
- [ ] Test CORS rejection:
  ```bash
  curl -H "Origin: http://evil.com" http://localhost:8360/vault_read
  # Should return CORS error or 400
  ```

### 11. Security Tests
- [ ] Create `tests/test_security.py`:
  ```python
  def test_auth_required():
      response = client.get("/vault_read")
      assert response.status_code == 401  # Unauthorized

  def test_cors_restricted():
      response = client.options("/vault_read",
          headers={"Origin": "http://evil.com"})
      assert "evil.com" not in response.headers.get("Access-Control-Allow-Origin", "")

  def test_path_traversal_blocked():
      with pytest.raises(ValueError):
          vault._resolve("../../../etc/passwd")

  def test_audit_logging():
      vault.read("decisions/test.md")
      # Check audit log contains the operation
  ```
- [ ] Run tests: `uv run pytest tests/test_security.py -v`
- [ ] All tests must pass

**Estimated Time**: 4 hours
**Risk Reduction**: 🟠 HIGH → 🟡 MEDIUM (encrypted, authenticated, auditable)

---

## Phase 3: MEDIUM PRIORITY (8 hours)
**Scope**: Harden against memory attacks, add monitoring

### 12. Memory Security
- [ ] Implement secure credential handling:
  ```python
  import secrets
  from cryptography.fernet import Fernet

  class SecureConfig:
      def __init__(self, api_key: str):
          self._key = secrets.token_bytes(32)
          self._cipher = Fernet(Fernet.generate_key())
          self._api_key_encrypted = self._cipher.encrypt(api_key.encode())

      def get_api_key(self) -> str:
          return self._cipher.decrypt(self._api_key_encrypted).decode()

      def __del__(self):
          # Attempt to clear on exit
          if hasattr(self, '_api_key_encrypted'):
              del self._api_key_encrypted
          if hasattr(self, '_cipher'):
              del self._cipher
  ```
- [ ] Clear subprocess output:
  ```python
  def _get_token(self) -> str:
      result = subprocess.run([...], capture_output=True, text=True)
      token = result.stdout.strip()
      # Clear buffers
      result.stdout = ""
      del result
      return token
  ```
- [ ] Use secure string library: pip install secure-string
- [ ] Test memory is cleared: Run valgrind or similar tool

### 13. Rate Limiting
- [ ] Install slowapi: `uv add slowapi`
- [ ] Implement rate limiting:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)
  app = limiter.limit("100/minute")(app)
  ```
- [ ] Apply per-endpoint limits:
  ```python
  @limiter.limit("10/minute")
  def vault_write(...):
      ...
  ```
- [ ] Test rate limiting:
  ```bash
  for i in {1..101}; do curl ...; done
  # Request 101 should be rate limited
  ```

### 14. Audit Log Management
- [ ] Implement log rotation:
  ```python
  from logging.handlers import RotatingFileHandler

  handler = RotatingFileHandler(
      "/var/log/vault-mcp-audit.log",
      maxBytes=10485760,  # 10MB
      backupCount=90,  # Keep 90 days if daily
  )
  logger.addHandler(handler)
  ```
- [ ] Implement audit log archival (90+ days):
  - Upload old logs to S3/GCS
  - Setup CloudWatch/DataDog shipping
- [ ] Verify retention: Check oldest log file is >90 days old

### 15. Network Security
- [ ] Change default host (0.0.0.0 → 127.0.0.1):
  ```python
  host: str = field(default_factory=lambda: os.environ.get("MCP_HOST", "127.0.0.1"))
  ```
- [ ] Document reverse proxy requirement in README:
  ```markdown
  ## Production Deployment

  MCP server binds to 127.0.0.1:8360 by default (localhost only).
  For remote access, use a reverse proxy:

  - nginx with TLS termination
  - AWS API Gateway
  - Cloud Run with IAM authentication
  ```
- [ ] Create nginx.conf example:
  ```nginx
  upstream vault_mcp {
    server 127.0.0.1:8360;
  }

  server {
    listen 443 ssl http2;
    server_name vault.example.com;

    ssl_certificate /etc/letsencrypt/live/vault.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vault.example.com/privkey.pem;

    location / {
      auth_request /auth;
      proxy_pass https://vault_mcp;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
  }
  ```
- [ ] Document in deployment guide

### 16. Monitoring & Alerting
- [ ] Setup alerts for security events:
  - [ ] Auth failures (401 responses)
  - [ ] Rate limit exceeded (429 responses)
  - [ ] Path traversal attempts (400 with "escapes vault")
  - [ ] Large responses (data exfiltration attempts)
- [ ] Create CloudWatch/DataDog dashboard:
  ```
  - Failed auth attempts per minute
  - Audit log volume
  - API latency (detect slowloris attacks)
  - Rate-limited requests
  ```
- [ ] Setup email/Slack alerts for critical events

**Estimated Time**: 8 hours
**Risk Reduction**: 🟡 MEDIUM → 🟢 LOW-MEDIUM (hardened, monitored)

---

## Phase 4: ONGOING
**Scope**: Continuous security improvements

### 17. Code Review Process
- [ ] Add security code review checklist:
  - [ ] No hardcoded secrets
  - [ ] All user input validated
  - [ ] SQL injection protection (if applicable)
  - [ ] Authentication/authorization checked
  - [ ] Sensitive data not logged
  - [ ] Error messages don't leak information

### 18. Dependency Scanning
- [ ] Install Snyk: `npm install -g snyk` or `pip install snyk`
- [ ] Setup in CI/CD:
  ```bash
  snyk test --severity-threshold=high
  ```
- [ ] Enable automatic updates for critical vulnerabilities
- [ ] Review Dependabot alerts weekly

### 19. Penetration Testing
- [ ] Schedule quarterly security assessments
- [ ] Test against OWASP Top 10:
  - [ ] Injection attacks
  - [ ] Broken authentication
  - [ ] Sensitive data exposure
  - [ ] XML external entities (XXE)
  - [ ] Broken access control
  - [ ] Cross-site request forgery (CSRF)
  - [ ] Using components with known vulnerabilities
  - [ ] Insecure deserialization
  - [ ] Using components with known vulnerabilities
  - [ ] Insufficient logging

### 20. Security Training
- [ ] Team training on:
  - [ ] Secure coding practices
  - [ ] Secret management
  - [ ] OWASP Top 10
  - [ ] Incident response
- [ ] Document security policies:
  - [ ] Password policy
  - [ ] API key rotation schedule
  - [ ] Incident reporting process
  - [ ] Breach notification timeline

**Estimated Time**: Ongoing (1-2 hours/week)
**Risk Reduction**: Continuous improvement toward 🟢 EXCELLENT

---

## Verification Checklist

After completing all phases, verify:

### Phase 1 Complete
- [ ] `curl localhost:8360/vault_read` returns 401 (no auth required)
- [ ] With Bearer token, request succeeds
- [ ] .env file has 600 permissions
- [ ] Pre-commit hook prevents secret commits
- [ ] All secrets have been rotated

### Phase 2 Complete
- [ ] Audit log file created and growing
- [ ] Path traversal tests pass
- [ ] HTTPS requests work with TLS certificate
- [ ] CORS header validation works
- [ ] All security tests pass (100%)

### Phase 3 Complete
- [ ] Rate limiting blocks 101st request per minute
- [ ] Audit logs older than 90 days are archived
- [ ] Server binds to 127.0.0.1 by default
- [ ] Nginx reverse proxy configured
- [ ] CloudWatch/DataDog alerts configured

### Phase 4 Complete
- [ ] Security code review process documented
- [ ] Snyk tests passing
- [ ] Penetration test results reviewed
- [ ] Team trained on security practices
- [ ] Security policy documented

---

## Sign-Off

**Phase 1 Completion**: _________________ (Date)
**Phase 2 Completion**: _________________ (Date)
**Phase 3 Completion**: _________________ (Date)
**Phase 4 Ongoing**: _________________ (Date)

**Verified by**: _________________ (Security Lead)
**Approved by**: _________________ (Team Lead)

---

## Related Documents

- **SECURITY_AUDIT_REPORT.md** - Complete technical analysis
- **SECURITY_AUDIT_EXECUTIVE_SUMMARY.md** - Executive overview
- **TASK_18_SECURITY_AUDIT_SUMMARY.txt** - Quick reference
- **.env.example** - Configuration template (no secrets)
- **SECURITY.md** - Vulnerability reporting policy

---

**Last Updated**: 2026-02-09
**Status**: READY FOR IMPLEMENTATION
**Assigned To**: Backend team (Phase 1-2), DevOps team (Phase 2-3)
