"""Thin runner: apply SkillOpt offline evolution to a Cohezion PRIME skill.

Entry point for the skillopt_sleep integration. Finds the skill file,
dumps SurrealDB traces as a corpus, runs SkillOpt, and writes
best_skill.md only if the validation gate passes.

CLI usage:
    uv run python -m cohezion.skillopt.runner --skill cohezion-debugging-scenarios
    uv run python -m cohezion.skillopt.runner --list   # show skills with enough traces
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)

SKILLS_ROOT = Path(__file__).parent.parent.parent.parent / "cohezion" / "skills"


def _find_skill_file(skill_name: str) -> Path | None:
    """Locate a PRIME skill markdown file by name."""
    for candidate in SKILLS_ROOT.rglob("*.md"):
        if candidate.stem.lower() == skill_name.lower().replace("-", "_"):
            return candidate
        if candidate.stem.lower() == skill_name.lower():
            return candidate
    return None


def run_skillopt(skill_name: str, dry_run: bool = False) -> bool:
    """Run SkillOpt offline evolution on one PRIME skill.

    Returns True if a valid improvement was found and applied.
    """
    try:
        from skillopt import SkillOptSleep  # type: ignore[import]
    except ImportError:
        logger.error("skillopt not installed — run: uv pip install skillopt")
        return False

    from cohezion.skillopt.lemonade_backend import LemonadeBackend
    from cohezion.skillopt.surreal_trajectory_loader import dump_corpus

    backend = LemonadeBackend()
    if not backend.is_available():
        logger.error("Lemonade router not reachable at :13305 — start it first")
        return False

    skill_path = _find_skill_file(skill_name)
    if skill_path is None:
        logger.error("Skill file not found for '%s' in %s", skill_name, SKILLS_ROOT)
        return False

    with tempfile.TemporaryDirectory(prefix="skillopt_") as tmp:
        corpus_path = dump_corpus(skill_name, Path(tmp) / "corpus")
        if corpus_path.stat().st_size == 0:
            logger.warning("No traces found for '%s' — cannot train", skill_name)
            return False

        optimizer = SkillOptSleep(model=backend)
        result_path = Path(tmp) / "best_skill.md"

        logger.info("Running SkillOpt on '%s' (%s) ...", skill_name, skill_path)
        optimizer.run(
            skill_path=str(skill_path),
            corpus_path=str(corpus_path),
            output_path=str(result_path),
        )

        if not result_path.exists():
            logger.warning("SkillOpt produced no output for '%s'", skill_name)
            return False

        if dry_run:
            print(result_path.read_text())
            return True

        # Backup original and replace
        backup = skill_path.with_suffix(".md.bak")
        shutil.copy2(skill_path, backup)
        shutil.copy2(result_path, skill_path)
        logger.info("Applied improvement to %s (backup: %s)", skill_path, backup)
        return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run SkillOpt on a Cohezion PRIME skill")
    parser.add_argument("--skill", help="Skill name (e.g. cohezion-debugging-scenarios)")
    parser.add_argument("--list", action="store_true", help="List skills with enough traces")
    parser.add_argument("--dry-run", action="store_true", help="Print result, don't write")
    args = parser.parse_args()

    if args.list:
        from cohezion.skillopt.surreal_trajectory_loader import list_skills_with_traces

        skills = list_skills_with_traces()
        if skills:
            print("\n".join(skills))
        else:
            print("No skills with ≥10 execution traces yet.")
        return

    if not args.skill:
        parser.error("--skill required (or use --list)")

    success = run_skillopt(args.skill, dry_run=args.dry_run)
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
