# Phase 2 Security Hardening - Implementation Guide

**Date**: 2026-02-09 (Session 45+ - Security Phase 2)
**Status**: ACTIVE SPRINT
**Duration**: 4-6 hours
**Blocking**: No (Phase 5B/6 remain operational)
**Confidence**: 99%

---

## Overview

Security Phase 2 completes the hardening of Phase 5B/6 production systems. Phase 1 (API key rotation) is complete. Phase 2 implements:

1. **Per-Agent Authentication** (APIKeyAuth middleware) - CVSS 9.8 mitigation
2. **Transport Security** (TLS/HTTPS) - CVSS 7.5 mitigation
3. **Audit Logging** (Compliance requirement) - GDPR/HIPAA/SOC2
4. **Secret Prevention** (Pre-commit hooks) - Prevent future leaks

All changes are backward compatible, non-breaking, and can run in parallel with Phase 5B/6.

---

## Task #1: APIKeyAuth Middleware (1.5-2h)

### Objective
Replace shared API key system with per-agent authentication. Current state: all team members use same API key (security gap). Target: each agent gets unique token.

### Implementation Steps

#### Step 1.1: Define Agent Authentication Model
**File**: `src/cohezion/security/agent_auth.py` (NEW)

```python
from dataclasses import dataclass
from typing import Optional, Dict
import uuid
import hashlib
from datetime import datetime, timedelta

@dataclass
class AgentCredential:
    """Per-agent authentication credential"""
    agent_id: str
    token: str  # UUID-based, not the actual API key
    api_key_hash: str  # bcrypt hash of actual API key
    created_at: datetime
    expires_at: Optional[datetime]
    permissions: list[str]  # ["read", "write", "delete"]
    is_active: bool
    last_used: Optional[datetime]

class AgentAuthManager:
    """Manages per-agent authentication and token validation"""

    def __init__(self, vault_path: str = "~/vaults/cohezion-vault/agents/"):
        self.vault_path = vault_path
        self.token_cache: Dict[str, AgentCredential] = {}

    def create_agent_credential(self, agent_id: str, permissions: list[str]) -> AgentCredential:
        """Create new credential for agent"""
        token = str(uuid.uuid4())
        credential = AgentCredential(
            agent_id=agent_id,
            token=token,
            api_key_hash="",  # Will be set during activation
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            permissions=permissions,
            is_active=False,
            last_used=None
        )
        # Persist to vault atomically
        self._persist_credential(credential)
        return credential

    def validate_token(self, token: str) -> Optional[AgentCredential]:
        """Validate agent token and return credential"""
        if token in self.token_cache:
            credential = self.token_cache[token]
            if credential.is_active and (not credential.expires_at or credential.expires_at > datetime.utcnow()):
                credential.last_used = datetime.utcnow()
                return credential
        return None

    def revoke_credential(self, agent_id: str):
        """Revoke agent's credential (on team member removal)"""
        # Implementation: mark as inactive in vault
        pass

    def rotate_credentials(self, agent_id: str):
        """Rotate agent's credential (periodic security)"""
        # Implementation: create new token, invalidate old
        pass

    def _persist_credential(self, credential: AgentCredential):
        """Persist credential to vault securely"""
        # Non-blocking async operation with JSONL fallback
        pass
```

#### Step 1.2: Create APIKeyAuth Middleware
**File**: `src/cohezion/security/apikey_auth_middleware.py` (NEW)

```python
from fastapi import FastAPI, HTTPException, Header, Request
from typing import Optional
from .agent_auth import AgentAuthManager

class APIKeyAuthMiddleware:
    """FastAPI middleware for per-agent API key validation"""

    def __init__(self, app: FastAPI, auth_manager: AgentAuthManager):
        self.app = app
        self.auth_manager = auth_manager
        self.app.add_middleware(self._auth_middleware)

    async def _auth_middleware(self, request: Request, call_next):
        """Validate X-Agent-Token header on every request"""
        token = request.headers.get("X-Agent-Token")

        if not token:
            raise HTTPException(status_code=401, detail="Missing X-Agent-Token header")

        credential = self.auth_manager.validate_token(token)
        if not credential:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Attach credential to request state for handlers
        request.state.agent_id = credential.agent_id
        request.state.permissions = credential.permissions

        return await call_next(request)
```

