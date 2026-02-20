"""Standalone CLI for the research pipeline — usable from any AI coding tool."""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "research/sources.yaml"
DEFAULT_VAULT = "."


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with run, triage, and status subcommands."""
    parser = argparse.ArgumentParser(
        prog="research",
        description="Cohezion daily research pipeline — discover, score, and publish findings.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to sources.yaml config")
    parser.add_argument("--vault", default=DEFAULT_VAULT, help="Path to vault root")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run the full research pipeline")
    run_parser.add_argument("--quick", action="store_true", help="Quick mode: web search only, keyword scoring")
    run_parser.add_argument("--focus", type=str, help="Filter to one focus area (e.g., compound-engineering)")
    run_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")

    # triage subcommand
    subparsers.add_parser("triage", help="Review inbox research notes and suggest vault placement")

    # status subcommand
    subparsers.add_parser("status", help="Show last run stats")

    return parser


def cmd_status(vault_path: Path) -> None:
    """Show last run stats as JSON."""
    status_file = vault_path / "research" / "last_run.json"
    if status_file.exists():
        with open(status_file) as f:
            data = json.load(f)
    else:
        data = {"last_run": None, "message": "No runs yet"}

    print(json.dumps(data, indent=2, default=str))


def cmd_triage(vault_path: Path) -> None:
    """Review inbox research notes and suggest vault placement."""
    inbox_dir = vault_path / "inbox"
    research_notes = sorted(inbox_dir.glob("research-*.md"))

    results = []
    for note_path in research_notes:
        content = note_path.read_text()
        # Extract frontmatter fields
        vault_target = "unknown"
        score = 0.0
        for line in content.split("\n"):
            if line.startswith("vault_target:"):
                vault_target = line.split(":", 1)[1].strip()
            if line.startswith("relevance_score:"):
                try:
                    score = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        results.append({
            "file": note_path.name,
            "vault_target": vault_target,
            "score": score,
        })

    print(json.dumps(results, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full research pipeline."""
    from research.harvester import load_config, harvest
    from research.scorer import score, detect_skill_candidates
    from research.publisher import publish

    config = load_config(args.config)
    vault_path = Path(args.vault)

    # Apply focus filter
    if args.focus:
        area_key = args.focus.replace("-", "_")
        if area_key in config.get("focus_areas", {}):
            config["focus_areas"] = {area_key: config["focus_areas"][area_key]}
        else:
            print(json.dumps({"error": f"Unknown focus area: {args.focus}"}))
            sys.exit(1)

    # Quick mode: skip Ollama, reduce sources
    if args.quick:
        config["sources"] = {}
        config.setdefault("scoring", {})["ollama_url"] = "http://localhost:0"  # Force fallback

    # Set vault path in publishing config
    config.setdefault("publishing", {})["vault_path"] = str(vault_path)

    # Run pipeline
    async def _run():
        if args.dry_run:
            # Dry run: report config without executing
            total_queries = sum(len(a.get("queries", [])) for a in config.get("focus_areas", {}).values())
            result = {
                "dry_run": True,
                "focus_areas": len(config.get("focus_areas", {})),
                "total_queries": total_queries,
                "sources_configured": list(config.get("sources", {}).keys()),
                "max_inbox_notes": config.get("publishing", {}).get("max_inbox_notes", 40),
            }
            return result

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

    result = asyncio.run(_run())
    print(json.dumps(result, indent=2, default=str))


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()

    vault_path = Path(args.vault)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(vault_path)
    elif args.command == "triage":
        cmd_triage(vault_path)


if __name__ == "__main__":
    main()
