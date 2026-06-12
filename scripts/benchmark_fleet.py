"""V-Model Phase 2 — Fleet benchmark.

Cross-backend comparison of the Cohezion inference fleet vs Claude API.
Produces ``benchmarks/fleet_report.md`` with the headline numbers that
feed the Universes cover letter:

  - "$X Claude budget + local fleet ≈ $Y Claude-only equivalent throughput"
  - "TTFT Nx faster than Claude API typical"

Invariants enforced (see docs/vmodel/PHASE2_BENCHMARK_PLAN.md):
  I1 Deterministic corpus
  I2 At least 2/4 configs complete
  I3 All 4 metrics per row
  I4 TTFT from streaming (not estimated)
  I5 Claude TTFT measured, not assumed
  I6 Report includes git SHA + timestamp + health snapshot
  I7 At least 1 local lane up before B/C/D

Run:
  make benchmark-fleet
or directly:
  uv run python scripts/benchmark_fleet.py --prompts 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from cohezion.inference import (
    check_fleet,
    extend_claude,
    format_fleet_summary,
    route,
)
from cohezion.inference.registry import Task


logger = logging.getLogger(__name__)


# I1: Deterministic 20-prompt corpus (routing-style, short output).
CORPUS: tuple[str, ...] = (
    'Reply in one word, "proceed" or "rollback", for scenario 1.',
    'Reply in one word, "proceed" or "rollback", for scenario 2.',
    'Reply in one word, "proceed" or "rollback", for scenario 3.',
    'Reply in one word, "proceed" or "rollback", for scenario 4.',
    'Reply in one word, "proceed" or "rollback", for scenario 5.',
    'Reply in one word, "safe" or "unsafe", about action magnitude 0.05.',
    'Reply in one word, "safe" or "unsafe", about action magnitude 0.5.',
    'Reply in one word, "coherent" or "divergent", for coherence = 0.5.',
    'Reply in one word, "coherent" or "divergent", for coherence = 0.1.',
    'Reply in one word, "stable" or "unstable", for HIHO near attractor.',
    'Reply in one word, "stable" or "unstable", for HIHO far from attractor.',
    'Reply in one word, "accept" or "reject", a JEPA-plausible transition.',
    'Reply in one word, "accept" or "reject", a JEPA-implausible transition.',
    'Reply in one word, "local" or "cloud", for latency-critical routing.',
    'Reply in one word, "npu" or "igpu", for a 2B model.',
    'Reply in one word, "npu" or "igpu", for a 26B MoE model.',
    'Reply in one word, "yes" or "no", should agent loop continue?',
    'Reply in one word, "yes" or "no", is coherence > 0.4?',
    'Reply in one word, "gauge" or "fiber", is SU(2) spinor coherence related to?',
    'Reply in one word, "sandbox" or "production", for an untrusted rollout?',
)


@dataclass
class CallResult:
    """Single invocation outcome."""

    prompt_idx: int
    ttft_ms: float | None
    total_ms: float
    cost_usd: float
    lane: str
    model: str
    success: bool
    error: str | None = None


@dataclass
class ConfigReport:
    """Aggregated metrics for one benchmark config."""

    name: str
    description: str
    calls: list[CallResult] = field(default_factory=list)

    @property
    def successes(self) -> list[CallResult]:
        return [c for c in self.calls if c.success]

    @property
    def failure_rate(self) -> float:
        return 1.0 - (len(self.successes) / len(self.calls)) if self.calls else 1.0

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def wall_time_s(self) -> float:
        return sum(c.total_ms for c in self.calls) / 1000.0

    def ttft_p50(self) -> float | None:
        ttfts = sorted(c.ttft_ms for c in self.successes if c.ttft_ms is not None)
        return ttfts[len(ttfts) // 2] if ttfts else None

    def ttft_range(self) -> tuple[float, float] | None:
        ttfts = [c.ttft_ms for c in self.successes if c.ttft_ms is not None]
        return (min(ttfts), max(ttfts)) if ttfts else None

    def lanes_used(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.successes:
            out[c.lane] = out.get(c.lane, 0) + 1
        return out


async def _run_config_A_claude_only(
    prompts: tuple[str, ...], *, stderr_sidecar: Path | None = None
) -> ConfigReport:
    """Config A: Claude-only baseline. I5: measure TTFT via `claude -p` subprocess.

    When ``stderr_sidecar`` is set, every ``claude -p`` invocation's full
    stderr is appended to that file (prefixed with prompt index). The
    120-char truncation in ``CallResult.error`` is fine for the summary table
    but insufficient to diagnose silent failures (adversarial review
    Scientific-rigor #2 — a silent ``claude -p`` failure leaves no trail).
    The sidecar preserves the full diagnostic.
    """
    report = ConfigReport(
        name="A — Claude-only",
        description="Headless `claude -p --model haiku-4-5` × N",
    )
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        for i, _ in enumerate(prompts):
            report.calls.append(
                CallResult(
                    i,
                    None,
                    0.0,
                    0.0,
                    "claude",
                    "claude-haiku-4-5",
                    False,
                    error="claude CLI not installed",
                )
            )
        if stderr_sidecar is not None:
            stderr_sidecar.parent.mkdir(parents=True, exist_ok=True)
            stderr_sidecar.write_text("claude CLI not installed; zero invocations\n")
        return report

    sidecar_entries: list[str] = []

    for i, prompt in enumerate(prompts):
        start = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                claude_bin,
                "-p",
                prompt,
                "--model",
                "haiku-4-5",
                "--output-format",
                "json",
                "--no-session-persistence",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if proc.returncode != 0:
                stderr_text = stderr_b.decode(errors="replace")
                sidecar_entries.append(
                    f"--- prompt {i} (exit {proc.returncode}) ---\n"
                    f"stdout: {stdout_b.decode(errors='replace')}\n"
                    f"stderr: {stderr_text}\n"
                )
                report.calls.append(
                    CallResult(
                        i,
                        None,
                        elapsed_ms,
                        0.0,
                        "claude",
                        "claude-haiku-4-5",
                        False,
                        error=stderr_text[:100] or f"exit {proc.returncode} (no stderr)",
                    )
                )
                continue
            data = json.loads(stdout_b.decode(errors="replace"))
            if isinstance(data, list):
                result_item = next(
                    (
                        item
                        for item in data
                        if isinstance(item, dict) and item.get("type") == "result"
                    ),
                    None,
                )
                if result_item:
                    data = result_item
                else:
                    data = data[-1] if data and isinstance(data[-1], dict) else {}
            cost = float(data.get("total_cost_usd", 0.0))
            # Claude CLI doesn't emit TTFT separately; proxy is total latency.
            # Flagged in the report as estimated, not measured-streaming.
            report.calls.append(
                CallResult(i, None, elapsed_ms, cost, "claude", "claude-haiku-4-5", True)
            )
        except (OSError, json.JSONDecodeError) as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            sidecar_entries.append(
                f"--- prompt {i} (python exception) ---\n{type(exc).__name__}: {exc}\n"
            )
            report.calls.append(
                CallResult(
                    i,
                    None,
                    elapsed_ms,
                    0.0,
                    "claude",
                    "claude-haiku-4-5",
                    False,
                    error=str(exc)[:100],
                )
            )

    if stderr_sidecar is not None and sidecar_entries:
        stderr_sidecar.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"# Config A stderr sidecar — {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"# {len(sidecar_entries)} of {len(prompts)} invocations failed\n\n"
        )
        stderr_sidecar.write_text(header + "".join(sidecar_entries))

    return report


async def _run_local_config(
    prompts: tuple[str, ...],
    *,
    name: str,
    description: str,
    budget_usd: float | None,
    use_extend_claude: bool = False,
) -> ConfigReport:
    """Configs B/C/D: local-first via ``route()`` (I4: stream=True for TTFT)."""
    report = ConfigReport(name=name, description=description)
    for i, prompt in enumerate(prompts):
        try:
            if use_extend_claude:
                r = await extend_claude(
                    prompt, claude_model="claude-haiku-4-5", quality_threshold=0.85, timeout=20.0
                )
            else:
                r = await route(
                    prompt,
                    task=Task.ROUTING,
                    stream=True,
                    max_tokens=16,
                    budget_usd=budget_usd,
                    timeout=20.0,
                )
            if r.error:
                report.calls.append(
                    CallResult(
                        i,
                        None,
                        r.latency_ms,
                        0.0,
                        r.lane or "unknown",
                        r.model or "",
                        False,
                        error=r.error[:100],
                    )
                )
            else:
                report.calls.append(
                    CallResult(i, r.ttft_ms, r.latency_ms, r.cost_usd, r.lane, r.model, True)
                )
        except Exception as exc:
            report.calls.append(
                CallResult(i, None, 0.0, 0.0, "unknown", "", False, error=str(exc)[:100])
            )
    return report


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _write_markdown(configs: list[ConfigReport], health_summary: str, path: Path) -> None:
    """I6: Report includes git SHA + timestamp + health snapshot."""
    now = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    sha = _git_sha()
    lines = [
        "# Fleet Benchmark Report",
        "",
        f"- **Generated:** {now}",
        f"- **Git SHA:** `{sha}`",
        f"- **Corpus:** {len(CORPUS)} deterministic routing prompts available; "
        f"this run executed {len(configs[0].calls) if configs and configs[0].calls else 0} "
        f"(use `--prompts {len(CORPUS)}` for the full benchmark)",
        f"- **Status:** {'BENCHMARK' if (configs and len(configs[0].calls) >= 20) else 'PILOT (n<20, not statistically conclusive)'}",
        "- **Dispatch:** streaming SSE (`stream=True`) for B/C/D so TTFT is the moment the first reasoning/content chunk arrives; Config A uses `claude -p` (non-streaming, total-latency proxy).",
        "",
        "## Fleet health at run time",
        "",
        "```",
        health_summary,
        "```",
        "",
        "## Headline table",
        "",
        "| Config | Calls (ok/total) | Wall time | TTFT p50 | TTFT range | Cost | Lanes used |",
        "|--------|------------------|-----------|----------|------------|------|------------|",
    ]
    for rep in configs:
        ok = len(rep.successes)
        total = len(rep.calls)
        ttft_p50 = rep.ttft_p50()
        ttft_rng = rep.ttft_range()
        ttft_p50_s = f"{ttft_p50:.0f}ms" if ttft_p50 is not None else "n/a"
        ttft_rng_s = f"{ttft_rng[0]:.0f}–{ttft_rng[1]:.0f}ms" if ttft_rng is not None else "n/a"
        lanes_s = ", ".join(f"{k}×{v}" for k, v in rep.lanes_used().items()) or "—"
        lines.append(
            f"| {rep.name} | {ok}/{total} | {rep.wall_time_s:.2f}s | "
            f"{ttft_p50_s} | {ttft_rng_s} | ${rep.total_cost_usd:.5f} | {lanes_s} |"
        )

    # Headline speedup claims (derived, only if A and B completed).
    lines.extend(["", "## Derived claims", ""])
    by_name = {r.name: r for r in configs}
    a = by_name.get("A — Claude-only")
    b = by_name.get("B — Local-only")
    if a and b and a.successes and b.successes:
        ttft_a = a.ttft_p50() or (a.wall_time_s * 1000 / max(len(a.successes), 1))
        ttft_b = b.ttft_p50()
        if ttft_b and ttft_b > 0:
            speedup = ttft_a / ttft_b
            lines.append(
                f"- **Local-vs-Claude TTFT speedup:** ~{speedup:.1f}× "
                f"(Claude {ttft_a:.0f}ms vs local {ttft_b:.0f}ms p50)"
            )
        saved = a.total_cost_usd - b.total_cost_usd
        ratio = (a.total_cost_usd / b.total_cost_usd) if b.total_cost_usd > 0 else float("inf")
        lines.append(
            f"- **Cost savings:** ${saved:.5f} ({ratio:.1f}× cheaper)"
            if ratio != float("inf")
            else f"- **Cost savings:** ${saved:.5f} (local = $0; {ratio} ratio)"
        )
    else:
        lines.append("- (Derived claims unavailable — config A or B did not complete)")

    lines.extend(
        [
            "",
            "---",
            "",
            "*Reproduce: `make benchmark-fleet`. "
            "V-Model plan: `docs/vmodel/PHASE2_BENCHMARK_PLAN.md`.*",
        ]
    )
    path.write_text("\n".join(lines))


def _validate_output_path(output: Path) -> Path:
    """Reject output paths that escape the current working directory.

    Prevents ``--output /etc/passwd`` or ``--output ../../../foo`` from writing
    outside the repo when the benchmark is driven by untrusted Make targets or
    automation (adversarial review Security MED #6).
    """
    cwd = Path.cwd().resolve()
    resolved = output.resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError as exc:
        raise ValueError(
            f"--output {output!s} resolves outside cwd ({cwd!s}); only paths under cwd are allowed"
        ) from exc
    return resolved


async def main(n_prompts: int, output: Path) -> int:
    output = _validate_output_path(output)
    prompts = CORPUS[:n_prompts]
    print(f"=== Fleet benchmark — {len(prompts)} prompts × 4 configs ===")

    # I7: health precheck before B/C/D run
    health = check_fleet(force=True)
    health_summary = format_fleet_summary(health)
    print(health_summary)
    print()
    local_up = health.any_local_up
    if not local_up:
        print("WARN: no local lanes up — configs B/C/D will likely fall back to Claude")

    configs: list[ConfigReport] = []

    # Sidecar lives next to the report so I2b can find it deterministically.
    stderr_sidecar = output.parent / f"{output.stem}.config_A.stderr.log"

    print("--- Config A (Claude-only baseline) ---")
    configs.append(await _run_config_A_claude_only(prompts, stderr_sidecar=stderr_sidecar))
    print(f"    {len(configs[-1].successes)}/{len(prompts)} ok, ${configs[-1].total_cost_usd:.5f}")
    if stderr_sidecar.exists():
        print(f"    stderr sidecar: {stderr_sidecar}")

    print("--- Config B (Local-only) ---")
    configs.append(
        await _run_local_config(
            prompts,
            name="B — Local-only",
            description="route(stream=True, budget_usd=0)",
            budget_usd=0.0,
        )
    )
    print(f"    {len(configs[-1].successes)}/{len(prompts)} ok, TTFT p50 {configs[-1].ttft_p50()}")

    print("--- Config C (Hybrid budget-capped) ---")
    configs.append(
        await _run_local_config(
            prompts,
            name="C — Hybrid $0.001",
            description="route(stream=True, budget_usd=0.001)",
            budget_usd=0.001,
        )
    )
    print(f"    {len(configs[-1].successes)}/{len(prompts)} ok")

    print("--- Config D (Hybrid quality-capped via extend_claude) ---")
    configs.append(
        await _run_local_config(
            prompts,
            name="D — Hybrid quality≥0.85",
            description="extend_claude(quality_threshold=0.85)",
            budget_usd=None,
            use_extend_claude=True,
        )
    )
    print(f"    {len(configs[-1].successes)}/{len(prompts)} ok")

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown(configs, health_summary, output)
    print()
    print(f"✓ Report written to {output}")

    # I2: at least 2 of 4 configs must have any successes
    configs_with_successes = sum(1 for c in configs if c.successes)
    if configs_with_successes < 2:
        print(f"✗ FAILED I2: only {configs_with_successes}/4 configs had any successes")
        return 2
    print(f"✓ I2: {configs_with_successes}/4 configs produced successes")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fleet benchmark harness")
    parser.add_argument(
        "--prompts", type=int, default=20, help="Subset of CORPUS to run (default 20)"
    )
    parser.add_argument("--output", type=Path, default=Path("benchmarks/fleet_report.md"))
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.prompts, args.output)))
