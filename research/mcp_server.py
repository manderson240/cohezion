"""FastMCP server exposing the research pipeline as MCP tools."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Stub for environments without mcp package
    class FastMCP:  # type: ignore[no-redef]
        def __init__(self, name: str): self.name = name
        def tool(self, *a, **kw): return lambda f: f
        def run(self): raise ImportError("mcp package not installed")

logger = logging.getLogger(__name__)

# Security note: this MCP server has no authentication. It is intended for
# local use only (loopback / Unix socket). Do not expose it on a public
# interface or network without adding authentication middleware first.
mcp = FastMCP("research-pipeline")

DEFAULT_CONFIG = "research/sources.yaml"
DEFAULT_VAULT = "."


@mcp.tool()
async def research_run(
    mode: str = "full",
    focus_area: str | None = None,
) -> dict[str, Any]:
    """Run the research pipeline. mode='full' or 'quick'. focus_area filters to one area."""
    from research.harvester import load_config, harvest
    from research.scorer import score, detect_skill_candidates
    from research.publisher import publish

    config = load_config(DEFAULT_CONFIG)
    vault_path = Path(DEFAULT_VAULT)

    if focus_area:
        area_key = focus_area.replace("-", "_")
        if area_key in config.get("focus_areas", {}):
            config["focus_areas"] = {area_key: config["focus_areas"][area_key]}

    if mode == "quick":
        config["sources"] = {}
        config.setdefault("scoring", {})["ollama_url"] = "http://localhost:0"

    config.setdefault("publishing", {})["vault_path"] = str(vault_path)

    findings = await harvest(config)
    scored_findings, metadata = await score(findings, config)
    skill_results = detect_skill_candidates(scored_findings)
    result = publish(scored_findings, skill_results, metadata, config)

    # Save run metadata
    run_meta = {
        "last_run": datetime.now().isoformat(),
        "findings": len(scored_findings),
        "inbox_notes": result.get("inbox_notes_created", 0),
        "skill_candidates": sum(1 for r in skill_results if r["skill_candidate"]),
    }
    meta_dir = vault_path / "research"
    meta_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_dir / "last_run.json", "w") as f:
        json.dump(run_meta, f, indent=2)

    return result


@mcp.tool()
async def research_triage() -> list[dict[str, Any]]:
    """Review inbox research notes and suggest vault placement."""
    vault_path = Path(DEFAULT_VAULT)
    inbox_dir = vault_path / "inbox"
    results = []

    for note_path in sorted(inbox_dir.glob("research-*.md")):
        content = note_path.read_text()
        vault_target = "unknown"
        relevance = 0.0
        for line in content.split("\n"):
            if line.startswith("vault_target:"):
                vault_target = line.split(":", 1)[1].strip()
            if line.startswith("relevance_score:"):
                try:
                    relevance = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
        results.append({"file": note_path.name, "vault_target": vault_target, "score": relevance})

    return results


@mcp.tool()
async def research_status() -> dict[str, Any]:
    """Show last run metadata."""
    vault_path = Path(DEFAULT_VAULT)
    status_file = vault_path / "research" / "last_run.json"
    if status_file.exists():
        with open(status_file) as f:
            return json.load(f)
    return {"last_run": None, "message": "No runs yet"}


if __name__ == "__main__":
    mcp.run()
