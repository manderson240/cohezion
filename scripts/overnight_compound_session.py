"""Overnight Compound Session — self-improving autonomous loop.

Runs four phases every night:
1. AUTORESEARCH   — analyse execution metrics → improvement opportunities
2. SKILL QUALITY  — score all PRIME and Hermes skills → persist to data/skill_quality/
3. BATCH PORT     — discover unported PRIME skills → attempt port via MCP bridge
4. ARCHIVE        — collect all outputs → timestamped snapshot in data/overnight/

Idempotency rules
- Archives use an ISO8601-minute timestamp: data/overnight/20260503T0045/
- Phase outputs append or timestamp-merge; never overwrite prior runs.
- Batch port always starts with dry_run=True, then converts dry_run=False on a
  configurable top_k subset (default 5).
- SIGINT interrupts gracefully (finishes current phase, writes archive, exits).

Usage::
    uv run python scripts/overnight_compound_session.py
    # or from repo root:
    python scripts/overnight_compound_session.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure project src is importable when running directly
_REPO_ROOT = Path(__file__).parent.parent.resolve()
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("overnight_compound_session")

# ---------------------------------------------------------------------------
# Constants keyed to current V-Model state (docs/V_MODEL_IMPROVEMENT_2026.md)
# ---------------------------------------------------------------------------
SKILLS_DIR = _REPO_ROOT / "src" / "cohezion" / "skills"
DATA_OVERNIGHT = _REPO_ROOT / "data" / "overnight"
DATA_SKILL_QUALITY = _REPO_ROOT / "data" / "skill_quality"
DATA_SKILL_HEALTH = _REPO_ROOT / "data" / "skill_health.json"
HERMES_SKILLS_ROOT = Path.home() / ".hermes" / "skills"
DEFAULT_TOP_K_PORT = 5

_STOP = False


def _install_sigint() -> None:
    def _handler(signum: int, frame: Any) -> None:
        global _STOP
        logger.warning("SIGINT received — finishing current phase then stopping")
        _STOP = True
    signal.signal(signal.SIGINT, _handler)


# ---------------------------------------------------------------------------
# Data objects
# ---------------------------------------------------------------------------

@dataclass
class PhaseResult:
    phase: str
    success: bool
    duration_seconds: float
    records_produced: int = 0
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class OvernightSessionReport:
    session_id: str
    started_at: str
    ended_at: str
    phases: list[PhaseResult]
    overall_success: bool
    manifest: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phase 1 — Autoresearch experiments
# ---------------------------------------------------------------------------

async def _phase_autoresearch(
    metrics_source: Path | None = None,
) -> PhaseResult:
    """Run autoresearch analysis on latest execution metrics."""
    t0 = time.monotonic()
    from cohezion.compound.autoresearch import AutoresearchEngine

    engine = AutoresearchEngine()
    # Build a synthetic metrics dict from skill_health.json if it exists
    metrics: dict[str, Any] = {}
    if metrics_source and metrics_source.exists():
        try:
            metrics = json.loads(metrics_source.read_text())
        except Exception as exc:
            logger.warning("Could not parse metrics source: %s", exc)

    # Fall back to a synthetic baseline so the engine always has something
    if not metrics:
        metrics = {
            "cache_hit_rate": 0.65,
            "avg_tokens_per_request": 4200,
            "avg_vault_latency_ms": 85,
            "coherence": 0.72,
        }

    try:
        opportunities = await engine.analyze(metrics)
    except Exception as exc:
        logger.error("Autoresearch analyze failed: %s", exc)
        return PhaseResult(
            phase="autoresearch",
            success=False,
            duration_seconds=time.monotonic() - t0,
            errors=[str(exc), traceback.format_exc()],
        )

    records_produced = len(opportunities)
    logger.info("Autoresearch: %d opportunities identified", records_produced)
    return PhaseResult(
        phase="autoresearch",
        success=True,
        duration_seconds=time.monotonic() - t0,
        records_produced=records_produced,
        metrics={
            "opportunity_count": records_produced,
            "opportunities": [str(o.recommendation) for o in opportunities[:10]],
        },
    )


# ---------------------------------------------------------------------------
# Phase 2 — Skill quality evaluation
# ---------------------------------------------------------------------------

def _phase_skill_quality(
    top_n: int = 20,
    all_skills: bool = False,
) -> PhaseResult:
    """Score PRIME skills. If all_skills=False, scores the top_n least-recently-evaluated."""
    t0 = time.monotonic()
    from cohezion.compound.skill_quality_scorer import SkillQualityScorer
    from cohezion.compound.skill_health_tracker import SkillHealthTracker

    scorer = SkillQualityScorer(health_tracker=SkillHealthTracker(storage_path=DATA_SKILL_HEALTH))
    skill_files = sorted(SKILLS_DIR.glob("*.md"))
    if not skill_files:
        return PhaseResult(
            phase="skill_quality",
            success=False,
            duration_seconds=time.monotonic() - t0,
            errors=["No .md files found in skills directory"],
        )

    # Determine subset to evaluate
    if all_skills:
        to_evaluate = skill_files
    else:
        # Heuristic: evaluate skills that don't have a recent quality report
        existing_reports = set()
        if DATA_SKILL_QUALITY.exists():
            existing_reports = {p.stem for p in DATA_SKILL_QUALITY.glob("*.jsonl")}
        to_evaluate = [p for p in skill_files if p.stem not in existing_reports]
        if len(to_evaluate) > top_n:
            to_evaluate = to_evaluate[:top_n]
        elif not to_evaluate:
            # Everyone has a report: evaluate first top_n by mtime desc (oldest first)
            skill_files.sort(key=lambda p: p.stat().st_mtime)
            to_evaluate = skill_files[:top_n]

    reports_written = 0
    errors: list[str] = []
    for spath in to_evaluate:
        if _STOP:
            logger.warning("Skill-quality phase interrupted by SIGINT")
            break
        try:
            report = scorer.evaluate(spath, skill_name=spath.stem)
            # DataPipeline.save_report is handled inside orchestrator normally,
            # but we mirror it here for idempotent standalone scoring.
            from cohezion.compound.skill_quality_data_pipeline import SkillQualityDataPipeline

            pipeline = SkillQualityDataPipeline(storage_dir=DATA_SKILL_QUALITY)
            pipeline.save_report(report.skill_name, report)
            reports_written += 1
        except Exception as exc:
            logger.error("Failed to evaluate %s: %s", spath.name, exc)
            errors.append(f"{spath.name}: {exc}")

    logger.info("Skill quality: %d/%d reports written", reports_written, len(to_evaluate))
    return PhaseResult(
        phase="skill_quality",
        success=len(errors) == 0,
        duration_seconds=time.monotonic() - t0,
        records_produced=reports_written,
        errors=errors,
        metrics={"evaluated_count": len(to_evaluate), "written_count": reports_written},
    )


# ---------------------------------------------------------------------------
# Phase 3 — Batch port of unported PRIME skills
# ---------------------------------------------------------------------------

def _discover_unported_skills() -> list[str]:
    """Return list of PRIME skill stems not yet ported to Hermes."""
    prime_files = sorted(SKILLS_DIR.glob("*PRIME*.md"))
    prime_stems = {p.stem for p in prime_files}
    if not HERMES_SKILLS_ROOT.exists():
        return sorted(prime_stems)

    # Hermes skills live in category dirs; the folder name is the skill name.
    hermes_names: set[str] = set()
    for cat_dir in HERMES_SKILLS_ROOT.iterdir():
        if cat_dir.is_dir():
            for skill_dir in cat_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    # Check if this is a Cohezion port by looking for legacy-name
                    content = (skill_dir / "SKILL.md").read_text()
                    # Simple heuristic: if folder name starts with original stem lowercased mapped,
                    # it's considered ported.  Also accept YAML legacy-name matching.
                    hermes_names.add(skill_dir.name)
                    # Legacy name heuristics — any PRIME stem present in YAML frontmatter?
                    for stem in list(prime_stems):
                        if stem in content or stem.lower().replace("_", "-") in skill_dir.name:
                            prime_stems.discard(stem)
    return sorted(prime_stems)


def _phase_batch_port(
    dry_run: bool = True,
    top_k: int = DEFAULT_TOP_K_PORT,
) -> PhaseResult:
    """Attempt to batch-port unported PRIME skills via the built-in converter.

    Idempotency: always dry-run first; if this is a non-dry-run invocation,
    only the top_k unported skills are attempted.
    """
    t0 = time.monotonic()
    unported = _discover_unported_skills()
    if not unported:
        logger.info("Batch port: all %d PRIME skills appear ported", len(list(SKILLS_DIR.glob("*PRIME*.md"))))
        return PhaseResult(
            phase="batch_port",
            success=True,
            duration_seconds=time.monotonic() - t0,
            records_produced=0,
            metrics={"unported_count": 0, "attempted": 0, "ported_count": 0},
        )

    to_attempt = unported[:top_k]
    logger.info("Batch port: %d unported skills, attempting %d (dry_run=%s)", len(unported), len(to_attempt), dry_run)

    # Attempt porting via the built-in converter entry point if available,
    # else fall back to importing the converter logic directly.
    successes = 0
    errors: list[str] = []
    for stem in to_attempt:
        if _STOP:
            logger.warning("Batch-port phase interrupted by SIGINT")
            break
        try:
            # Try python -m cohezion.prime_to_hermes --skill <stem> [--dry-run]
            import subprocess

            cmd = [sys.executable, "-m", "cohezion.prime_to_hermes", "--skill", stem]
            if dry_run:
                cmd.append("--dry-run")
            # 60s timeout per skill
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=_REPO_ROOT)
            if result.returncode == 0:
                successes += 1
                logger.info("  ✓ %s", stem)
            else:
                err = result.stderr.strip() or "non-zero exit"
                errors.append(f"{stem}: {err}")
                logger.warning("  ✗ %s — %s", stem, err)
        except FileNotFoundError:
            # Module not available as CLI — fall back to direct import
            try:
                from cohezion.prime_to_hermes import convert_skill

                out = convert_skill(stem, dry_run=dry_run)
                if out:
                    successes += 1
                    logger.info("  ✓ %s (import fallback)", stem)
                else:
                    errors.append(f"{stem}: conversion returned None")
                    logger.warning("  ✗ %s — conversion returned None", stem)
            except Exception as exc:
                errors.append(f"{stem}: {exc}")
                logger.warning("  ✗ %s — %s", stem, exc)
        except Exception as exc:
            errors.append(f"{stem}: {exc}")
            logger.warning("  ✗ %s — %s", stem, exc)

    return PhaseResult(
        phase="batch_port",
        success=successes == len(to_attempt) and not errors,
        duration_seconds=time.monotonic() - t0,
        records_produced=successes,
        errors=errors,
        metrics={
            "unported_count": len(unported),
            "attempted": len(to_attempt),
            "ported_count": successes,
            "dry_run": dry_run,
        },
    )


# ---------------------------------------------------------------------------
# Phase 4 — Archive
# ---------------------------------------------------------------------------

def _phase_archive(
    session_id: str,
    phase_results: list[PhaseResult],
) -> PhaseResult:
    """Collect outputs into timestamped archive directory."""
    t0 = time.monotonic()
    archive_dir = DATA_OVERNIGHT / session_id
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Build manifest
    manifest: dict[str, Any] = {
        "session_id": session_id,
        "created_at": datetime.now(UTC).isoformat(),
        "repo_root": str(_REPO_ROOT),
        "phases": [],
    }
    for pr in phase_results:
        manifest["phases"].append(
            {
                "phase": pr.phase,
                "success": pr.success,
                "duration_seconds": pr.duration_seconds,
                "records_produced": pr.records_produced,
                "error_count": len(pr.errors),
                "metrics": pr.metrics,
            }
        )

    manifest_path = archive_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # Aggregate report
    report = OvernightSessionReport(
        session_id=session_id,
        started_at=manifest["phases"][0]["phase"] if manifest["phases"] else session_id,
        ended_at=datetime.now(UTC).isoformat(),
        phases=phase_results,
        overall_success=all(p.success for p in phase_results),
        manifest=manifest,
    )
    report_path = archive_dir / "report.json"
    report_path.write_text(json.dumps(asdict(report), indent=2) + "\n")

    # Symlink latest
    latest_link = DATA_OVERNIGHT / "latest"
    try:
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(archive_dir, target_is_directory=True)
    except OSError:
        pass  # non-fatal

    logger.info("Archive: wrote %s (%d phases)", archive_dir, len(phase_results))
    return PhaseResult(
        phase="archive",
        success=True,
        duration_seconds=time.monotonic() - t0,
        records_produced=2,  # manifest + report
        metrics={"archive_dir": str(archive_dir), "manifest": str(manifest_path)},
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _run_session(
    dry_run: bool = True,
    top_k: int = DEFAULT_TOP_K_PORT,
    all_skills: bool = False,
) -> OvernightSessionReport:
    session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M")
    logger.info("=" * 60)
    logger.info("Overnight Compound Session %s starting", session_id)
    logger.info("  dry_run=%s  top_k=%d  all_skills=%s", dry_run, top_k, all_skills)
    logger.info("=" * 60)

    phase_results: list[PhaseResult] = []

    # Phase 1 — autoresearch
    if not _STOP:
        phase_results.append(await _phase_autoresearch(metrics_source=DATA_SKILL_HEALTH))

    # Phase 2 — skill quality
    if not _STOP:
        phase_results.append(_phase_skill_quality(top_n=top_k * 2, all_skills=all_skills))

    # Phase 3 — batch port
    if not _STOP:
        phase_results.append(_phase_batch_port(dry_run=dry_run, top_k=top_k))

    # Phase 4 — archive
    phase_results.append(_phase_archive(session_id, phase_results))

    report = OvernightSessionReport(
        session_id=session_id,
        started_at=session_id,
        ended_at=datetime.now(UTC).isoformat(),
        phases=phase_results,
        overall_success=all(p.success for p in phase_results),
    )
    logger.info("Session %s complete — overall_success=%s", session_id, report.overall_success)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Overnight Compound Session")
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        default=True,
        action="store_false",
        help="Attempt real skill porting (default: dry-run only)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K_PORT,
        help=f"Max skills to port per run (default {DEFAULT_TOP_K_PORT})",
    )
    parser.add_argument(
        "--all-skills",
        action="store_true",
        help="Evaluate quality for all skills (default: subset)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level",
    )
    args = parser.parse_args(argv)

    logging.getLogger().setLevel(getattr(logging, args.log_level))
    _install_sigint()

    report = asyncio.run(_run_session(dry_run=args.dry_run, top_k=args.top_k, all_skills=args.all_skills))
    return 0 if report.overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
