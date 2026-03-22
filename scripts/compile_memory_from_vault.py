#!/usr/bin/env python3
"""
Compile MEMORY.md from Cohezion Vault

Version History:
- v2.0 (2026-02-12): GraphRAG-powered with impact scoring, graph relationships
- v1.0 (2026-02-11): Flat file reading from vault

Generates a ≤200 line MEMORY.md cache from vault knowledge:
- Recent decisions (last 7 days)
- Most-used patterns (top 10)
- Current project state
- Quick reference commands

Usage:
    # V2 (GraphRAG, requires SurrealDB)
    uv run python scripts/compile_memory_from_vault.py --graphrag

    # V1 (Flat files, faster)
    uv run python scripts/compile_memory_from_vault.py

Output:
    ~/.claude/projects/-home-mike-anderson-dev-cohezion/memory/MEMORY.md
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Add cloud-vault-mcp to path for GraphRAG
sys.path.insert(0, str(Path(__file__).parent.parent / "cloud-vault-mcp" / "src"))


# ============================================================================
# V1: Flat File Implementation
# ============================================================================


def load_vault_decisions_v1(vault_path: Path, days: int = 7) -> list[dict]:
    """V1: Load recent decisions from vault files"""
    decisions_dir = vault_path / "decisions"
    cutoff_date = datetime.now() - timedelta(days=days)

    recent = []
    for decision_file in decisions_dir.glob("*.md"):
        try:
            date_str = "-".join(decision_file.stem.split("-")[:3])
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date >= cutoff_date:
                content = decision_file.read_text()
                recent.append(
                    {
                        "date": date_str,
                        "title": decision_file.stem,
                        "path": str(decision_file.relative_to(vault_path)),
                        "content": content[:200],
                    }
                )
        except (ValueError, IndexError):
            continue

    return sorted(recent, key=lambda x: x["date"], reverse=True)


def load_vault_patterns_v1(vault_path: Path, top_n: int = 10) -> list[dict]:
    """V1: Load patterns from vault files"""
    patterns_dir = vault_path / "patterns"

    patterns = []
    for pattern_file in patterns_dir.glob("*.md"):
        content = pattern_file.read_text()
        patterns.append(
            {
                "name": pattern_file.stem,
                "path": str(pattern_file.relative_to(vault_path)),
                "preview": content.split("\n\n")[0][:150],
            }
        )

    return sorted(patterns, key=lambda x: x["name"])[:top_n]


def compile_memory_v1(vault_path: Path, output_path: Path):
    """V1: Compile MEMORY.md from flat vault files"""
    recent_decisions = load_vault_decisions_v1(vault_path, days=7)
    top_patterns = load_vault_patterns_v1(vault_path, top_n=10)

    today = datetime.now().strftime("%Y-%m-%d")

    memory_content = f"""# Cohezion Memory (Auto-Generated {today})

**Source**: Compiled from ~/vaults/cohezion-vault/ (flat files)
**Refresh**: Run `uv run python scripts/compile_memory_from_vault.py` weekly

## Recent Decisions (Last 7 Days)

"""

    if recent_decisions:
        for decision in recent_decisions[:5]:
            memory_content += f"- **{decision['date']}**: {decision['title']}\n"
            memory_content += f"  → See `{decision['path']}`\n\n"
    else:
        memory_content += "No recent decisions. All decisions in vault: `decisions/`\n\n"

    memory_content += """## Most-Used Patterns

"""

    for pattern in top_patterns:
        memory_content += f"- **{pattern['name']}**\n"
        memory_content += f"  → See `{pattern['path']}`\n\n"

    memory_content += """## Quick Reference

**Search Vault**: `vault_find_relevant_context(query)`
**Log Learnings**:
- Decision: `vault_log_decision(project, title, context, decision, rationale)`
- Experiment: `vault_log_experiment(project, hypothesis, method, result, learnings)`
- Pattern: `vault_extract_pattern(source_path, pattern_name, description)`

**Commands**:
- Tests: `uv run pytest tests/ -q`
- Format: `make format && make lint`
- API: `uv run uvicorn cohezion.api:app --reload`

## Core Principles

1. **Compound Engineering**: Every feature makes future features easier
2. **Token Efficiency**: Implement → validate → test (not test-first)
3. **Vault-First**: Log all learnings using structured tools
4. **Honest Metrics**: Report actual numbers, not inflated
5. **Non-Blocking Observability**: Failures never crash execution

