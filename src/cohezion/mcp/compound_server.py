"""MCP Compound Server - Unified interface for compound engineering.

Elegant refactor: 782 lines compounded into ~380.
- DRY error handling via @mcp_tool decorator
- Shared MCP client resolution via McpClientResolver
- Response factories (ok/err) eliminate repeated dict literals
- Tool domain grouped logically by function
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.compound_utils import McpClientResolver, err, mcp_tool, ok

logger = logging.getLogger(__name__)

# ────────────────────────── FastMCP instance ─────────────────────────────
mcp = FastMCP(
    "Compound Engineering",
    instructions=(
        "A compound engineering MCP server for multi-session AI workflows. "
        "Manage sessions with warm-start/clean-shutdown, optimize token efficiency, "
        "run adversarial reviews, and capture learnings to vault."
    ),
)


# ────────────────────────── Lazy component globals ─────────────────────────
def _get_mcp() -> Any:
    from cohezion.core.mcp_client import get_mcp_client

    return get_mcp_client()


_mcp_resolver = McpClientResolver(get_default_client=_get_mcp)
_session_manager: Any = None


def _get_manager() -> Any:
    from cohezion.compound.session_manager import CompoundSessionManager

    global _session_manager
    if _session_manager is None:
        _session_manager = CompoundSessionManager()
    return _session_manager


# ══════════════════════════ SESSION LIFECYCLE ══════════════════════════════


@mcp_tool(mcp)
async def compound_start_session(
    max_cache_entries: int = 256, enable_persistence: bool = True
) -> dict[str, Any]:
    """Start a compound session with warm-start from vault."""
    mgr = _get_manager()
    await mgr.__aenter__()
    summary = mgr.start_session(max_cache_entries=max_cache_entries)
    return ok(
        session_id=summary.get("session_id"),
        cache_entries_loaded=summary.get("cache_entries_loaded", 0),
        persistence_enabled=enable_persistence,
    )


@mcp_tool(mcp)
async def compound_check_alignment(request: str, threshold: float = 0.5) -> dict[str, Any]:
    """Check request alignment before execution."""
    if _session_manager is None:
        return err("No active session. Call compound_start_session first.")
    result = _session_manager.check_alignment(request, threshold)
    return ok(
        coherence=result.coherence,
        should_proceed=result.should_proceed,
        issues=result.issues if hasattr(result, "issues") else [],
    )


@mcp_tool(mcp)
async def compound_end_session(save_cache: bool = True) -> dict[str, Any]:
    """End compound session with clean-shutdown to vault."""
    global _session_manager
    if _session_manager is None:
        return err("No active session to end.")
    summary = _session_manager.end_session()
    if save_cache:
        mcp_client = _get_mcp()
        await mcp_client.vault_write(
            f"logs/compound/session_{summary.get('session_id')}_end.json",
            json.dumps(summary, indent=2),
        )
    await _session_manager.__aexit__(None, None, None)
    _session_manager = None
    return ok(session_summary=summary)


# ══════════════════════════ CACHE TOOLS ════════════════════════════════════


@mcp_tool(mcp)
async def cache_get_metrics() -> dict[str, Any]:
    """Get token cache efficiency metrics."""
    from cohezion.swarm.token_cache_optimizer import get_token_cache_optimizer

    return ok(metrics=get_token_cache_optimizer().get_metrics())


@mcp_tool(mcp)
async def cache_optimize() -> dict[str, Any]:
    """Run cache optimization pass."""
    from cohezion.swarm.token_cache_optimizer import get_token_cache_optimizer

    recommendations = await get_token_cache_optimizer().optimize()
    return ok(recommendations=recommendations)


# ══════════════════════════ ADVERSARIAL REVIEW ═════════════════════════════


@mcp_tool(mcp)
async def ralph_lopps_review(code: str, context: str = "") -> dict[str, Any]:
    """Run Ralph Lopps Red Team adversarial review."""
    from cohezion.compound.adversarial import RalphLoppsReviewer

    findings = RalphLoppsReviewer().review(code, {"context": context} if context else {})
    return ok(
        findings=[
            {
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "recommendation": f.recommendation,
                "line_number": f.line_number,
            }
            for f in findings
        ],
        total_findings=len(findings),
        critical_count=sum(1 for f in findings if f.severity == "critical"),
    )


@mcp_tool(mcp)
async def multiperspective_review(proposal: str) -> dict[str, Any]:
    """Run Blue/Green/Yellow Hat multiperspective review."""
    from cohezion.compound.adversarial import MultiperspectiveReviewBoard

    review = MultiperspectiveReviewBoard().full_review(json.loads(proposal))
    return ok(
        review={
            "blue_process_optimizations": review["blue"],
            "green_alternatives": review["green"],
            "yellow_risks": review["yellow"],
            "ralph_findings": [
                {"severity": f.severity, "description": f.description} for f in review["ralph"]
            ],
        }
    )


# ══════════════════════════ AUTORESEARCH ═══════════════════════════════════


@mcp_tool(mcp)
async def autoresearch_analyze(metrics_json: str) -> dict[str, Any]:
    """Analyze metrics and identify improvement opportunities."""
    from cohezion.compound.autoresearch import AutoresearchEngine

    opportunities = await AutoresearchEngine().analyze(json.loads(metrics_json))
    return ok(
        opportunities=[
            {
                "category": o.category,
                "priority": o.priority,
                "current_value": o.current_value,
                "target_value": o.target_value,
                "potential_impact": o.potential_impact,
                "recommendation": o.recommendation,
            }
            for o in opportunities
        ],
        total_opportunities=len(opportunities),
    )


# ══════════════════════════ LEARNING LOOP ══════════════════════════════════


@mcp_tool(mcp)
async def learning_capture(
    execution_result_json: str, server_url: str | None = None
) -> dict[str, Any]:
    """Capture execution learning to vault."""
    from cohezion.compound.autoresearch import RetrospectionEngine

    client, _ = await _mcp_resolver.resolve(server_url)
    path = await RetrospectionEngine().capture_learning(json.loads(execution_result_json), client)
    return ok(vault_path=path, captured=path is not None)


@mcp_tool(mcp)
async def learning_process_execution(
    execution_result_json: str, server_url: str | None = None
) -> dict[str, Any]:
    """Process execution through full learning loop."""
    from cohezion.compound.autoresearch import ExperientialLearningLoop

    client, _ = await _mcp_resolver.resolve(server_url)
    results = await ExperientialLearningLoop().process_execution(
        json.loads(execution_result_json), client
    )
    return ok(results=results)


# ══════════════════════════ SKILL REFINEMENT ═════════════════════════════════


@mcp_tool(mcp)
async def skill_refinement_apply(skill_name: str, refinement_type: str) -> dict[str, Any]:
    """Apply refinement to a skill."""
    import re

    from cohezion.compound.autoresearch import SkillRefiner

    if not re.match(r"^[\w\-]+$", skill_name):
        return err(
            "Invalid skill_name. Use only alphanumeric characters, hyphens, and underscores."
        )
    valid = {"token_optimization", "coherence_improvement", "cache_optimization"}
    if refinement_type not in valid:
        return err(f"Invalid refinement_type. Must be one of: {', '.join(sorted(valid))}")
    success = await SkillRefiner().apply_refinement(
        f"src/cohezion/skills/{skill_name}.md",
        {
            "type": refinement_type,
            "finding": f"Auto-generated refinement for {refinement_type}",
            "recommendation": "See skill file for updates",
        },
    )
    return ok(skill=skill_name, refinement_applied=success)


# ══════════════════════════ CONTEXT POLICY ═══════════════════════════════════


@mcp_tool(mcp)
async def get_context_policy() -> dict[str, Any]:
    """Get current learned context policy budgets."""
    from cohezion.compound.context_policy import ContextPolicy, TaskProfile

    policy = ContextPolicy()
    budgets: dict[str, Any] = {}
    for name in ("focused", "exploratory", "routine"):
        b = policy.get_budget(TaskProfile(name))
        budgets[name] = {
            "flux_top_k": b.flux_top_k,
            "flux_min_relevance": b.flux_min_relevance,
            "token_budget": b.token_budget,
            "skill_overlay": b.skill_overlay,
        }
    return ok(
        profiles=budgets,
        task_overrides=policy._task_overrides,
        outcome_summary=policy._outcome_summary,
    )


@mcp_tool(mcp)
async def update_context_policy(
    profile: str,
    flux_top_k: int | None = None,
    flux_min_relevance: float | None = None,
    token_budget: int | None = None,
) -> dict[str, Any]:
    """Update a context policy profile's budget parameters."""
    from cohezion.compound.context_policy import ContextBudget, ContextPolicy, TaskProfile

    try:
        task = TaskProfile(profile)
    except ValueError:
        return err(f"Invalid profile: {profile}. Use focused/exploratory/routine.")

    policy = ContextPolicy()
    current = policy.get_budget(task)
    updated = ContextBudget(
        flux_top_k=flux_top_k if flux_top_k is not None else current.flux_top_k,
        flux_min_relevance=flux_min_relevance
        if flux_min_relevance is not None
        else current.flux_min_relevance,
        flux_sources=current.flux_sources,
        token_budget=token_budget if token_budget is not None else current.token_budget,
        skill_overlay=current.skill_overlay,
    )
    policy._budgets[task] = updated
    policy.save_learned_budgets()
    return ok(
        profile=profile,
        budget={
            "flux_top_k": updated.flux_top_k,
            "flux_min_relevance": updated.flux_min_relevance,
            "token_budget": updated.token_budget,
            "skill_overlay": updated.skill_overlay,
        },
    )


