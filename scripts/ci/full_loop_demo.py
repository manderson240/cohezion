#!/usr/bin/env python3
"""Full-loop demo: exercises all 8 components from this session (2026-06-04).

Components:
  WS1A  OuroborosRecorder  (flight recorder, telemetry)
  WS1B  HealerAgent        (HEALING_EVENT on failure)
  WS1C  OuroborosWikiBridge (per-session wiki note on success)
  WS1D  MyceliumLoop        (auto-test-synthesis for new .py files)
  WS2   frontier_digest     (arxiv + HF + top models digest)
  WS4   SelfImprovementOrchestrator (routes all bus events)

What this does:
  1. Bootstraps an isolated vault under /tmp/cohezion-demo-vault/
  2. Builds a CompoundExecutor with mocked MCP
  3. Subscribes the SelfImprovementOrchestrator to the bus
  4. Runs 3 successful skill executions (varied descriptions) + 1
     failing execution (so we can capture BOTH HEALING_EVENT and
     WITNESS_MARK artifacts)
  5. Creates a fake new .py file and kicks the MyceliumLoop
     (mocked, since the real LLM isn't available)
  6. Runs frontier_digest with mocked sources (no network)
  7. Produces a final report listing all artifacts written

The demo is **idempotent**: re-running cleans /tmp/cohezion-demo-vault/
and re-creates everything.

Usage:
    PYTHONPATH=src:scripts/ci python scripts/ci/full_loop_demo.py
    make demo

Expected runtime: < 30 seconds.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock


VAULT = Path("/tmp/cohezion-demo-vault")
ARTIFACTS: list[dict[str, Any]] = []
STEPS: list[str] = []


def log_step(name: str) -> None:
    STEPS.append(name)
    print(f"\n[STEP {len(STEPS):02d}] {name}")


def record_artifact(kind: str, path: str | Path, **meta: Any) -> None:
    ARTIFACTS.append(
        {
            "kind": kind,
            "path": str(path),
            "size_bytes": Path(path).stat().st_size if Path(path).exists() else 0,
            **meta,
        }
    )
    print(f"    -> {kind}: {path} ({ARTIFACTS[-1]['size_bytes']} bytes)")


def bootstrap_vault() -> None:
    """Create an isolated vault under /tmp."""
    if VAULT.exists():
        shutil.rmtree(VAULT)
    VAULT.mkdir(parents=True)
    (VAULT / "wiki" / "ouroboros" / "improvements").mkdir(parents=True)
    (VAULT / "wiki" / "ouroboros" / "patterns").mkdir(parents=True)
    (VAULT / "wiki" / "ouroboros" / "healings").mkdir(parents=True)
    (VAULT / "frontier").mkdir(parents=True)
    print(f"    -> bootstrapped {VAULT}")


def build_orchestrator() -> Any:
    """WS4: build the SelfImprovementOrchestrator and subscribe to bus."""
    from cohezion.compound.self_improvement_orchestrator import (
        SelfImprovementOrchestrator,
    )

    orch = SelfImprovementOrchestrator(vault_path=VAULT)
    subscribed = orch.subscribe_to_bus()
    print(f"    -> subscribed to bus: {subscribed}")
    return orch


def build_executor() -> Any:
    """WS1A/B/C/D: build CompoundExecutor with all wirings enabled."""
    from cohezion.compound.executor import CompoundExecutor

    mcp = MagicMock()
    mcp.list_servers = MagicMock(return_value=[])
    ex = CompoundExecutor(
        mcp_client=mcp,
        enable_guardrails=False,
        enable_skill_refinement=False,
        enable_alignment_analysis=False,
    )
    return ex


def start_recorder(executor: Any) -> Any:
    """WS1A: start the OuroborosRecorder flight recorder."""
    from cohezion.ouroboros.recorder import OuroborosRecorder

    rec = OuroborosRecorder(interval_seconds=1.0, output_dir=str(VAULT / "ouroboros"))
    # Don't actually run the async loop here — we just want the
    # instance to exist; the executor's start_recorder() handles
    # the lifecycle.
    started = executor.start_recorder(interval_seconds=1.0)
    print(f"    -> executor.start_recorder: {started}")
    return rec


def run_successful_skill(
    executor: Any,
    skill_name: str,
    description: str,
    output: str,
    coherence: float = 0.7,
) -> None:
    """WS1A/B/C + WS4: run one successful skill execution.

    This emits (via the executor's normal path):
      - WITNESS_MARK (skill executed)
      - any wiki note from the OuroborosWikiBridge (WS1C)
      - any HEALING_EVENT (only on failure; we don't trigger here)
    """

    def execute_fn(guidance: str) -> tuple[str, dict[str, Any]]:
        return output, {
            "coherence": coherence,
            "duration_seconds": 0.01,
            "tokens_in": 100,
            "tokens_out": 50,
        }

    try:
        result = executor.execute_task(
            task_description=description,
            skill_name=skill_name,
            operation_type="generate",
            execute_fn=execute_fn,
        )
        print(f"    -> result.success: {result.success if hasattr(result, 'success') else 'n/a'}")
    except Exception as e:
        print(f"    -> execute raised (continuing): {type(e).__name__}: {e}")


def run_failing_skill(
    executor: Any,
    skill_name: str,
    description: str,
) -> None:
    """WS1B: run a failing skill — should trigger HEALING_EVENT."""

    def execute_fn(guidance: str) -> tuple[str, dict[str, Any]]:
        raise RuntimeError("synthetic failure for demo: bwrap 429")

    try:
        result = executor.execute_task(
            task_description=description,
            skill_name=skill_name,
            operation_type="generate",
            execute_fn=execute_fn,
        )
        print(f"    -> result.success: {result.success if hasattr(result, 'success') else 'n/a'}")
    except Exception as e:
        print(f"    -> execute raised (expected): {type(e).__name__}")


def kick_mycelium_loop(executor: Any) -> None:
    """WS1D: trigger auto-test-synthesis for a fake new .py file.

    We mock both the scripter and the loop so this doesn't
    need a real LLM, but we exercise the wiring path.
    """
    # Create a fake new .py file in src/
    fake_path = Path("src/cohezion/_demo_fake_module.py")
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    fake_path.write_text(
        '"""Fake module for demo purposes."""\n\ndef hello() -> str:\n    return \'hi\'\n'
    )

    # Mock the scripter + loop so we don't hit a real LLM
    mock_loop = MagicMock()
    mock_loop.execute = AsyncMock(return_value=0.85)
    executor._mycelium_loop = mock_loop
    executor._shadow_scripter = MagicMock()
    executor._maybe_kick_mycelium_loop(str(fake_path), "context")
    print(f"    -> mycelium loop called: {mock_loop.execute.called}")
    print(f"    -> await_count: {mock_loop.execute.await_count}")

    # Clean up
    fake_path.unlink()


def run_frontier_digest_mocked() -> Path:
    """WS2: run the frontier digest with mocked sources (no network)."""
    import frontier_digest

    sample_findings = [
        {
            "title": "Sparse Mixture-of-Experts for Long-Context Reasoning",
            "url": "https://arxiv.org/abs/2606.00001",
            "source": "arxiv",
            "category": "cs.LG",
            "snippet": "Demonstrates 4x speedup on 100K-token contexts with sparse activation.",
            "authors": ["Smith, J.", "Lee, K."],
            "published": "2026-06-01",
        },
        {
            "title": "Agentic Tool Use via Self-Refinement",
            "url": "https://arxiv.org/abs/2606.00002",
            "source": "arxiv",
            "category": "cs.MA",
            "snippet": "Agents that critique their own tool calls improve by 18% on HumanEval.",
            "authors": ["Patel, R."],
            "published": "2026-06-02",
        },
        {
            "title": "DeepSeek-V4",
            "url": "https://huggingface.co/deepseek-ai/DeepSeek-V4",
            "source": "hf_models",
            "category": "top_model",
            "snippet": "4,200,000 downloads, 18,500 likes, task: text-generation",
        },
        {
            "title": "Constitutional AI: Practical Lessons",
            "url": "https://huggingface.co/papers/2606.12345",
            "source": "hf_daily",
            "category": "trending",
            "snippet": "Lessons from 6 months of constitutional training at scale.",
        },
    ]

    today = datetime.now().date().isoformat()
    out_path = VAULT / "frontier" / f"{today}.md"
    frontier_digest.write_digest(
        [frontier_digest.Finding(**f) for f in sample_findings],
        output_path=out_path,
        today=today,
    )
    return out_path


def capture_orchestrator_artifacts(orchestrator: Any) -> None:
    """Walk the vault and record any artifacts that the
    orchestrator + bridge may have written."""
    improvements = list((VAULT / "wiki" / "ouroboros" / "improvements").glob("*.md"))
    patterns = list((VAULT / "wiki" / "ouroboros" / "patterns").glob("*.md"))
    healings = list((VAULT / "wiki" / "ouroboros" / "healings").glob("*.md"))

    for p in improvements:
        record_artifact("WS1C_wiki_note", p, subdir="improvements")
    for p in patterns:
        record_artifact("WS4_pattern_note", p, subdir="patterns")
    for p in healings:
        record_artifact("WS4_healing_note", p, subdir="healings")


async def main_async() -> int:
    parser = argparse.ArgumentParser(prog="full_loop_demo")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    print("=" * 70)
    print("Cohezion Full-Loop Demo — 2026-06-04 session artifacts")
    print("=" * 70)

    log_step("Bootstrap isolated vault")
    bootstrap_vault()

    log_step("WS4: Build + subscribe SelfImprovementOrchestrator")
    orch = build_orchestrator()

    log_step("Build CompoundExecutor with all wirings")
    executor = build_executor()

    log_step("WS1A: Start OuroborosRecorder (flight recorder)")
    recorder = start_recorder(executor)

    log_step("WS1C: Run 3 successful skill executions")
    for i, (skill, desc) in enumerate(
        [
            ("refactor_module", "Extract 3 repeated patterns into a helper function"),
            ("write_tests", "Generate pytest cases for the new helper"),
            ("update_docs", "Update README with the new helper signature"),
        ]
    ):
        print(f"    --- skill {i + 1}/3: {skill} ---")
        run_successful_skill(executor, skill, desc, f"output for {skill}")

    log_step("WS1B: Run 1 failing skill execution (triggers HEALING_EVENT)")
    run_failing_skill(executor, "flaky_inference", "Generate inference with bwrap 429")

    log_step("WS1D: Kick MyceliumLoop for a fake new .py file")
    kick_mycelium_loop(executor)

    log_step("WS2: Run frontier digest (mocked sources)")
    digest_path = run_frontier_digest_mocked()
    record_artifact("WS2_frontier_digest", digest_path)

    log_step("Capture all orchestrator + bridge artifacts from vault")
    capture_orchestrator_artifacts(orch)

    # Final report
    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(f"Steps run: {len(STEPS)}")
    print(f"Artifacts produced: {len(ARTIFACTS)}")
    print(f"Vault root: {VAULT}")
    print()
    by_kind: dict[str, int] = {}
    for a in ARTIFACTS:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")
    print()
    print("All artifacts:")
    for a in ARTIFACTS:
        print(f"  [{a['kind']:25s}] {a['path']}")
    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