---

**For deeper context**: `vault_find_relevant_context("your query")`
**Full vault**: ~/vaults/cohezion-vault/ (150+ decisions, patterns, experiments)
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(memory_content)

    print(f"✅ Compiled MEMORY.md V1 ({len(memory_content.splitlines())} lines)")
    print(f"   {len(recent_decisions)} decisions, {len(top_patterns)} patterns")


# ============================================================================
# V2: GraphRAG Implementation
# ============================================================================


async def load_high_impact_decisions_v2(days: int = 7, top_n: int = 10) -> list[dict]:
    """V2: Load decisions from SurrealDB sorted by graph impact"""
    import httpx
    from mcp_server.graphrag_helpers import execute_surreal_async

    async with httpx.AsyncClient() as client:
        query = f"""
        SELECT id, title, type, created_at,
            count(->informed_by) AS informs,
            count(<-led_to) AS led_to,
            count(<-used_in) AS used_in,
            (count(->informed_by) + count(<-led_to) + count(<-used_in)) AS impact_score
        FROM vault_memory
        WHERE type = 'decision'
            AND created_at > time::now() - {days}d
        ORDER BY impact_score DESC, created_at DESC
        LIMIT {top_n};
        """

        results = await execute_surreal_async(query, client)
        return results[0].get("result", [])


async def load_pattern_usage_v2(top_n: int = 10) -> list[dict]:
    """V2: Load patterns from SurrealDB sorted by usage"""
    import httpx
    from mcp_server.graphrag_helpers import execute_surreal_async

    async with httpx.AsyncClient() as client:
        query = f"""
        SELECT id, title,
            count(<-informed_by) AS referenced_by,
            count(<-used_in) AS used_in,
            (count(<-informed_by) + count(<-used_in)) AS total_usage
        FROM vault_memory
        WHERE type = 'pattern'
        ORDER BY total_usage DESC, title ASC
        LIMIT {top_n};
        """

        results = await execute_surreal_async(query, client)
        return results[0].get("result", [])


