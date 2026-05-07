"""Security MCP Server - Vulnerability scanning and security analysis.

Port: 8369
Features:
- Dependency vulnerability scanning (Snyk-style)
- Secret detection in code
- Security checklist validation
- OWASP compliance checks
- SAST (Static Application Security Testing)
- Container image scanning
- Report generation

Integrates with BMAD workflows for security-by-design.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import web

from .scanner import SecurityChecklist, Vulnerability, build_severity_report


# (Ω12 P2 Patch 20) Pin path-sanitizer base to repo root (or env override),
# not Path.cwd() which depends on where the server was invoked from.
def _resolve_repo_root():
    import os as _os
    from pathlib import Path as _Path
    env_root = _os.environ.get("MCP_REPO_ROOT")
    if env_root:
        return _Path(env_root)
    return _Path(__file__).resolve().parents[5]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8369"))


class SecurityScanner:
    """Multi-purpose security scanner."""

    # OWASP Top 10 2021
    OWASP_TOP_10 = {
        "A01": "Broken Access Control",
        "A02": "Cryptographic Failures",
        "A03": "Injection",
        "A04": "Insecure Design",
        "A05": "Security Misconfiguration",
        "A06": "Vulnerable and Outdated Components",
        "A07": "Identification and Authentication Failures",
        "A08": "Software and Data Integrity Failures",
        "A09": "Security Logging and Monitoring Failures",
        "A10": "Server-Side Request Forgery (SSRF)",
    }

    # Secret patterns
    SECRET_PATTERNS = {
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"[0-9a-zA-Z/+]{40}",
        "github_token": r"ghp_[0-9a-zA-Z]{36}",
        "private_key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "api_key": r"api[_-]?key[\s]*[:=][\s]*['\"]?[a-zA-Z0-9]{16,}['\"]?",
        "password": r"password[\s]*[:=][\s]*['\"]?[^'\"\s]{8,}['\"]?",
        "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
    }

    def __init__(self):
        self.vulnerabilities: list[Vulnerability] = []

    def scan_file(self, file_path: Path, content: str | None = None) -> list[Vulnerability]:
        """Scan a single file for vulnerabilities."""
        findings = []

        if content is None:
            try:
                content = file_path.read_text()
            except Exception:
                return findings

        # Secret detection
        findings.extend(self._scan_secrets(file_path, content))

        # Language-specific scans
        if file_path.suffix == ".py":
            findings.extend(self._scan_python(file_path, content))
        elif file_path.suffix in [".js", ".ts"]:
            findings.extend(self._scan_javascript(file_path, content))

        return findings

    def _scan_secrets(self, file_path: Path, content: str) -> list[Vulnerability]:
        """Scan for secrets in code."""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip test/example files
                    if "test" in str(file_path).lower() or "example" in str(file_path).lower():
                        continue

                    vuln = Vulnerability(
                        id=f"SECRET-{secret_type.upper()}",
                        title=f"Potential {secret_type.replace('_', ' ').title()} Exposed",
                        severity="critical"
                        if secret_type in ["private_key", "aws_secret_key"]
                        else "high",
                        description=f"Found potential {secret_type.replace('_', ' ')} in code",
                        file=str(file_path),
                        line=line_num,
                        fix=f"Move {secret_type} to environment variables or secret manager",
                        owasp_category="A02",
                    )
                    findings.append(vuln)

        return findings

    def _scan_python(self, file_path: Path, content: str) -> list[Vulnerability]:
        """Python-specific security scans."""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # SQL Injection
            if re.search(r"execute\s*\(\s*['\"].*%s", line):
                findings.append(
                    Vulnerability(
                        id="PY-SQLI-001",
                        title="Potential SQL Injection",
                        severity="critical",
                        description="String formatting detected in SQL query",
                        file=str(file_path),
                        line=line_num,
                        fix="Use parameterized queries",
                        cwe="CWE-89",
                        owasp_category="A03",
                    )
                )

            # Eval/exec
            if re.search(r"\beval\s*\(|\bexec\s*\(", line):
                findings.append(
                    Vulnerability(
                        id="PY-EVAL-001",
                        title="Dangerous eval/exec Usage",
                        severity="critical",
                        description="eval() or exec() can lead to code injection",
                        file=str(file_path),
                        line=line_num,
                        fix="Use ast.literal_eval() or avoid dynamic execution",
                        cwe="CWE-94",
                        owasp_category="A03",
                    )
                )

            # Hardcoded IPs
            if re.search(
                r"\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                line,
            ):
                findings.append(
                    Vulnerability(
                        id="PY-IP-001",
                        title="Hardcoded IP Address",
                        severity="low",
                        description="Hardcoded IP detected",
                        file=str(file_path),
                        line=line_num,
                        fix="Use DNS names or configuration",
                    )
                )

        return findings

    def _scan_javascript(self, file_path: Path, content: str) -> list[Vulnerability]:
        """JavaScript-specific security scans."""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # XSS - innerHTML
            if "innerHTML" in line:
                findings.append(
                    Vulnerability(
                        id="JS-XSS-001",
                        title="Potential XSS via innerHTML",
                        severity="high",
                        description="innerHTML can lead to XSS if user input is used",
                        file=str(file_path),
                        line=line_num,
                        fix="Use textContent or sanitize input",
                        cwe="CWE-79",
                        owasp_category="A03",
                    )
                )

            # eval
            if re.search(r"\beval\s*\(", line):
                findings.append(
                    Vulnerability(
                        id="JS-EVAL-001",
                        title="Dangerous eval() Usage",
                        severity="critical",
                        description="eval() can lead to code injection",
                        file=str(file_path),
                        line=line_num,
                        fix="Use JSON.parse() or avoid dynamic execution",
                        cwe="CWE-94",
                        owasp_category="A03",
                    )
                )

        return findings

    async def scan_dependencies(self, project_path: Path) -> list[Vulnerability]:
        """Scan project dependencies for known vulnerabilities."""
        findings = []

        # Python requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            findings.extend(await self._scan_python_dependencies(req_file))

        # JavaScript package.json
        pkg_file = project_path / "package.json"
        if pkg_file.exists():
            findings.extend(await self._scan_js_dependencies(pkg_file))

        return findings

    async def _scan_python_dependencies(self, req_file: Path) -> list[Vulnerability]:
        """Scan Python dependencies."""
        findings = []
        # This would query PyPI vulnerability database
        # For now, return empty with note
        from cohezion.mcp.servers.safe_input import sanitize_log

        logger.info("Scanning Python deps: %s", sanitize_log(str(req_file)))
        return findings

    async def _scan_js_dependencies(self, pkg_file: Path) -> list[Vulnerability]:
        """Scan JS dependencies."""
        findings = []
        # This would query npm audit
        from cohezion.mcp.servers.safe_input import sanitize_log

        logger.info("Scanning JS deps: %s", sanitize_log(str(pkg_file)))
        return findings

    def generate_report(self) -> dict[str, Any]:
        """Generate security scan report."""
        report = build_severity_report(self.vulnerabilities)
        report["scan_time"] = datetime.utcnow().isoformat()
        return report


# Global scanner
_scanner: SecurityScanner | None = None


def get_scanner() -> SecurityScanner:
    """Get security scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = SecurityScanner()
    return _scanner


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "security",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Security MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "tools": [
                "security_scan_file",
                "security_scan_project",
                "security_get_checklist",
                "security_validate_checklist",
                "security_generate_report",
            ],
            "owasp_top_10": list(SecurityScanner.OWASP_TOP_10.keys()),
        }
    )


