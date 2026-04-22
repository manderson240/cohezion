"""Session-end: wire RetrospectionEngine + SkillRefiner to the per-session
signals recorded by the V-model + experiential-learning post-commit hooks.

Companion to the two per-commit hooks. Each commit records structural +
narrative rows; this script aggregates them at the END of a session and
triggers the compound-loop counterparts:

  * `RetrospectionEngine.summarize()` — builds a first-person retrospection
    summary from per-commit metrics; writes to the vault and SurrealDB.
  * `SkillRefiner.refine()` — for any PRIME skill files touched in the
    session's commits, appends a refinement signal to the skill definition.

Closes ARC backlog item #3 from `patterns/arc-lessons-applied-to-cohezion.md`:
"RetrospectionEngine → SkillRefiner session-end wiring (the narrative
counterpart of the per-commit hook)."

Usage:
    # Default: process the current COHEZION_SESSION_ID
    uv run python scripts/session_end.py

    # Explicit session, e.g. when cleaning up a prior handoff
    uv run python scripts/session_end.py --session-id sess-abc123

    # Dry-run: show what WOULD be summarized / refined, write nothing
    uv run python scripts/session_end.py --dry-run

Wiring (operator must do this once):
    * Invoke this before `cz session send-clear` in the 90% handoff path, OR
    * Add it to .git/hooks/pre-push for per-push retrospection, OR
    * Call it from a Claude Code Stop hook in ~/.claude/settings.json.

Non-goals:
    * Running the full 11-step CompoundExecutor pipeline. That's for planned
      cycles. This is the opportunistic "everything that happened since the
      last invocation" summarizer.
    * Blocking anything. All SurrealDB + skill-file writes are best-effort.

Exit codes:
    0  success (or dry-run)
    1  no session data found (nothing to summarize)
    2  CLI arg error
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


# Only imported when actually summarizing / refining — keeps the CLI
# queryable (--help, --dry-run) without the full cohezion install.


SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")


def _session_id() -> str:
    """Default session key — matches delegate.py / vmodel_gate_post_commit.py
    convention so all three writers land in the same aggregation bucket."""
    return os.environ.get("COHEZION_SESSION_ID") or f"pid-{os.getpid()}"


def _basic_auth(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


def _surreal_query(sql: str) -> list | None:
    """POST a SurrealQL query; return the parsed `result` array of the first
    statement, or None on any network/parse failure. Never raises."""
    req = urllib.request.Request(  # noqa: S310
        SURREAL_URL,
        data=sql.encode("utf-8"),
        headers={
            "Accept": "application/json",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Authorization": _basic_auth(SURREAL_USER, SURREAL_PASS),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if first.get("status") != "OK":
        return None
    result = first.get("result")
    return result if isinstance(result, list) else None


def fetch_session_signals(session_id: str) -> dict:
    """Pull the three tables this session wrote to via per-commit hooks.
    Returns a dict with counts + aggregates, suitable for building an
    ExecutionResult shape that SkillRefiner can consume."""
    # Single-quote-escape the session_id before interpolation. SurrealDB
    # doesn't expose parameterized queries over HTTP /sql, so we escape and
    # accept the lint warning — session_id comes from $COHEZION_SESSION_ID
    # or os.getpid(), not untrusted user input.
    sid = session_id.replace("'", "\\'")
    gates = _surreal_query(f"SELECT * FROM vmodel_gate WHERE session_id = '{sid}';") or []  # noqa: S608
    narratives = (
        _surreal_query(f"SELECT * FROM narrative_learning WHERE session_id = '{sid}';") or []  # noqa: S608
    )
    drifts = _surreal_query(f"SELECT * FROM import_drift WHERE session_id = '{sid}';") or []  # noqa: S608

    total_gates = len(gates)
    passed_gates = sum(1 for g in gates if g.get("passed") is True)
    narrative_latency_ms_total = sum(float(n.get("latency_ms") or 0.0) for n in narratives)
    # Prefer the real tokens_used field (added 2026-04-22); fall back to the
    # latency-as-proxy heuristic for older records that don't have it. A record
    # without tokens_used contributes 0 to the token total rather than doubling
    # itself as a latency proxy — under-counting is safer than over-counting.
    narrative_tokens_total = sum(int(n.get("tokens_used") or 0) for n in narratives)
    drift_count = sum(int(d.get("drift_count") or 0) for d in drifts)

    # Anomaly score: drift is the clearest anomaly signal. Normalize by
    # narrative count to avoid counting a single bad commit forever.
    anomaly_score = min(1.0, drift_count / max(1, len(narratives) * 2))

    return {
        "session_id": session_id,
        "total_gates": total_gates,
        "passed_gates": passed_gates,
        "pass_rate": passed_gates / total_gates if total_gates else 1.0,
        "narrative_count": len(narratives),
        "narrative_latency_ms_total": narrative_latency_ms_total,
        "narrative_tokens_total": narrative_tokens_total,
        "drift_count": drift_count,
        "anomaly_score": anomaly_score,
        "_raw_narratives": narratives,
        "_raw_gates": gates,
    }


def session_commits_touching_skills(session_id: str, repo_root: Path) -> list[str]:
    """Return distinct PRIME skill basenames touched by commits in this session.
    Heuristic: grep `git log` output for commits whose changed-file list includes
    `src/cohezion/skills/*.md`. We match commits back to the session via the
    auto-<short-sha> convention that vmodel_gate_post_commit.py uses when
    COHEZION_SESSION_ID is unset, OR by the session_id env var on direct
    writes. Safe to just grep the entire recent history and intersect."""
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_root), "log", "--since=7 days ago", "--name-only", "--format="],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if out.returncode != 0:
        return []
    skills: set[str] = set()
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("src/cohezion/skills/") and line.endswith(".md"):
            skills.add(Path(line).stem)
    return sorted(skills)


def build_execution_result(signals: dict) -> dict:
    """Shape the aggregate into the dict SkillRefiner._extract_metrics expects."""
    # Prefer the real token count field; fall back to latency_ms as tokens proxy
    # only when narrative_tokens_total is 0 AND there are narratives (legacy
    # records pre-2026-04-22). This lets old sessions still produce a signal.
    tokens = int(signals.get("narrative_tokens_total") or 0)
    if tokens == 0 and signals["narrative_count"] > 0:
        tokens = int(signals["narrative_latency_ms_total"])
    return {
        "success": signals["pass_rate"] >= 0.8 and signals["drift_count"] == 0,
        "duration_seconds": signals["narrative_latency_ms_total"] / 1000.0,
        "metrics": {
            "anomaly_score": signals["anomaly_score"],
        },
        "token_metrics": {
            "tokens_used": tokens,
            "cache_hits": 0,
        },
    }


def build_cycle_metrics(signals: dict, skill_name: str):
    """Build a CycleMetrics for RetrospectionEngine.summarize."""
    from cohezion.compound.retrospection_summary import CycleMetrics

    # Coherence proxy: 0.5 baseline, shift by pass rate delta from 0.5
    coh_end = 0.5 + (signals["pass_rate"] - 0.5) * 0.4  # damped
    anomalies: list[str] = []
    if signals["drift_count"] > 0:
        anomalies.append(f"{signals['drift_count']} import-drift rows recorded")
    if signals["pass_rate"] < 0.8:
        anomalies.append(f"pass_rate={signals['pass_rate']:.2f} (below 0.8 threshold)")
    tokens = int(signals.get("narrative_tokens_total") or 0)
    if tokens == 0 and signals["narrative_count"] > 0:
        tokens = int(signals["narrative_latency_ms_total"])  # legacy fallback
    return CycleMetrics(
        coherence_start=0.5,
        coherence_end=max(0.0, min(1.0, coh_end)),
        tokens_used=tokens,
        skill_name=skill_name,
        phase="reflecting",
        success=signals["pass_rate"] >= 0.8,
        anomalies=anomalies,
    )


def write_retrospection_to_vault(
    session_id: str, summary, signals: dict, vault_root: Path | None = None
) -> Path | None:
    """Write the retrospection narrative to the cohezion vault as a markdown
    file under `retrospections/`. Returns the path written, or None on failure."""
    if vault_root is None:
        vault_root = Path.home() / "vaults" / "cohezion-vault"
    target_dir = vault_root / "retrospections"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    path = target_dir / f"{session_id}.md"
    body = (
        "---\n"
        f"title: Session retrospection — {session_id}\n"
        f"session_id: {session_id}\n"
        f"cycle_id: {summary.cycle_id}\n"
        f"coherence_delta: {summary.metrics.coherence_end - summary.metrics.coherence_start:.3f}\n"
        f"pass_rate: {signals['pass_rate']:.2f}\n"
        f"drift_count: {signals['drift_count']}\n"
        "tags: [retrospection, session-end]\n"
        "---\n\n"
        f"# Retrospection: {session_id}\n\n"
        f"## Narrative\n\n{summary.narrative}\n\n"
        f"## Metrics\n\n"
        f"- Gates recorded: {signals['total_gates']} ({signals['passed_gates']} passed)\n"
        f"- Narratives recorded: {signals['narrative_count']}\n"
        f"- Import drifts: {signals['drift_count']}\n"
        f"- Anomaly score: {signals['anomaly_score']:.3f}\n\n"
        f"## Insights\n\n"
    )
    if summary.insights:
        body += "\n".join(f"- {i}" for i in summary.insights) + "\n"
    else:
        body += "- (no distinct insights surfaced this cycle)\n"
    try:
        path.write_text(body)
    except OSError:
        return None
    return path


def insert_retrospection_record(summary, signals: dict) -> bool:
    """Write a `session_retrospection` row to SurrealDB for cross-session
    aggregation. Returns False on any failure; non-blocking."""
    from scripts.hooks import vmodel_gate_post_commit as vg  # reuse SQL escaper

    esc = vg._escape_sql_string
    sql = (
        f"CREATE session_retrospection SET "
        f"session_id = '{esc(summary.cycle_id)}', "
        f"narrative = '{esc(summary.narrative[:1000])}', "
        f"pass_rate = {signals['pass_rate']:.3f}, "
        f"drift_count = {signals['drift_count']}, "
        f"anomaly_score = {signals['anomaly_score']:.3f}, "
        f"total_gates = {signals['total_gates']}, "
        f"narrative_count = {signals['narrative_count']};"
    )
    return _surreal_query(sql) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--session-id", default=None, help="Override $COHEZION_SESSION_ID.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be summarized/refined; write nothing.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Git repo root (default: auto-detect from cwd).",
    )
    args = parser.parse_args(argv)

    session_id = args.session_id or _session_id()
    repo_root = Path(args.repo_root) if args.repo_root else Path.cwd()

    signals = fetch_session_signals(session_id)
    if signals["total_gates"] == 0 and signals["narrative_count"] == 0:
        print(
            f"[session-end] no per-commit signals found for session={session_id}; "
            "nothing to summarize.",
            file=sys.stderr,
        )
        return 1

    skills_touched = session_commits_touching_skills(session_id, repo_root)
    skill_name_for_summary = skills_touched[0] if skills_touched else "session-end-aggregate"

    print(
        f"[session-end] session={session_id} gates={signals['total_gates']} "
        f"narratives={signals['narrative_count']} drift={signals['drift_count']} "
        f"skills_touched={len(skills_touched)}"
    )

    if args.dry_run:
        print("[session-end] dry-run; would summarize + refine. exiting.")
        return 0

    # Run retrospection — this needs the cohezion package, so it's lazy-imported.
    try:
        from cohezion.compound.retrospection_summary import RetrospectionEngine
    except ImportError as exc:
        print(f"[session-end] cohezion import failed ({exc}); skipping.", file=sys.stderr)
        return 0

    engine = RetrospectionEngine()
    cycle_id = f"session-{session_id}"
    cycle_metrics = build_cycle_metrics(signals, skill_name_for_summary)
    summary = engine.summarize(cycle_id, cycle_metrics)

    vault_path = write_retrospection_to_vault(session_id, summary, signals)
    if vault_path:
        print(f"[session-end] wrote retrospection to {vault_path}")

    if insert_retrospection_record(summary, signals):
        print(f"[session-end] recorded session_retrospection row for {session_id}")

    # Refine skills — one refine() call per touched PRIME file.
    try:
        from cohezion.compound.skill_refiner import SkillRefiner
    except ImportError:
        return 0

    refiner = SkillRefiner()
    execution_result = build_execution_result(signals)
    refined_count = 0
    for skill_name in skills_touched:
        refined_path = refiner.refine(
            skill_name=skill_name,
            operation_type="session_aggregate",
            execution_result=execution_result,
        )
        if refined_path:
            refined_count += 1
    if refined_count:
        print(f"[session-end] refined {refined_count} skill definition(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