# ══════════════════════════ SKILL PORT TOOLS ═══════════════════════════════


@mcp_tool(mcp)
async def cohezion_batch_port_skills(
    skill_names: list[str], dry_run: bool = False
) -> dict[str, Any]:
    """Batch-port multiple PRIME skills to Hermes format."""
    project_root = Path(__file__).resolve().parents[3]
    converter = project_root / "scripts" / "prime_to_hermes_converter.py"
    if not converter.exists():
        return err("Converter script not found", path=str(converter))

    results: list[dict[str, Any]] = []
    for name in skill_names:
        cmd = [sys.executable, str(converter), "--skill", name]
        if dry_run:
            cmd.append("--dry-run")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            results.append(
                {
                    "name": name,
                    "success": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                }
            )
        except asyncio.TimeoutError:
            results.append({"name": name, "success": False, "error": "Timeout after 30s"})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "success": False, "error": str(exc)})
    successes = sum(1 for r in results if r.get("success"))
    return ok(total=len(skill_names), successes=successes, dry_run=dry_run, results=results)


@mcp_tool(mcp)
async def cohezion_inspect_codebase(
    subdirectory: str = "", pattern: str = "*.py", max_depth: int = 4
) -> dict[str, Any]:
    """Inspect a Cohezion codebase subdirectory and return file metrics."""
    project_root = Path(__file__).resolve().parents[3]
    root = (
        project_root / "src" / "cohezion" / subdirectory.strip().strip("/")
        if subdirectory
        else project_root / "src" / "cohezion"
    )
    if not root.exists():
        return err(f"Path not found: {root}")

    tree: list[dict[str, Any]] = []
    root_path = root.resolve()
    for p in root_path.rglob(pattern):
        depth = len(p.relative_to(root_path).parts) - 1
        if depth > max_depth:
            continue
        try:
            with open(p, "rb") as f:
                lines = sum(1 for _ in f)
        except Exception:
            lines = 0
        tree.append({"path": str(p.relative_to(root_path)), "lines": lines, "depth": depth})

    return ok(
        root=str(root.relative_to(project_root)),
        files=len(tree),
        total_lines=sum(n["lines"] for n in tree),
        max_depth_found=max((n["depth"] for n in tree), default=0),
        tree=tree[:200],
    )


