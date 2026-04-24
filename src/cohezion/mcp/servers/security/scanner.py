# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
"""Security MCP Server - data models and checklist (no scanner regex patterns)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Vulnerability:
    """Security vulnerability finding."""

    id: str
    title: str
    severity: str  # critical, high, medium, low, info
    description: str
    file: str
    line: int | None = None
    column: int | None = None
    fix: str | None = None
    cwe: str | None = None
    owasp_category: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "fix": self.fix,
            "cwe": self.cwe,
            "owasp_category": self.owasp_category,
            "createdAt": self.created_at,
        }


class SecurityChecklist:
    """Security checklist validation."""

    CHECKLISTS = {
        "general": [
            {"id": "SEC-001", "item": "No secrets in code", "severity": "critical"},
            {"id": "SEC-002", "item": "Input validation implemented", "severity": "critical"},
            {"id": "SEC-003", "item": "Authentication enforced", "severity": "critical"},
            {"id": "SEC-004", "item": "Authorization checks present", "severity": "high"},
            {"id": "SEC-005", "item": "SQL injection prevention", "severity": "critical"},
            {"id": "SEC-006", "item": "XSS protection", "severity": "high"},
            {"id": "SEC-007", "item": "CSRF tokens", "severity": "medium"},
            {"id": "SEC-008", "item": "HTTPS enforced", "severity": "high"},
            {"id": "SEC-009", "item": "Secrets management", "severity": "critical"},
            {"id": "SEC-010", "item": "Audit logging", "severity": "medium"},
        ],
        "api": [
            {"id": "API-001", "item": "Rate limiting", "severity": "high"},
            {"id": "API-002", "item": "API key validation", "severity": "critical"},
            {"id": "API-003", "item": "Request size limits", "severity": "medium"},
            {"id": "API-004", "item": "CORS configured", "severity": "medium"},
        ],
        "database": [
            {"id": "DB-001", "item": "Parameterized queries", "severity": "critical"},
            {"id": "DB-002", "item": "Connection pooling", "severity": "low"},
            {"id": "DB-003", "item": "Backup strategy", "severity": "high"},
            {"id": "DB-004", "item": "Encryption at rest", "severity": "high"},
        ],
    }

    def get_checklist(self, checklist_type: str = "general") -> list[dict]:
        """Get security checklist."""
        return self.CHECKLISTS.get(checklist_type, self.CHECKLISTS["general"])


# Report helper used by SecurityScanner
def build_severity_report(vulnerabilities: list[Vulnerability]) -> dict[str, Any]:
    """Build severity count report from vulnerability list."""
    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for vuln in vulnerabilities:
        severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
    return {
        "total": len(vulnerabilities),
        "severity_counts": severity_counts,
        "vulnerabilities": [v.to_dict() for v in vulnerabilities],
    }