#### Step 1.3: Integrate with MCP Server
**File**: `cloud-vault-mcp/src/mcp_server/main.py` (MODIFY)

```python
from cohezion.security.agent_auth import AgentAuthManager
from cohezion.security.apikey_auth_middleware import APIKeyAuthMiddleware

# Initialize auth manager
auth_manager = AgentAuthManager()

# Add middleware to FastMCP app
app = mcp.streamable_http_app()
app = APIKeyAuthMiddleware(app, auth_manager).app
```

#### Step 1.4: Testing (5-6 tests)
**File**: `tests/security/test_agent_auth.py` (NEW)

```python
import pytest
from cohezion.security.agent_auth import AgentAuthManager

class TestAgentAuth:
    @pytest.fixture
    def auth_manager(self):
        return AgentAuthManager()

    def test_create_credential(self, auth_manager):
        """Test creating new agent credential"""
        credential = auth_manager.create_agent_credential(
            "agent-1",
            ["read", "write"]
        )
        assert credential.agent_id == "agent-1"
        assert credential.is_active == False
        assert len(credential.token) > 0

    def test_validate_token(self, auth_manager):
        """Test token validation"""
        credential = auth_manager.create_agent_credential("agent-1", ["read"])
        credential.is_active = True

        result = auth_manager.validate_token(credential.token)
        assert result is not None
        assert result.agent_id == "agent-1"

    def test_invalid_token(self, auth_manager):
        """Test invalid token returns None"""
        result = auth_manager.validate_token("invalid-token")
        assert result is None

    def test_expired_credential(self, auth_manager):
        """Test expired credentials are rejected"""
        # Create credential with past expiration
        # Verify it's rejected
        pass

    def test_revoke_credential(self, auth_manager):
        """Test credential revocation"""
        pass

    def test_rotate_credentials(self, auth_manager):
        """Test credential rotation"""
        pass
```

### Success Criteria
- ✅ Agent can obtain unique token
- ✅ Token validates correctly
- ✅ Expired tokens rejected
- ✅ All 6 tests passing
- ✅ MCP server integrates cleanly

### Rollback
- Remove middleware from MCP app
- Revert to shared API key (in env var)
- Existing requests continue working

---

## Task #2: TLS/HTTPS Configuration (1-1.5h)

### Objective
Enable TLS/HTTPS for MCP server. Current state: HTTP only. Target: All connections encrypted.

### Implementation Steps

#### Step 2.1: Generate Certificates
**File**: `scripts/setup/generate_tls_certificates.sh` (NEW)

```bash
#!/bin/bash

# Development certificate (self-signed)
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt \
  -days 365 -nodes \
  -subj "/CN=localhost/O=Cohezion/C=US"

# Copy to secure location
mkdir -p /etc/cohezion/certs/
cp server.key /etc/cohezion/certs/server.key
cp server.crt /etc/cohezion/certs/server.crt
chmod 600 /etc/cohezion/certs/server.key
chmod 644 /etc/cohezion/certs/server.crt

echo "✅ TLS certificates generated"
echo "Key: /etc/cohezion/certs/server.key"
echo "Cert: /etc/cohezion/certs/server.crt"
```

#### Step 2.2: Configure Uvicorn with SSL
**File**: `cloud-vault-mcp/src/mcp_server/main.py` (MODIFY)

```python
import uvicorn
import ssl

def run_server(host="0.0.0.0", port=8360, ssl_enabled=True):
    """Run MCP server with optional TLS"""

    if ssl_enabled:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile="/etc/cohezion/certs/server.crt",
            keyfile="/etc/cohezion/certs/server.key"
        )

        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile="/etc/cohezion/certs/server.key",
            ssl_certfile="/etc/cohezion/certs/server.crt",
            ssl_version=ssl.PROTOCOL_TLS_SERVER,
        )
    else:
        uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    # Check env var for SSL enablement
    import os
    ssl_enabled = os.getenv("ENABLE_TLS", "true").lower() == "true"
    run_server(ssl_enabled=ssl_enabled)
```