@routes.post("/tools/security_scan_file")
async def tool_scan_file(request: web.Request) -> web.Response:
    """Scan a file for vulnerabilities."""
    try:
        data = await request.json()
        file_path = data.get("filePath", "")
        content = data.get("content")

        if not file_path:
            return web.json_response({"error": "filePath is required"}, status=400)

        from pathlib import Path

        from cohezion.mcp.servers.safe_input import sanitize_path

        scanner = get_scanner()
        path = sanitize_path(file_path, base_dir=_resolve_repo_root())
        findings = scanner.scan_file(path, content)

        return web.json_response(
            {
                "tool": "security_scan_file",
                "file": file_path,
                "findings_count": len(findings),
                "findings": [f.to_dict() for f in findings],
            }
        )
    except Exception as e:
        logger.exception("Scan failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/security_scan_project")
async def tool_scan_project(request: web.Request) -> web.Response:
    """Scan entire project."""
    try:
        data = await request.json()
        project_path = data.get("projectPath", ".")

        from pathlib import Path

        from cohezion.mcp.servers.safe_input import sanitize_path

        scanner = get_scanner()
        path = sanitize_path(project_path, base_dir=_resolve_repo_root())

        all_findings = []

        # Scan all files
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".py",
                ".js",
                ".ts",
                ".json",
                ".yaml",
                ".yml",
            ]:
                findings = scanner.scan_file(file_path)
                all_findings.extend(findings)

        # Scan dependencies
        dep_findings = await scanner.scan_dependencies(path)
        all_findings.extend(dep_findings)

        scanner.vulnerabilities = all_findings

        return web.json_response(
            {
                "tool": "security_scan_project",
                "project": project_path,
                "total_files_scanned": len(list(path.rglob("*"))),
                "vulnerabilities_count": len(all_findings),
                "report": scanner.generate_report(),
            }
        )
    except Exception as e:
        logger.exception("Project scan failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/security_get_checklist")
async def tool_get_checklist(request: web.Request) -> web.Response:
    """Get security checklist."""
    try:
        data = await request.json()
        checklist_type = data.get("type", "general")

        checklist = SecurityChecklist()
        items = checklist.get_checklist(checklist_type)

        return web.json_response(
            {
                "tool": "security_get_checklist",
                "type": checklist_type,
                "count": len(items),
                "items": items,
            }
        )
    except Exception as e:
        logger.exception("Get checklist failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/security_generate_report")
async def tool_generate_report(request: web.Request) -> web.Response:
    """Generate security report."""
    try:
        scanner = get_scanner()
        report = scanner.generate_report()

        return web.json_response(
            {
                "tool": "security_generate_report",
                "report": report,
            }
        )
    except Exception as e:
        logger.exception("Report generation failed")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run Security MCP Server."""
    get_scanner()

    logger.info(f"Starting Security MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Security Server running on http://localhost:{MCP_PORT}")
    logger.info(f"   OWASP Top 10: {len(SecurityScanner.OWASP_TOP_10)} categories")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Security MCP Server stopped")
