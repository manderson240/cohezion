"""Frontier oracle — route ONLY the genuinely-hardest tasks to Claude Fable 5.

Token-efficient by design: local silicon ($0) handles routine tasks; Fable fires
ONLY when (a) the task is frontier-hard AND (b) the monthly Fable budget has headroom.

Routing via extend_claude(): local fleet first, Fable only on quality-gate miss.
Non-frontier tasks go directly to the local TieredOrchestrator.

Also exports frontier_complete_sync for callers in synchronous context
(e.g. SkillRefiner._adversarial_reviewer) — direct subprocess cascade without
async machinery: Fable → Opus → agy (Google Antigravity 2.0).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# These names live in the frontier_oracle namespace so tests can patch them:
#   patch("cohezion.inference.frontier_oracle.extend_claude", ...)
#   patch("cohezion.inference.frontier_oracle.build_triune_orchestrator", ...)
from cohezion.inference.fleet import extend_claude
from cohezion.inference.triune_orchestrator import build_triune_orchestrator
from cohezion.inference.usage_log import record_usage


logger = logging.getLogger(__name__)

_FABLE_MODEL = "claude-fable-5"
_OPUS_FALLBACK = "claude-opus-4-8"

# Keywords that signal frontier-level difficulty.
# Whole-word matching only (after whitespace split + punctuation strip).
# "improve" does NOT match "prove"; "architecture" matches "architecture".
_HARD_KEYWORDS = frozenset(
    {
        # Formal methods / proofs
        "prove",
        "proof",
        "theorem",
        "formally",
        # System design
        "architecture",
        "architectural",
        "fault-tolerant",
        # Adversarial reasoning
        "adversarial",
        "critique",
        "refute",
        "invariant",
        # AI alignment / safety
        "hallucination",
        "alignment",
        "self-improve",
        # Compound engineering domain
        "compound",
    }
)

# Frontier tasks must be substantial — bare "prove it" must NOT reach Fable.
_FRONTIER_MIN_WORDS = 10


@dataclass
class FrontierDecision:
    """Routing decision returned by decide_frontier."""

    use_frontier: bool
    reason: str


def is_frontier_task(prompt: str) -> bool:
    """Return True when *prompt* requires frontier-level reasoning.

    Heuristic: ≥1 hard keyword AND ≥10 words.
    Uses whole-word matching: "improve" does NOT trigger; "prove" (standalone) does.
    Stays sparing — most compound loop tasks should stay on $0 local silicon.
    """
    words = prompt.lower().split()
    keyword_hits = sum(1 for w in words if w.rstrip(".,;:!?") in _HARD_KEYWORDS)
    return keyword_hits >= 1 and len(words) >= _FRONTIER_MIN_WORDS


def fable_spend_usd(path: str | Path | None = None) -> float:
    """Return total USD spent on claude-fable-5 from the JSONL usage log at *path*."""
    log_path = Path(path) if path else Path.home() / ".cohezion" / "usage.jsonl"
    if not log_path.exists():
        return 0.0
    total = 0.0
    try:
        with log_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("model") == _FABLE_MODEL:
                        total += float(rec.get("cost_usd", 0.0))
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
    except OSError:
        pass
    return total


def decide_frontier(
    prompt: str,
    *,
    monthly_budget_usd: float = 1.0,
    path: str | Path | None = None,
) -> FrontierDecision:
    """Decide (synchronously) whether to route *prompt* to Fable.

    Returns FrontierDecision(use_frontier=True) when the task is frontier-hard
    AND the monthly Fable budget has not been exhausted.
    """
    if not is_frontier_task(prompt):
        return FrontierDecision(
            use_frontier=False,
            reason="not a frontier task — routing to local silicon",
        )
    spent = fable_spend_usd(path)
    if spent >= monthly_budget_usd:
        return FrontierDecision(
            use_frontier=False,
            reason=f"budget exhausted: spent ${spent:.4f} >= cap ${monthly_budget_usd:.4f}",
        )
    return FrontierDecision(
        use_frontier=True,
        reason=f"frontier task; budget ok (${spent:.4f} of ${monthly_budget_usd:.4f} used)",
    )


async def frontier_complete(
    prompt: str,
    *,
    monthly_budget_usd: float = 1.0,
    path: str | Path | None = None,
) -> tuple[str, FrontierDecision]:
    """Complete *prompt* via Fable (frontier) or the local orchestrator (ordinary).

    Returns (text, decision) so callers can inspect the routing choice.

    Frontier path: extend_claude(prompt, claude_model="claude-fable-5")
    Ordinary path: build_triune_orchestrator().run(prompt)
    """
    decision = decide_frontier(prompt, monthly_budget_usd=monthly_budget_usd, path=path)

    if decision.use_frontier:
        result = await extend_claude(prompt, claude_model=_FABLE_MODEL)
        text = result.text or ""
        # Record spend fail-open — if result is a mock or cost unavailable, skip.
        try:
            cost = float(result.cost_usd or 0)
            if cost > 0:
                record_usage(
                    model=_FABLE_MODEL,
                    lane="cloud",
                    input_tokens=0,
                    output_tokens=len(text.split()),
                    cost_usd=cost,
                    local=False,
                    path=path,
                )
        except Exception:
            pass
        return text, decision

    orch = build_triune_orchestrator()
    result = await orch.run(prompt)
    return result.text or "", decision


# --------------------------------------------------------------------------- #
# frontier_complete_sync — for synchronous callers (SkillRefiner._adversarial_reviewer)
# --------------------------------------------------------------------------- #


def _call_agy_sync(prompt: str, timeout: float) -> str:
    """Call `agy -p <prompt>` synchronously and return plain-text response."""
    binary = shutil.which("agy")
    if binary is None:
        raise RuntimeError("agy CLI not found on PATH")
    result = subprocess.run(
        [binary, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"agy CLI exit {result.returncode}: {result.stderr[:400]}")
    return result.stdout.strip()


def _call_claude_sync(model_id: str, prompt: str, timeout: float) -> tuple[str, float]:
    """Call `claude -p <prompt> --model <id>` synchronously and return (text, cost)."""
    binary = shutil.which("claude")
    if binary is None:
        raise RuntimeError("claude CLI not found on PATH")
    result = subprocess.run(
        [
            binary,
            "-p",
            prompt,
            "--model",
            model_id,
            "--output-format",
            "json",
            "--no-session-persistence",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:400]}")
    try:
        data = json.loads(result.stdout)
        text = (
            data.get("result")
            or data.get("text")
            or data.get("response")
            or data.get("content")
            or ""
        )
        cost = float(data.get("total_cost_usd", 0.0))
    except json.JSONDecodeError:
        text = result.stdout.strip()
        cost = 0.0
    return text, cost


def frontier_complete_sync(
    prompt: str,
    *,
    timeout: float = 120.0,
    spend_log: str | None = None,
) -> str:
    """Synchronous frontier cascade: Fable → Opus → agy (Google Antigravity 2.0).

    Returns response text; raises RuntimeError only when ALL three models fail.
    Designed for sync callers (SkillRefiner._adversarial_reviewer).
    """
    _spend_path = Path(spend_log) if spend_log else None
    attempts = [
        ("fable", _FABLE_MODEL, lambda: _call_claude_sync(_FABLE_MODEL, prompt, timeout)),
        ("opus", _OPUS_FALLBACK, lambda: _call_claude_sync(_OPUS_FALLBACK, prompt, timeout)),
        ("agy", "agy-default", lambda: (_call_agy_sync(prompt, timeout), 0.0)),
    ]
    last_exc: Exception | None = None
    for label, model_id, fn in attempts:
        try:
            logger.debug("frontier_complete_sync: trying %s", label)
            text, cost = fn()
            if cost > 0 and _spend_path:
                try:
                    record_usage(
                        model=model_id,
                        lane="cloud",
                        input_tokens=0,
                        output_tokens=len(text.split()),
                        cost_usd=cost,
                        local=False,
                        path=_spend_path,
                    )
                except Exception:
                    pass
            if text:
                logger.debug("frontier_complete_sync: %s succeeded (len=%d)", label, len(text))
                return text
        except Exception as exc:
            logger.warning("frontier_complete_sync: %s failed: %s", label, exc)
            last_exc = exc
    raise RuntimeError(f"frontier_complete_sync: all models failed. Last: {last_exc}")