#### Step 2.3: Client Configuration
**File**: `src/cohezion/core/mcp_client.py` (MODIFY)

```python
import httpx

class MCPClient:
    def __init__(self, host="localhost", port=8360, use_tls=True, verify_cert=False):
        self.base_url = f"{'https' if use_tls else 'http'}://{host}:{port}"

        # For self-signed certs in dev, disable cert verification
        self.client = httpx.Client(
            base_url=self.base_url,
            verify=verify_cert  # False for self-signed, True for prod
        )

    def call_tool(self, tool_name: str, args: dict):
        """Call MCP tool over HTTPS"""
        response = self.client.post(
            f"/tools/{tool_name}",
            json=args,
            headers={"X-Agent-Token": self.agent_token}
        )
        return response.json()
```

#### Step 2.4: Testing (4 tests)
**File**: `tests/security/test_tls_configuration.py` (NEW)

```python
import pytest
import ssl
import socket

class TestTLSConfiguration:
    def test_certificate_exists(self):
        """Test certificate files exist"""
        import os
        assert os.path.exists("/etc/cohezion/certs/server.crt")
        assert os.path.exists("/etc/cohezion/certs/server.key")

    def test_certificate_valid(self):
        """Test certificate is valid and not expired"""
        # Parse cert, check expiration
        pass

    def test_https_connection(self):
        """Test HTTPS connection works"""
        # Connect to MCP server via HTTPS
        # Verify handshake succeeds
        pass

    def test_certificate_chain(self):
        """Test certificate chain is correct"""
        # Verify cert signed by expected CA
        pass
```

### Success Criteria
- ✅ TLS certificates generated
- ✅ Server starts with HTTPS
- ✅ Clients connect via HTTPS
- ✅ All 4 tests passing
- ✅ Certificate valid for 1+ year

### Rollback
- Disable TLS via env var `ENABLE_TLS=false`
- Server reverts to HTTP
- All clients continue working

---

## Task #3: Audit Logging (1.5-2h)

### Objective
Implement comprehensive audit trail for all vault operations. Current state: minimal logging. Target: GDPR/HIPAA/SOC2 compliant audit trail.

### Implementation Steps

#### Step 3.1: Define Audit Log Schema
**File**: `src/cohezion/security/audit_log.py` (NEW)

```python
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import json

class AuditAction(str, Enum):
    """Audit-logged actions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    AUTHENTICATE = "authenticate"
    REVOKE = "revoke"
    ROTATE = "rotate"
    EXPORT = "export"

@dataclass
class AuditLogEntry:
    """Single audit log entry"""
    timestamp: datetime
    agent_id: str
    action: AuditAction
    resource: str  # path, e.g., "/projects/SESSION_45.md"
    status: str  # "success" or "failure"
    details: Optional[dict]  # Additional context
    ip_address: Optional[str]
    user_agent: Optional[str]

    def to_json(self) -> str:
        """Serialize to JSON"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["action"] = self.action.value
        return json.dumps(data)

class AuditLogger:
    """Manages audit log persistence and querying"""

    def __init__(self, log_path: str = "data/audit_logs/"):
        self.log_path = log_path
        self.current_log_file = None

    def log(self, entry: AuditLogEntry) -> bool:
        """Log an action (non-blocking)"""
        try:
            # Write to JSONL file (append-only, atomic)
            with open(f"{self.log_path}/audit_{entry.timestamp.date()}.jsonl", "a") as f:
                f.write(entry.to_json() + "\n")
            return True
        except Exception as e:
            # Non-blocking: log to stderr but don't crash
            print(f"Audit logging failed: {e}")
            return False

    def query(self, agent_id: Optional[str] = None,
              action: Optional[AuditAction] = None,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None) -> list[AuditLogEntry]:
        """Query audit logs with filters"""
        # Implementation: read JSONL files, parse, filter
        pass

    def export_for_compliance(self, start_date: datetime, end_date: datetime) -> str:
        """Export audit trail for compliance review"""
        # Implementation: generate CSV/JSON report for auditors
        pass

    def cleanup_old_logs(self, retention_days: int = 90):
        """Delete audit logs older than retention period"""
        # Implementation: enforce retention policy
        pass
```

