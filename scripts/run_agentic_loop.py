#!/usr/bin/env python3
"""Agentic compound loop — local inference via Lemonade OmniRouter on :13305.

Populates a backlog from PRIME skills and runs LoopCoordinator.
All inference routed through the single OmniRouter; no per-port addresses.

Usage:
    uv run python scripts/run_agentic_loop.py                # 10 skills, 5 min sprints
    uv run python scripts/run_agentic_loop.py --skills 20    # larger backlog
    uv run python scripts/run_agentic_loop.py --dry-run      # verify connectivity only
    uv run python scripts/run_agentic_loop.py --skills 5 --sprint 120  # short sprints
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator, LoopTask
from cohezion.compound.autonomous_loop.local_executor import get_tier_health, warmup_tiers
from cohezion.config.defaults import LEMONADE_BASE_URL
from cohezion.inference.oom_guard import check_ram, verify_all_bounded


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agentic_loop")


def _check_router(base_url: str) -> bool:
    try:
        req = urllib.request.Request(f"{base_url}/api/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            d = json.loads(resp.read())
            models = d if isinstance(d, list) else d.get("models", d.get("data", []))
            logger.info("OmniRouter healthy: %d models available", len(models))
            return True
    except Exception as exc:
        logger.error("OmniRouter unreachable at %s: %s", base_url, exc)
        return False


def _warmup_and_show_tiers(base_url: str, skip_warmup: bool = False) -> None:
    """Pre-load all compute tiers and display device placement."""
    if not skip_warmup:
        logger.info("Warming up compute tiers (NPU / iGPU / CPU) …")
        results = warmup_tiers(base_url)
        for tier, ok in results.items():
            logger.info("  tier %-6s warmup: %s", tier, "OK" if ok else "FAILED")

    health = get_tier_health(base_url)
    if health:
        logger.info("Active inference tiers:")
        tier_map = {"npu": "NPU (XDNA2)", "gpu": "iGPU (RDNA3.5)", "cpu": "CPU (x86)"}
        for model, device in sorted(health.items()):
            label = tier_map.get(device, device)
            logger.info("  %-45s → %s", model, label)
    else:
        logger.warning("Could not reach /v1/health to verify tier placement")


def _query_bughunt_state() -> dict:
    """Query SurrealDB for bughunt WIN/LOSS summary — used to size pyright tasks."""
    sql = (
        "SELECT count() AS total, "
        "count(success = true) AS wins "
        "FROM vault_neuron WHERE category = 'code_quality' GROUP ALL;"
    )
    try:
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read())
        results = data[0].get("result", []) if isinstance(data, list) else []
        row = results[0] if results else {}
        return {"total": row.get("total", 0), "wins": row.get("wins", 0)}
    except Exception as exc:
        logger.debug("SurrealDB bughunt query failed: %s", exc)
        return {"total": 0, "wins": 0}


def _query_vault_context() -> str:
    """Pull a brief session context summary from vault_neuron for the loop header."""
    sql = (
        "SELECT category, count() AS n, "
        "math::mean(quality_score) AS avg_quality "
        "FROM vault_neuron GROUP BY category ORDER BY n DESC LIMIT 5;"
    )
    try:
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read())
        results = data[0].get("result", []) if isinstance(data, list) else []
        lines = [
            f"  {r['category']}: {r['n']} records, avg_quality={r.get('avg_quality', 0):.2f}"
            for r in results
            if isinstance(r, dict)
        ]
        return "\n".join(lines) if lines else "  (no vault data)"
    except Exception as exc:
        logger.debug("Vault context query failed: %s", exc)
        return "  (vault offline)"


def _build_backlog(n: int) -> list[LoopTask]:
    """Build a loop backlog from PRIME skills + live infrastructure state.

    Queries SurrealDB to avoid adding tasks that are already saturated and
    to size pyright bughunt batches based on current WIN rate. Uses a Markov
    chain quality tracker to weight task priority by expected improvement delta.
    """
    from cohezion.compound.autonomous_loop.quality_tracker import MarkovQualityTracker
    from cohezion.core.template_engine import TemplateEngine

    # Build Markov quality tracker from vault history
    tracker = MarkovQualityTracker.from_vault()
    logger.info("Quality tracker states:\n%s", tracker.summary())

    engine = TemplateEngine()
    specs = engine.parse_all()
    with_instructions = [s for s in specs if s.instructions]
    selected = (with_instructions + [s for s in specs if not s.instructions])[:n]

    tasks: list[LoopTask] = []
    for i, spec in enumerate(selected):
        # Build a rich task that uses the skill's actual content
        domain = (spec.domain_expertise or "").strip()[:400]
        all_instructions = spec.instructions[:5] if spec.instructions else [f"Analyze {spec.name}"]
        instructions_str = "\n".join(
            f"  {j + 1}. {inst}" for j, inst in enumerate(all_instructions)
        )
        description = (
            f"[SKILL: {spec.name}]\n"
            f"Domain: {domain}\n"
            f"Instructions:\n{instructions_str}\n\n"
            f"Apply this skill pattern to the Cohezion codebase (src/cohezion/). "
            f"Identify 1-2 concrete improvements: state the file path and specific change needed. "
            f"Be precise — file:line and what to change."
        )
        # Markov-weighted priority: high P(improve) → higher priority
        markov_weight = tracker.suggest_priority_weight("skill_improvement")
        base_priority = 10 - (i % 10)
        priority = max(1, min(10, round(base_priority * markov_weight)))
        tasks.append(
            LoopTask(
                id=f"skill-{i + 1:03d}-{spec.name[:20].replace(' ', '_')}",
                description=description,
                category="skill_improvement",
                priority=priority,
                verification=(
                    f"Output names a specific file in src/cohezion/ with a concrete change for {spec.name}"
                ),
                estimated_tokens=500,
            )
        )

    # Query live state to calibrate infrastructure tasks
    bughunt = _query_bughunt_state()
    bughunt_wins = bughunt["wins"]
    bughunt_total = bughunt["total"]
    win_rate = bughunt_wins / bughunt_total if bughunt_total > 0 else 0.0
    logger.info(
        "Bughunt state from vault: %d/%d WINs (%.0f%%)", bughunt_wins, bughunt_total, win_rate * 100
    )

    # Pyright bughunt batch — scale batch size to current win rate
    batch_size = 5 if win_rate >= 0.5 else 3  # be conservative when win rate is low
    tasks.append(
        LoopTask(
            id="pyright-bughunt-batch-001",
            description=(
                f"Run Pyright bughunt (batch={batch_size}): "
                f"uv run python scripts/drivers/routine_pyright_bughunt.py --batch {batch_size}. "
                f"Current vault state: {bughunt_wins}/{bughunt_total} WINs. "
                "Pick the next unattempted errors, apply minimal fixes, verify with pyright+pytest, "
                "push WIN/LOSS to vault_neuron and code_quality_patterns.jsonl."
            ),
            category="code_quality",
            priority=9,
            verification=f"At least 1 new WIN in vault_neuron category=code_quality (currently {bughunt_wins} WINs)",
            estimated_tokens=600,
        )
    )

    # Repo health — git bloat, unpushed commits, LFS health
    tasks.append(
        LoopTask(
            id="repo-health-001",
            description=(
                "Assess repository health: run uv run python scripts/assess_git_health.py to check "
                "git bloat, unpushed commits, entire/ branch count, LFS pointer integrity. "
                "Summarize findings and flag any action items (>500MB .git/, >20 entire/ branches)."
            ),
            category="repo_health",
            priority=8,
            verification="Git health report written to SurrealDB. .git/ size reported. No critical bloat.",
            estimated_tokens=300,
        )
    )

    # OOM guard — N3 invariant verification
    tasks.append(
        LoopTask(
            id="oom-guard-verify-001",
            description="Verify all heavy models in the OmniRouter catalog have ctx_size bounded (N3 invariant): "
            "curl -s http://localhost:13305/api/v1/models and check recipe_options.ctx_size for "
            "any model >= 5GB. Any ctx_size=0 on a heavy model is a CRITICAL finding.",
            category="infrastructure",
            priority=9,
            verification="All heavy models show ctx_size <= 16384 or ctx_size=null (FLM/GGUF safe). No ctx_size=0.",
            estimated_tokens=200,
        )
    )

    # Compound loop health — cache + routing
    tasks.append(
        LoopTask(
            id="compound-loop-health-001",
            description="Assess compound engineering loop health via SurrealDB: "
            "SELECT avg(quality_score), count() FROM vault_neuron GROUP BY node; "
            "Report cache hit rate, model routing distribution per node, and flag "
            "any node with avg_quality < 0.5 as a degradation signal.",
            category="compound_health",
            priority=7,
            verification="Health report shows routing distribution. Any degraded node flagged.",
            estimated_tokens=250,
        )
    )

    # DataMesh audit
    tasks.append(
        LoopTask(
            id="datamesh-quality-001",
            description="Audit the DataMesh EventBridge SurrealDB write-through path for correctness and OOM safety. "
            "Check that queue-full is handled gracefully and ctx_size=0 guard is enforced on any "
            "model loaded through the EventBridge path.",
            category="data_mesh",
            priority=6,
            verification="EventBridge handles queue-full gracefully and ctx_size=0 guard is enforced.",
            estimated_tokens=400,
        )
    )

    # --- BMAD tasks: structured adversarial review + architecture + course correction ---

    # BMAD code review — adversarial 3-reviewer pass on recent src/cohezion changes
    bmad_review_weight = tracker.suggest_priority_weight("bmad_review")
    bmad_review_priority = max(1, min(10, round(9 * bmad_review_weight)))
    tasks.append(
        LoopTask(
            id="bmad-review-recent-changes-001",
            description=(
                "[BMAD: Dev (James) — Code Review]\n"
                "Apply BMAD v6.3.0 adversarial 3-reviewer pattern to recent src/cohezion/ changes.\n\n"
                "1. Gather context: run `git diff HEAD~3 --stat` to identify changed files\n"
                "2. Blind Hunter review: read diff only — flag logic errors, dead code, type mismatches\n"
                "3. Edge Case Hunter review: target boundary conditions, null guards, off-by-one errors\n"
                "4. Acceptance Auditor: verify test coverage exists for changed functions\n"
                "5. Triage findings into P0 (critical/block), P1 (high), P2 (medium)\n\n"
                "Output: structured list — file:line + finding + severity (P0/P1/P2). "
                "Flag any P0 explicitly at the top."
            ),
            category="bmad_review",
            priority=bmad_review_priority,
            verification="Output contains structured findings with file:line and P0/P1/P2 severity labels.",
            estimated_tokens=600,
        )
    )

    # BMAD architecture assessment — Winston persona reviews compound loop architecture
    bmad_arch_weight = tracker.suggest_priority_weight("bmad_architecture")
    bmad_arch_priority = max(1, min(10, round(8 * bmad_arch_weight)))
    tasks.append(
        LoopTask(
            id="bmad-arch-compound-loop-001",
            description=(
                "[BMAD: Architect (Winston) — Architecture Assessment]\n"
                "Apply BMAD v6.3.0 architecture review to the compound autonomous loop.\n\n"
                "Target: src/cohezion/compound/autonomous_loop/ and scripts/run_agentic_loop.py\n\n"
                "1. Gather context: read coordinator.py, local_executor.py, quality_tracker.py\n"
                "2. Assess: does the Markov→priority feedback loop close correctly?\n"
                "3. Assess: is vault_neuron write-back idempotent (no duplicate inserts on retry)?\n"
                "4. Assess: does the BMAD Challenger/Solver pattern have a concrete wiring target?\n"
                "5. Output: 1-2 concrete architectural improvement recommendations — "
                "state the file:line and the specific change, no speculation."
            ),
            category="bmad_architecture",
            priority=bmad_arch_priority,
            verification=(
                "Output contains architecture findings with specific file:line references "
                "and actionable improvement recommendations."
            ),
            estimated_tokens=500,
        )
    )

    # BMAD correct-course — fires with elevated priority if quality tracker shows regression
    bmad_course_state = tracker._current.get("skill_improvement", "failing")  # noqa: SLF001
    bmad_course_priority = 10 if bmad_course_state == "regressing" else 5
    tasks.append(
        LoopTask(
            id="bmad-correct-course-001",
            description=(
                "[BMAD: PM (John) — Correct Course]\n"
                f"Current Markov quality state for skill_improvement: {bmad_course_state.upper()}\n\n"
                "Apply BMAD v6.3.0 correct-course pattern to detect loop drift:\n\n"
                "1. Query vault_neuron: SELECT category, avg(quality_score), count() "
                "FROM vault_neuron GROUP BY category ORDER BY avg_quality ASC LIMIT 5\n"
                "2. Compare: which categories have avg_quality < 0.5 (drifting)?\n"
                "3. Identify: is the drift from poor task descriptions, model routing, "
                "or systemic issues (e.g., all NPU fallbacks going to CPU)?\n"
                "4. Recommend: minimum-change correction — 1 specific adjustment to "
                "task priority, model routing, or skill selection that addresses root cause.\n\n"
                "Output: root cause + one concrete correction. No infrastructure. No new modules."
            ),
            category="bmad_governance",
            priority=bmad_course_priority,
            verification=(
                "Output identifies at least 1 drifting category with avg_quality < 0.5 "
                "OR confirms all categories are healthy (avg >= 0.7)."
            ),
            estimated_tokens=350,
        )
    )

    infra_count = 5
    bmad_count = 3
    logger.info(
        "Backlog built: %d tasks (%d from skills, %d infrastructure, %d BMAD)",
        len(tasks),
        len(selected),
        infra_count,
        bmad_count,
    )
    return tasks


def _run_rzero(base_url: str, n_tasks: int, n_episodes: int) -> None:
    """Run R-Zero Challenger/Solver co-evolution episodes and print results."""
    from cohezion.compound.autonomous_loop.rzero_challenger import RZeroChallengerExecutor

    logger.info("=" * 60)
    logger.info("R-Zero Co-Evolution Mode")
    logger.info("  Episodes : %d", n_episodes)
    logger.info("  Tasks/ep : %d", n_tasks)
    logger.info("  Challenger model: llama3.2-1b-FLM (NPU)")
    logger.info("  Solver model    : Gemma-4-E4B-it-GGUF (iGPU)")
    logger.info("=" * 60)

    executor = RZeroChallengerExecutor(base_url=base_url)
    all_rewards: list[float] = []

    try:
        for ep in range(1, n_episodes + 1):
            logger.info("Episode %d/%d …", ep, n_episodes)
            result = executor.run_episode(n_tasks=n_tasks)
            all_rewards.append(result.challenger_reward)
    except KeyboardInterrupt:
        logger.info("R-Zero interrupted by user")

    if all_rewards:
        logger.info("=" * 60)
        logger.info("R-Zero summary: %d episodes", len(all_rewards))
        logger.info(
            "  Challenger rewards: %s",
            " | ".join(f"{r:.2f}" for r in all_rewards),
        )
        logger.info("  Mean reward: %.2f", sum(all_rewards) / len(all_rewards))
        logger.info("  (0.5 = perfect 50%% calibration; 1.0 = impossible)")
        logger.info("  Results pushed to vault_neuron (category=skill_improvement)")
        logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic compound loop with local inference")
    parser.add_argument(
        "--skills", type=int, default=10, help="Number of PRIME skills to include (default: 10)"
    )
    parser.add_argument(
        "--sprint", type=float, default=300.0, help="Sprint duration in seconds (default: 300)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=50_000, help="Token budget for the loop (default: 50000)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity and exit")
    parser.add_argument("--base-url", default=LEMONADE_BASE_URL, help="OmniRouter base URL")
    parser.add_argument(
        "--rzero",
        action="store_true",
        help="Run R-Zero Challenger/Solver co-evolution instead of standard loop",
    )
    parser.add_argument(
        "--rzero-tasks", type=int, default=8, help="Tasks per R-Zero episode (default: 8)"
    )
    parser.add_argument(
        "--rzero-episodes", type=int, default=3, help="Number of R-Zero episodes (default: 3)"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Cohezion Agentic Loop — Lemonade OmniRouter: %s", args.base_url)
    logger.info("=" * 60)

    # Pull live vault context — keeps loop state-aware without holding it in memory
    vault_ctx = _query_vault_context()
    logger.info("Vault neuron summary (top categories):\n%s", vault_ctx)

    # Pre-flight checks
    if not _check_router(args.base_url):
        logger.error("Aborting: OmniRouter not reachable. Start with: lemond --port 13305")
        sys.exit(1)

    _, violations = verify_all_bounded(args.base_url)
    if violations:
        logger.error("N3 VIOLATION: heavy models with ctx_size=0: %s", violations)
        logger.error("Run: oom_guard.scan_and_harden() to fix before continuing")
        sys.exit(1)

    safe, free_gb = check_ram(min_free_gb=8.0)
    if not safe:
        logger.warning("RAM low: %.1f GiB free (8 GiB floor). Proceeding with caution.", free_gb)
    else:
        logger.info("RAM: %.1f GiB free — OK", free_gb)

    # Warmup all three compute tiers (fixes stale NPU FLM context; loads CPU tier)
    _warmup_and_show_tiers(args.base_url, skip_warmup=args.dry_run)

    if args.dry_run:
        logger.info("Dry run complete — all pre-flight checks passed")
        return

    # R-Zero co-evolution mode
    if args.rzero:
        _run_rzero(args.base_url, n_tasks=args.rzero_tasks, n_episodes=args.rzero_episodes)
        return

    # Build backlog
    tasks = _build_backlog(args.skills)

    # Configure and run loop
    config = LoopConfig(
        use_local_inference=True,
        local_base_url=args.base_url,
        max_tokens=args.max_tokens,
        sprint_duration_seconds=args.sprint,
        cloud_escalation_threshold=3,
        min_free_ram_gb=8.0,
    )

    coordinator = LoopCoordinator(config)
    coordinator._backlog = tasks
    logger.info(
        "Starting loop: %d tasks, %.0fs sprints, %d token budget",
        len(tasks),
        config.sprint_duration_seconds,
        config.max_tokens,
    )
    t0 = time.monotonic()

    try:
        report = coordinator.run()
    except KeyboardInterrupt:
        logger.info("Loop interrupted by user")
        return

    elapsed = time.monotonic() - t0
    local_tokens = sum(s.local_tokens for s in report.sprint_results)
    cloud_tokens = sum(s.cloud_tokens for s in report.sprint_results)

    logger.info("=" * 60)
    logger.info("Loop complete in %.1fs", elapsed)
    logger.info("  Tasks completed : %d", report.tasks_completed)
    logger.info("  Tasks failed    : %d", report.tasks_failed)
    logger.info("  Local tokens    : %d (cost: $0.00)", local_tokens)
    logger.info("  Cloud tokens    : %d", cloud_tokens)
    logger.info("  Sprints         : %d", len(report.sprint_results))

    node_counts: dict[str, int] = {}
    fallback_count = 0
    for r in report.results:
        n = r.get("node", "?")
        node_counts[n] = node_counts.get(n, 0) + 1
        if r.get("fallback"):
            fallback_count += 1
    logger.info(
        "  Routing         : %s", " | ".join(f"{n}={c}" for n, c in sorted(node_counts.items()))
    )
    if fallback_count:
        logger.info("  NPU fallbacks   : %d", fallback_count)
    logger.info("=" * 60)

    # Print per-task summary
    for r in report.results[:20]:
        status = "✓" if r["success"] else "✗"
        node = r.get("node", "?")[:5]
        model = r.get("model", "?")[:18]
        ms = r.get("elapsed_ms", 0)
        fb = "↓" if r.get("fallback") else " "
        logger.info(
            "  %s %s%s %-38s  %s  %dms  %d tok",
            status,
            node,
            fb,
            r["task_id"][:38],
            model,
            ms,
            r.get("tokens", 0),
        )

    _push_loop_results_to_vault(report.results, elapsed)


def _push_loop_results_to_vault(results: list[dict], elapsed_s: float) -> None:
    """Push per-task results to vault_neuron for quality tracking.

    quality_score = 1.0 (WIN) if model produced non-empty output, else 0.0 (LOSS).
    Enables _query_vault_context() on the next run to show real win rates.
    """
    wins = sum(1 for r in results if r.get("success"))
    total = len(results)
    win_rate = wins / total if total > 0 else 0.0

    rows = []
    for r in results:
        tid = r["task_id"].replace("'", "")[:80]
        success_str = "true" if r.get("success") else "false"
        quality = 1.0 if r.get("success") else 0.0
        node = r.get("node", "?").replace("'", "")[:20]
        tokens = r.get("tokens", 0)
        rows.append(
            f"{{task_id: 'loop:{tid}', category: 'skill_improvement', "
            f"success: {success_str}, quality_score: {quality}, "
            f"node: '{node}', tokens: {tokens}, recorded_at: time::now()}}"
        )

    # Batch insert
    sql = "INSERT INTO vault_neuron [" + ", ".join(rows) + "];"
    try:
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            resp.read()
        logger.info(
            "Vault: pushed %d task results (%.0f%% WIN rate, %.1fs elapsed)",
            total,
            win_rate * 100,
            elapsed_s,
        )
    except Exception as exc:
        logger.debug("Vault push failed (non-fatal): %s", exc)


if __name__ == "__main__":
    main()