async def compile_memory_v2(output_path: Path):
    """V2: Compile MEMORY.md from GraphRAG (SurrealDB)"""
    import httpx
    from mcp_server.graphrag_helpers import execute_surreal_async
    from mcp_server.graphrag_pattern_detector import PatternDetector

    vault_path = Path.home() / "vaults" / "cohezion-vault"

    # Load graph data
    decisions = await load_high_impact_decisions_v2(days=7, top_n=10)
    patterns = await load_pattern_usage_v2(top_n=10)

    # Pattern auto-detection (Phase 5)
    async with PatternDetector(vault_path) as detector:
        pattern_suggestions = await detector.suggest_patterns(min_similarity=0.7, max_suggestions=5)
        pattern_summary = await detector.get_pattern_impact_summary()

    lines = []
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header
    lines.append(f"# Cohezion Memory (GraphRAG {today})")
    lines.append("")
    lines.append("**Source**: SurrealDB GraphRAG (vault + relationships)")
    lines.append("**Refresh**: `uv run python scripts/compile_memory_from_vault.py --graphrag`")
    lines.append("")

    # High-impact decisions
    lines.append("## High-Impact Recent Decisions (Last 7 Days)")
    lines.append("")

    if decisions:
        for dec in decisions:
            title = dec.get("title", "Untitled")[:70]
            impact = dec.get("impact_score", 0)
            informs = dec.get("informs", 0)
            led_to = dec.get("led_to", 0)
            used_in = dec.get("used_in", 0)

            lines.append(f"- **{title}**")
            lines.append(
                f"  - Impact: {impact} (→{informs} informs, ←{led_to} led to, ↗{used_in} used)"
            )
            lines.append("")
    else:
        lines.append("_No recent decisions in graph_")
        lines.append("")

    # Top patterns
    lines.append("## Top Patterns (By Usage)")
    lines.append("")

    if patterns:
        for pattern in patterns:
            title = pattern.get("title", "Untitled")[:60]
            usage = pattern.get("total_usage", 0)
            ref_by = pattern.get("referenced_by", 0)
            used = pattern.get("used_in", 0)

            lines.append(f"- **{title}**")
            lines.append(f"  - Referenced: {ref_by}× | Used: {used}× | Total: {usage}")
            lines.append("")
    else:
        lines.append("_No patterns in graph_")
        lines.append("")

    # Suggested patterns (Phase 5: Auto-Detection)
    lines.append("## Suggested Patterns (Auto-Detected)")
    lines.append("")

    if pattern_suggestions:
        for suggestion in pattern_suggestions:
            title = suggestion.suggested_title
            themes = ", ".join(suggestion.common_themes[:3])
            count = len(suggestion.source_docs)

            lines.append(f"- **{title}**")
            lines.append(f"  - Similar docs: {count} | Themes: {themes}")
            lines.append(f"  - Rationale: {suggestion.rationale}")
            lines.append("")
    else:
        lines.append("_No pattern suggestions (run full vault import first)_")
        lines.append("")

    # Pattern impact summary
    if pattern_summary:
        lines.append("## Pattern Impact Summary")
        lines.append("")
        lines.append(f"- Total patterns: {pattern_summary.get('total_patterns', 0)}")
        lines.append(f"- High-impact (≥5 refs): {pattern_summary.get('high_impact_patterns', 0)}")
        lines.append(f"- Avg usage: {pattern_summary.get('avg_usage', 0.0):.1f} refs/pattern")
        lines.append(f"- Unused patterns: {pattern_summary.get('unused_patterns', 0)}")
        lines.append("")

    # Graph statistics
    async with httpx.AsyncClient() as client:
        stats_query = """
        SELECT count() AS total FROM vault_memory GROUP ALL;
        SELECT count() AS total FROM informed_by GROUP ALL;
        """
        stats_results = await execute_surreal_async(stats_query, client)

        doc_count = stats_results[0].get("result", [{}])[0].get("total", 0)
        edge_count = stats_results[1].get("result", [{}])[0].get("total", 0)

        lines.append("## Graph Statistics")
        lines.append("")
        lines.append(f"- **Documents**: {doc_count}")
        lines.append(f"- **Relationships**: {edge_count}")
        lines.append(f"- **Avg Connections**: {edge_count / doc_count if doc_count > 0 else 0:.2f}")
        lines.append("")

    # Quick reference
    lines.append("## Quick Reference")
    lines.append("")
    lines.append("**GraphRAG Search**: Semantic vector + graph ancestry")
    lines.append("**Auto-Sync**: File changes automatically indexed")
    lines.append("**Vault Tools**: `vault_log_decision()`, `vault_find_relevant_context()`")
    lines.append("")

    lines.append("## Core Principles")
    lines.append("")
    lines.append("1. **Compound Engineering**: Knowledge compounds exponentially via graph")
    lines.append("2. **Token Efficiency**: 10× context for 0 additional tokens")
    lines.append("3. **Impact Scoring**: Prioritize high-impact learnings")
    lines.append("4. **Graph Awareness**: Decisions inform patterns inform experiments")
    lines.append("")

    # Truncate to ≤200 lines
    memory_content = "\n".join(lines)
    memory_lines = memory_content.split("\n")
    if len(memory_lines) > 200:
        memory_content = "\n".join(memory_lines[:200]) + "\n\n_(Truncated to 200 lines)_"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(memory_content)

    print(f"✅ Compiled MEMORY.md V2 ({len(memory_lines)} lines)")
    print(f"   {doc_count} documents, {edge_count} relationships")


# ============================================================================
# Main Entry Point
# ============================================================================


async def main_async(use_graphrag: bool):
    """Async main for V2"""
    output_path = (
        Path.home()
        / ".claude"
        / "projects"
        / "-home-mike-anderson-dev-cohezion"
        / "memory"
        / "MEMORY.md"
    )

    if use_graphrag:
        print("🔍 Compiling MEMORY.md V2 (GraphRAG from SurrealDB)...")
        await compile_memory_v2(output_path)
    else:
        vault_path = Path.home() / "vaults" / "cohezion-vault"
        if not vault_path.exists():
            print(f"❌ Vault not found: {vault_path}")
            sys.exit(1)

        print("📁 Compiling MEMORY.md V1 (flat files)...")
        compile_memory_v1(vault_path, output_path)

    print(f"📍 Output: {output_path}")
    print("✅ Compilation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile MEMORY.md from vault")
    parser.add_argument("--graphrag", action="store_true", help="Use V2 GraphRAG (requires SurrealDB)")
    args = parser.parse_args()

    asyncio.run(main_async(args.graphrag))