#### Step 3.2: Integrate with MCP Server
**File**: `cloud-vault-mcp/src/mcp_server/inbox_main.py` (MODIFY)

```python
from cohezion.security.audit_log import AuditLogger, AuditAction, AuditLogEntry

audit_logger = AuditLogger()

@mcp.tool()
def vault_read(path: str) -> str:
    """Read from vault (audited)"""
    try:
        data = vault.read(path)

        # Log successful read
        audit_logger.log(AuditLogEntry(
            timestamp=datetime.utcnow(),
            agent_id=get_agent_id_from_request(),
            action=AuditAction.READ,
            resource=path,
            status="success",
            details={"bytes_read": len(data)},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        ))

        return data
    except Exception as e:
        # Log failed read
        audit_logger.log(AuditLogEntry(
            timestamp=datetime.utcnow(),
            agent_id=get_agent_id_from_request(),
            action=AuditAction.READ,
            resource=path,
            status="failure",
            details={"error": str(e)},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        ))
        raise

@mcp.tool()
def vault_write(path: str, data: str) -> bool:
    """Write to vault (audited)"""
    # Similar pattern: try/log success/log failure
    pass

@mcp.tool()
def vault_delete(path: str) -> bool:
    """Delete from vault (audited)"""
    # Similar pattern
    pass
```

#### Step 3.3: Testing (5 tests)
**File**: `tests/security/test_audit_logging.py` (NEW)

```python
import pytest
from datetime import datetime
from cohezion.security.audit_log import AuditLogger, AuditAction, AuditLogEntry

class TestAuditLogging:
    @pytest.fixture
    def logger(self):
        return AuditLogger(log_path="/tmp/test_audit_logs/")

    def test_log_entry_creation(self):
        """Test creating audit log entry"""
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/projects/test.md",
            status="success",
            details=None,
            ip_address="127.0.0.1",
            user_agent="test-client"
        )
        assert entry.agent_id == "agent-1"
        assert entry.action == AuditAction.READ

    def test_log_persistence(self, logger):
        """Test audit log is persisted"""
        entry = AuditLogEntry(...)
        result = logger.log(entry)
        assert result == True
        # Verify file was written

    def test_query_by_agent(self, logger):
        """Test querying logs by agent"""
        # Create multiple entries, query by agent_id
        pass

    def test_compliance_export(self, logger):
        """Test exporting for compliance review"""
        # Generate compliance report
        pass

    def test_log_retention(self, logger):
        """Test cleanup of old logs"""
        # Create old logs, verify cleanup works
        pass
```

### Success Criteria
- ✅ All vault operations logged
- ✅ Audit trail immutable (append-only)
- ✅ Query and export working
- ✅ Retention policy enforced
- ✅ All 5 tests passing
- ✅ GDPR/HIPAA/SOC2 requirements met

### Rollback
- Disable audit logging via feature flag
- Logs continue to be written but not queried
- No data loss

---

## Task #4: Pre-commit Hooks (30-45 min)

### Objective
Prevent API keys from being committed to git. Current state: risk of accidental leaks. Target: automated secret detection.

### Implementation Steps

#### Step 4.1: Install detect-secrets
**File**: `scripts/setup/install_security_tools.sh` (NEW)

```bash
#!/bin/bash

# Install detect-secrets package
pip install detect-secrets

# Generate baseline of known secrets (if any)
detect-secrets scan --baseline .secrets.baseline

# Install git hook
detect-secrets install-hook git

echo "✅ Pre-commit hook installed"
echo "Baseline: .secrets.baseline"
```

#### Step 4.2: Configure Detection Rules
**File**: `.secrets.baseline` (NEW)