@mcp_tool(mcp)
async def cohezion_skill_matrix() -> dict[str, Any]:
    """Return the PRIME skill cross-reference matrix as JSON."""
    import re

    project_root = Path(__file__).resolve().parents[3]
    skills_dir = project_root / "src" / "cohezion" / "skills"
    prime_skills: list[dict[str, Any]] = []
    categories: set[str] = set()

    if skills_dir.exists():
        for fpath in sorted(skills_dir.glob("*.md")):
            stem = fpath.stem
            lower = stem.lower()
            # Category inference
            category = "prime" if stem.isupper() else "general"
            for keyword, cat in (
                (("mcp", "bridge", "server"), "mcp"),
                (("swarm", "orchestration", "team"), "orchestration"),
                (("mlops", "training", "inference"), "mlops"),
                (("engineering", "compound", "design"), "engineering"),
                (("competition", "kaggle", "arc"), "competition"),
            ):
                if any(k in lower for k in keyword):
                    category = cat
                    break
            prime_skills.append(
                {"name": stem, "category": category, "path": str(fpath.relative_to(project_root))}
            )
            categories.add(category)

    # Local Hermes skills
    hermes_skills_dir = Path.home() / ".hermes" / "skills"
    local_skills: list[dict[str, Any]] = []
    if hermes_skills_dir.exists():
        for root in hermes_skills_dir.rglob("SKILL.md"):
            text = root.read_text(encoding="utf-8", errors="ignore")[:4096]
            is_cohezion = any(
                tag in text
                for tag in ["project: cohezion", "cohezion", "legacy-name:", "converted: true"]
            )
            if not is_cohezion:
                continue
            rel = root.relative_to(hermes_skills_dir)
            skill_name = rel.parts[-2] if len(rel.parts) >= 2 else root.parent.name
            category = rel.parts[0] if rel.parts else "unknown"
            legacy_match = re.search(r"legacy-name:\s*([A-Z_0-9]+_PRIME)", text)
            local_skills.append(
                {
                    "name": skill_name,
                    "category": category,
                    "full_path": str(root),
                    "legacy_name": legacy_match.group(1) if legacy_match else None,
                }
            )

    prime_names = {s["name"] for s in prime_skills}
    local_legacies = {s["legacy_name"] for s in local_skills if s.get("legacy_name")}
    matrix = {
        "prime_total": len(prime_names),
        "hermes_local_total": len(local_skills),
        "ported": sorted(prime_names & local_legacies),
        "not_ported": sorted(prime_names - local_legacies),
        "hermes_only": sorted({s["name"] for s in local_skills}),
    }
    return ok(
        prime_skills=prime_skills,
        categories=sorted(categories),
        local_hermes_skills=local_skills,
        matrix=matrix,
    )


# ══════════════════════════ HEALTH & LIFECYCLE ═════════════════════════════


async def check_redis_health() -> dict[str, Any]:
    """Check Redis connection health on startup."""
    import redis.asyncio as redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        client = redis.from_url(redis_url, socket_connect_timeout=5)
        await client.ping()
        await client.close()
        logger.info("Redis health check passed: %s", redis_url)
        return ok(url=redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis health check failed: %s", exc)
        return err(str(exc), url=redis_url)


def main() -> None:
    """Run the MCP server."""
    health = asyncio.run(check_redis_health())
    if health["status"] != "success":
        logger.warning("Redis unavailable — cache persistence disabled")
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    port = int(os.environ.get("MCP_PORT", "8379"))
    if transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
