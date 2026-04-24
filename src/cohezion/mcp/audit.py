# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""MCP Server Auditor - Performs deep scans of the MCP server fleet."""

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

from cohezion.mcp.manager.server_manager import MCPServerManager, get_manager


logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    server_name: str
    healthy: bool
    latency_ms: float
    tool_count: int
    security_score: float  # 0.0 to 1.0
    issues: list[str]


class MCPAuditor:
    manager: MCPServerManager

    def __init__(self) -> None:
        self.manager = get_manager()

    async def audit_server(self, name: str, port: int) -> AuditResult:
        start_time = time.perf_counter()
        healthy = False
        tool_count = 0
        issues: list[str] = []
        latency = 0.0
        security_score = 1.0

        try:
            timeout = aiohttp.ClientTimeout(total=2)
            async with aiohttp.ClientSession() as session:
                # 1. Health Ping
                async with session.get(f"http://localhost:{port}/health", timeout=timeout) as resp:
                    healthy = resp.status == 200
                    latency = (time.perf_counter() - start_time) * 1000

                # 2. Tool Discovery
                # Note: This assumes a standard MCP /tools endpoint if implemented
                # For now, we use the registry information for the count
                # If we had a live tool-listing protocol, we'd use it here.

                # 3. Security Check (Mock logic for adversarial review)
                security_score = 1.0
                if "shell" in name or "git" in name:
                    # High risk servers need stricter checks
                    security_score = 0.8
                    issues.append(
                        "High-risk surface area: requires manual audit of tool arguments."
                    )

                if latency > 500:
                    issues.append(f"High latency: {latency:.2f}ms")
                    security_score -= 0.1

        except Exception as e:
            issues.append(f"Connection failed: {e!s}")
            healthy = False

        return AuditResult(
            server_name=name,
            healthy=healthy,
            latency_ms=latency,
            tool_count=tool_count,
            security_score=max(0.0, security_score),
            issues=issues,
        )

    async def run_fleet_audit(self) -> list[AuditResult]:
        _results: list[AuditResult] = []
        # We audit the servers registered in the manager
        manager_status = self.manager.get_status()
        servers = manager_status["servers"]

        tasks = []
        if servers:
            for name, config in servers.items():
                tasks.append(self.audit_server(name, config["port"]))
        else:
            # Fallback: scan port range
            logger.info("No servers in manager, scanning port range 8360-8400...")
            for port in range(8360, 8400):
                # Try common ports plus range
                if port == 8370:  # Manager
                    tasks.append(self.audit_server("mcp-manager", port))
                elif 8361 <= port <= 8375:
                    tasks.append(self.audit_server(f"port-{port}", port))

        return await asyncio.gather(*tasks)


async def run_audit() -> None:
    auditor = MCPAuditor()
    results: list[AuditResult] = await auditor.run_fleet_audit()

    print("\n--- MCP FLEET AUDIT RESULTS ---")
    for r in results:
        status = "PASSED" if r.healthy and r.security_score > 0.7 else "FAILED"
        print(
            f"[{status}] {r.server_name:15} | Latency: {r.latency_ms:6.2f}ms | Score: {r.security_score:.2f}"
        )
        for issue in r.issues:
            print(f"  ! {issue}")


if __name__ == "__main__":
    asyncio.run(run_audit())