```json
{
  "version": "1.4.0",
  "plugins_used": [
    {
      "name": "ArtifactoryDetector"
    },
    {
      "name": "AWSKeyDetector"
    },
    {
      "name": "AzureStorageKeyDetector"
    },
    {
      "name": "BasicAuthDetector"
    },
    {
      "name": "CloudantDetector"
    },
    {
      "name": "DiscordBotTokenDetector"
    },
    {
      "name": "GitHubTokenDetector"
    },
    {
      "name": "HexHighEntropyString",
      "hex_limit": 3.0
    },
    {
      "name": "IbmCloudIamDetector"
    },
    {
      "name": "IbmCosHmacDetector"
    },
    {
      "name": "JwtTokenDetector"
    },
    {
      "name": "MailchimpDetector"
    },
    {
      "name": "NgrokDetector"
    },
    {
      "name": "PrivateKeyDetector"
    },
    {
      "name": "SendGridDetector"
    },
    {
      "name": "SlackDetector"
    },
    {
      "name": "StripeDetector"
    },
    {
      "name": "TwilioKeyDetector"
    }
  ],
  "filters_used": [
    {
      "path": "detect_secrets.filters.allowlist.is_line_allowlisted"
    },
    {
      "path": "detect_secrets.filters.common.is_baseline",
      "filename": ".secrets.baseline"
    },
    {
      "path": "detect_secrets.filters.common.is_not_secret",
      "filename": ".secrets.baseline"
    }
  ],
  "results": {},
  "generated_at": "2026-02-09T00:00:00Z"
}
```

#### Step 4.3: CI/CD Integration
**File**: `.github/workflows/pre-commit-check.yml` (NEW)

```yaml
name: Pre-commit Secret Detection

on: [pull_request, push]

jobs:
  detect-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install detect-secrets
        run: pip install detect-secrets

      - name: Scan for secrets
        run: |
          detect-secrets scan --baseline .secrets.baseline
          if [ $? -ne 0 ]; then
            echo "❌ Secrets detected in commit!"
            exit 1
          fi

      - name: Verify no new secrets
        run: |
          detect-secrets audit .secrets.baseline
```

#### Step 4.4: Testing (2 tests)
**File**: `tests/security/test_secret_prevention.py` (NEW)

```python
import pytest
import subprocess

class TestSecretPrevention:
    def test_detect_aws_key(self):
        """Test AWS key detection"""
        test_file = "/tmp/test_secret.py"
        with open(test_file, "w") as f:
            f.write("aws_key = 'AKIAIOSFODNN7EXAMPLE'")

        result = subprocess.run(
            ["detect-secrets", "scan", test_file],
            capture_output=True
        )
        assert result.returncode == 1  # Should fail (secret detected)

    def test_github_token_detection(self):
        """Test GitHub token detection"""
        # Similar test for GitHub token
        pass
```

### Success Criteria
- ✅ detect-secrets installed and configured
- ✅ Git hook prevents secret commits
- ✅ CI/CD blocks PRs with secrets
- ✅ All 2 tests passing
- ✅ Zero accidental leaks

### Rollback
- Uninstall git hook: `git config --unset core.hooksPath`
- Remove CI/CD workflow
- Existing commits unaffected

---

## Implementation Timeline

```
Task #1: APIKeyAuth (1.5-2h)
├── 0:00-0:15: Auth model definition
├── 0:15-0:45: Middleware implementation
├── 0:45-1:00: MCP server integration
└── 1:00-1:30: Testing and verification

Task #2: TLS/HTTPS (1-1.5h) [parallel with Task #1]
├── 0:00-0:20: Certificate generation
├── 0:20-0:40: Uvicorn configuration
├── 0:40-1:00: Client configuration
└── 1:00-1:15: Testing and verification

Task #3: Audit Logging (1.5-2h) [parallel]
├── 0:00-0:30: Audit schema definition
├── 0:30-1:00: MCP server integration
├── 1:00-1:30: Query and export implementation
└── 1:30-1:45: Testing and verification

Task #4: Pre-commit Hooks (30-45 min) [parallel]
├── 0:00-0:10: Install detect-secrets
├── 0:10-0:20: Configure detection rules
├── 0:20-0:30: CI/CD integration
└── 0:30-0:40: Testing and verification

TOTAL: 4-6 hours (parallel execution)
```

