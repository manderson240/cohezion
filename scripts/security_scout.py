import json
import logging
import os
import re
from pathlib import Path

from cohezion.security.audit import get_audit_logger
from cohezion.security.vault import get_vault


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SecurityScout")

REPO_ROOT = Path(__file__).parent.parent.resolve()

# Common Secret Patterns
SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google Cloud API Key"),
    (re.compile(r"sk-[a-zA-Z0-9]{48}"), "OpenAI API Key"),
    (re.compile(r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"), "Slack Token"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"sq0csp-[0-9A-Za-z-_]{43}"), "Square Access Token"),
    (re.compile(r"access_key_id\s*=\s*['\"][A-Z0-9]{20}['\"]"), "AWS Access Key ID"),
    (
        re.compile(r"secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"),
        "AWS Secret Access Key",
    ),
    (re.compile(r"PRIVATE\s+KEY"), "Private Key Descriptor"),
    (re.compile(r"BEGIN\s+RSA\s+PRIVATE\s+KEY"), "RSA Private Key"),
    (re.compile(r"BEGIN\s+OPENSSH\s+PRIVATE\s+KEY"), "OpenSSH Private Key"),
]


def audit_secrets():
    """Scan the repository for potential hardcoded secrets."""
    logger.info("🔍 Scanning for hardcoded secrets...")
    found_secrets = []

    # Exclude directories that shouldn't be scanned
    exclude_dirs = {".git", ".venv", "__pycache__", "node_modules", "logs", ".archive"}

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in {".py", ".json", ".env", ".md", ".sh"}:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            for pattern, name in SECRET_PATTERNS:
                                if pattern.search(line):
                                    found_secrets.append(
                                        {
                                            "file": str(file_path.relative_to(REPO_ROOT)),
                                            "line": i + 1,
                                            "type": name,
                                        }
                                    )
                except Exception as e:
                    logger.error(f"Failed to scan {file_path}: {e}")

    if found_secrets:
        logger.warning(f"⚠️ Found {len(found_secrets)} potential secrets!")
        for s in found_secrets:
            logger.warning(f"  - {s['type']} in {s['file']}:{s['line']}")
    else:
        logger.info("✅ No obvious secrets found.")
    return found_secrets


def audit_logs():
    """Analyze audit logs for security anomalies."""
    logger.info("📜 Analyzing audit logs for anomalies...")
    audit_logger = get_audit_logger()
    events = audit_logger.get_recent_events(limit=1000)

    security_events = [e for e in events if e.get("event_type") == "security"]
    failures = [e for e in events if e.get("status") == "failure"]
    blocked = [e for e in events if e.get("event_type") == "security" and e.get("status") == "blocked"]

    logger.info(f" - Recent security events: {len(security_events)}")
    logger.info(f" - Auth failures: {len(failures)}")
    logger.info(f" - Blocked injections: {len(blocked)}")

    if len(blocked) > 50:
        logger.error("🚨 High frequency of blocked injections detected! Possible adversarial attack.")

    return {
        "security_events": len(security_events),
        "auth_failures": len(failures),
        "blocked_injections": len(blocked),
    }


def verify_vault():
    """Verify that the vault is accessible and functioning."""
    logger.info("🔐 Verifying vault integrity...")
    vault = get_vault()
    if vault.is_locked():
        logger.warning("Vault is locked (Standard state for non-interactive check).")
    else:
        logger.info("Vault is unlocked.")
    return not vault.is_locked()


def main():
    logger.info("🛡️ Initiating Security Audit...")
    secrets = audit_secrets()
    logs = audit_logs()
    vault_status = verify_vault()

    summary = {
        "secrets_found": len(secrets),
        "audit_summary": logs,
        "vault_unlocked": vault_status,
    }

    # Save report
    report_path = REPO_ROOT / "reports" / "security_audit.json"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"✅ Security Audit Complete. Report saved to {report_path}")


if __name__ == "__main__":
    main()