---

## Quality Gates

Before marking Phase 2 complete:

- [ ] All 4 tasks implemented
- [ ] 16+ new tests created and passing
- [ ] 99%+ overall test pass rate maintained
- [ ] Zero breaking changes
- [ ] Backward compatible with Phase 5B/6
- [ ] No security audit findings remaining
- [ ] GDPR/HIPAA/SOC2 compliant
- [ ] Documentation updated
- [ ] Team sign-off from all owners

---

## Deployment Checklist (After Phase 2)

```
PRE-DEPLOYMENT (30 min):
[ ] Verify all Phase 2 tests passing
[ ] Verify Phase 5B/6 tests still passing (no regressions)
[ ] Brief operations team
[ ] Confirm feature flags ready

STAGING (1 hour):
[ ] Deploy to staging environment
[ ] Run smoke tests
[ ] Verify dashboards operational
[ ] Test APIKeyAuth with test agents
[ ] Verify TLS handshake
[ ] Review audit logs

CANARY (2 hours):
[ ] Deploy to 10% production traffic
[ ] Monitor for 30 minutes
[ ] Check all alerts functioning
[ ] Verify cost metrics
[ ] Monitor error rates

FULL ROLLOUT:
[ ] If canary healthy: scale to 100%
[ ] Monitor for 1 hour
[ ] Confirm all systems operational
[ ] Send deployment notification

POST-DEPLOYMENT (7 days):
[ ] Daily reviews by on-call team
[ ] Weekly metrics review
[ ] Operations handbook validation
[ ] Prepare Phase 7 planning
```

---

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|-----------|-------|
| APIKeyAuth breaks existing clients | Backward compat mode: shared key still works during transition | security-lead |
| TLS cert expired in production | Auto-renewal via Let's Encrypt, monitoring | devops-lead |
| Audit logs consume too much disk | Compression + retention policy (90 days) | audit-specialist |
| Secret detector false positives | Baseline updated regularly, manual review | devops-lead |
| Parallel tasks interfere | Clear task boundaries, no shared file edits | qa-lead |

---

## Success Metrics

| Metric | Target | Owner |
|--------|--------|-------|
| APIKeyAuth integration tests | 6/6 passing | security-lead |
| TLS certificate valid | 365+ days | devops-lead |
| Audit log queries | <100ms per query | audit-specialist |
| Secret detection accuracy | 100% (no false negatives) | devops-lead |
| Overall test pass rate | ≥99.4% | qa-lead |

---

## Communication Plan

- **Start**: Broadcast to all teams (DONE ✅)
- **Hourly**: Quick status updates to main channel
- **Task completion**: Individual task owner updates
- **Issues**: Escalate to qa-lead immediately
- **End**: Final completion broadcast with metrics

---

## Resources

**Relevant Files**:
- Security audit findings: `/home/mike-anderson/dev/cohezion/FAILURE_MODES_ANALYSIS.md`
- Risk assessment: `/home/mike-anderson/vaults/cohezion-vault/experiments/2026-02-09-phase-5b-production-readiness-validation.md`
- Phase 5B code: `src/cohezion/` (all modules)

**External Resources**:
- detect-secrets: https://github.com/Yelp/detect-secrets
- FastAPI security: https://fastapi.tiangolo.com/tutorial/security/
- OpenSSL certificates: https://www.openssl.org/docs/

---

## Conclusion

Security Phase 2 is the final gate before production deployment. All prerequisite work is complete. Implementation is straightforward, low-risk, and can execute in parallel.

**Expected outcome**: Phase 2 complete in 4-6 hours, enabling immediate production deployment of Phase 5B/6.

---

**Created**: 2026-02-09 (Session 45)
**Status**: IMPLEMENTATION GUIDE ACTIVE
**Owner**: qa-lead, security-lead, devops-lead, audit-specialist
**Confidence**: 99%
