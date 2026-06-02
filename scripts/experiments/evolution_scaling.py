#!/usr/bin/env python3
"""Evolution-scaling experiment — empirical test of the A-Evolve hypothesis.

Tests "Position: Agentic Evolution is the Path to Evolving LLMs" (arXiv 2602.00359):
    P*(C_evolve, pi0) strictly increases with evolve-compute.

We operationalize evolve-compute as *cycles of skill refinement* and measure
downstream task quality per cycle on a fixed task set, on local silicon
(Granite-4.1-8B via the lemonade router :13305). Three arms isolate the effect:

  evolve  — each cycle appends a generic, ANSWER-AGNOSTIC strategy hint to the
            skill (e.g. "state the canonical term; be concise"). No answer leakage:
            the hints help because local-model failures are largely *format*
            failures (verbosity/hedging), which a refined prompt fixes.
  static  — skill frozen. With temperature=0 this is a perfectly flat baseline
            (the hypothesis's "plateau").
  placebo — each cycle appends NEUTRAL filler of similar length. Controls for the
            confound "any prompt growth helps." If evolve >> placebo, the gain is
            the strategy content, not prompt length.

Honest-result contract: "evolution wins" is falsifiable. If the evolve arm does
not rise above static/placebo, that is reported as a negative result.

Run:  uv run python scripts/experiments/evolution_scaling.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Reuse the existing compound trend tracker (compound principle: don't rebuild).
try:
    from cohezion.compound.compound_score_tracker import CompoundScoreWindow
except Exception:  # pragma: no cover - allow standalone run if import path differs
    CompoundScoreWindow = None  # type: ignore

ROUTER_URL = "http://localhost:13305/v1/chat/completions"
MODEL = "Granite-4.1-8B-GGUF"
CYCLES = 6  # cycle 0 = base skill (no additions) for all arms; 1..5 add one item/cycle
import os

MAX_TOKENS = int(os.environ.get("EVOSCALE_MAX_TOKENS", "60"))
TIMEOUT_S = 30

# Deliberately weak pi0: a verbose base policy that reproduces the documented local-model
# failure (preamble/CoT exhausts the token budget before the keyword is emitted). Evolution
# refines this unrefined start — exactly the A-Evolve setup. NOT answer leakage; the placebo
# arm (verbose base + filler) controls for prompt growth.
BASE_SKILL = (
    "You are a thorough teaching assistant. For every question, first restate the question "
    "in your own words, then explain the relevant background and reasoning step by step, "
    "and only afterward give the final answer."
)

# Answer-AGNOSTIC strategy hints (one appended per evolve cycle). None names an answer.
STRATEGY_HINTS = [
    "State the single canonical name or term directly; do not describe around it.",
    "Be concise: one short sentence, no preamble.",
    "Do not hedge or add caveats; commit to the most precise answer.",
    "Lead with the answer in the first few words.",
    "Use the exact technical term, not a paraphrase.",
]
# Placebo control = untargeted-but-plausible WRITING ADVICE (not inert filler, not
# metric-aware). Controls for "any plausible instruction helps", a stronger control
# than length alone. If evolve_llm beats this, the gain is targeted diagnosis.
PLACEBO_FILLER = [
    "Use correct grammar and spelling.",
    "Write in complete, well-formed sentences.",
    "Maintain a clear and professional tone.",
    "Organize your response logically.",
    "Be polite and respectful in your wording.",
]

# Evolver model (cheap-local tier, per the harness-tier routing policy). Same node;
# swap to llama3.2-1b-FLM (:13306) to test the "weak evolver = weak updates" claim.
EVOLVER_MODEL = "Granite-4.1-8B-GGUF"


@dataclass
class Task:
    question: str
    expected: list[str] = field(default_factory=list)


# Fixed task set — terse-answer questions where verbosity/hedging loses the keyword.
TASKS: list[Task] = [
    Task("What data structure uses last-in-first-out (LIFO) ordering?", ["stack"]),
    Task("What HTTP status code means 'Not Found'?", ["404"]),
    Task("What Python keyword makes a function a generator (lazy return)?", ["yield"]),
    Task("What is the worst-case time complexity of binary search? Use big-O.", ["log"]),
    Task("Which AWS service provides object storage?", ["s3"]),
    Task("What cryptographic protocol does HTTPS use for encryption?", ["tls"]),
    Task("What sorting algorithm repeatedly merges sorted sublists?", ["merge"]),
    Task("What SQL keyword removes duplicate rows from a result set?", ["distinct"]),
]


def score_answer(text: str, expected: list[str]) -> float:
    """Fraction of expected terms present as whole words (case-insensitive).

    Word-boundary match, not bare substring — avoids the substring trap
    (e.g. '404' inside '4040', 'stack' inside 'stackoverflow').
    """
    if not expected:
        return 0.0
    low = text.lower()
    hits = 0
    for term in expected:
        # \b works for alnum tokens like 'stack','404','tls','s3','distinct'.
        if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", low):
            hits += 1
    return hits / len(expected)


def _chat(model: str, system: str, user: str, max_tokens: int) -> str:
    """One local-fleet call (temp=0 for reproducibility). Returns content or ''."""
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
    ).encode()
    req = urllib.request.Request(
        ROUTER_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"].get("content", "") or ""
    except Exception as e:  # network/timeout/parse — log, count as empty (score 0)
        print(f"    [warn] call failed: {e}", file=sys.stderr)
        return ""


def solve(skill: str, question: str) -> str:
    return _chat(MODEL, skill, question, MAX_TOKENS)


def evolve_hint(skill: str, failures: list[tuple[str, str]]) -> str:
    """Cheap-local LLM EVOLVER: real evolution-compute spent per cycle.

    Given failed (question, wrong_answer) pairs — but NOT the expected keywords — the
    evolver infers why answers failed and writes ONE new general instruction to append
    to the skill. This is the closed-loop Diagnose→Update. Can produce a weak/vague hint
    (→ evolve curve stays flat), which is the harness paper's "weak updates" mode.
    """
    if not failures:
        return ""
    cases = "\n".join(f"- Q: {q}\n  assistant answered: {a!r}" for q, a in failures[:4])
    evolver_system = (
        "You improve an AI assistant's instructions. You are shown questions and the "
        "assistant's own answers that were judged INCORRECT. You do NOT know the correct "
        "answers. Infer why the answers likely failed and write ONE short, general "
        "instruction (max 15 words) to add to the assistant's guidance so future answers "
        "score better. Output ONLY the instruction text, no preamble, no quotes."
    )
    user = f"Current guidance:\n{skill}\n\nFailed cases:\n{cases}\n\nNew instruction:"
    out = _chat(EVOLVER_MODEL, evolver_system, user, max_tokens=40)
    if not out.strip():
        return ""
    line = out.strip().splitlines()[0].strip()
    return line.lstrip("-*0123456789. ").strip().strip('"').strip()


def skill_for(arm: str, cycle: int) -> str:
    """Build the skill artifact for an arm at a given cycle.

    cycle 0 = base skill for ALL arms (common starting point). Each subsequent
    cycle appends one item (strategy hint for evolve, filler for placebo).
    """
    lines = [BASE_SKILL]
    if arm == "evolve":
        lines += STRATEGY_HINTS[:cycle]
    elif arm == "placebo":
        lines += PLACEBO_FILLER[:cycle]
    # static: never appends
    return "\n".join(lines)


def run() -> dict:
    arms = ["evolve", "static", "placebo"]
    curves: dict[str, list[float]] = {a: [] for a in arms}
    windows = (
        {a: CompoundScoreWindow() for a in arms}  # type: ignore[misc]
        if CompoundScoreWindow is not None
        else {}
    )

    print(f"Evolution-scaling experiment | model={MODEL} | tasks={len(TASKS)} | cycles={CYCLES}")
    print(f"{'cycle':>5} | {'evolve':>7} | {'static':>7} | {'placebo':>7}")
    print("-" * 38)

    for cycle in range(CYCLES):
        row: dict[str, float] = {}
        for arm in arms:
            skill = skill_for(arm, cycle)
            scores = [score_answer(solve(skill, t.question), t.expected) for t in TASKS]
            mean_q = sum(scores) / len(scores)
            curves[arm].append(mean_q)
            row[arm] = mean_q
            if windows:
                windows[arm].record(mean_q)
        print(
            f"{cycle:>5} | {row['evolve']:>7.3f} | {row['static']:>7.3f} | {row['placebo']:>7.3f}"
        )

    # Verdict: hypothesis supported iff evolve ends strictly above its start AND
    # above both static and placebo at the final cycle, with a non-negative slope.
    def trend(arm: str) -> float:
        """Least-squares slope of the arm's quality curve (transparent, raw)."""
        c = curves[arm]
        n = len(c)
        if n < 2:
            return 0.0
        xbar = (n - 1) / 2.0
        ybar = sum(c) / n
        num = sum((i - xbar) * (c[i] - ybar) for i in range(n))
        den = sum((i - xbar) ** 2 for i in range(n))
        return num / den if den else 0.0

    evolve_gain = curves["evolve"][-1] - curves["evolve"][0]
    beats_static = curves["evolve"][-1] > curves["static"][-1]
    beats_placebo = curves["evolve"][-1] > curves["placebo"][-1]
    supported = evolve_gain > 0 and beats_static and beats_placebo and trend("evolve") >= 0

    verdict = {
        "experiment": "evolution_scaling",
        "paper": "arXiv 2602.00359 (A-Evolve evolution-scaling hypothesis)",
        "model": MODEL,
        "cycles": CYCLES,
        "n_tasks": len(TASKS),
        "curves": curves,
        "evolve_gain": round(evolve_gain, 4),
        "evolve_trend": round(trend("evolve"), 5),
        "final": {a: round(curves[a][-1], 4) for a in arms},
        "hypothesis_supported": supported,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    print("-" * 38)
    print(
        f"evolve: {curves['evolve'][0]:.3f} -> {curves['evolve'][-1]:.3f} "
        f"(gain {evolve_gain:+.3f}, trend {trend('evolve'):+.4f})"
    )
    print(
        f"final  evolve={verdict['final']['evolve']}  static={verdict['final']['static']}  placebo={verdict['final']['placebo']}"
    )
    print(f"HYPOTHESIS SUPPORTED: {supported}")
    return verdict


def run_closed_loop() -> dict:
    """v2: real evolution-compute. evolve_llm grows its skill via the LLM evolver each
    cycle (from observed failures, no answer leakage); static is frozen; placebo appends
    untargeted writing advice. Now the x-axis IS evolution steps, so this tests P*(C_evolve).
    """
    arms = ["evolve_llm", "static", "placebo"]
    skills: dict[str, str] = {a: BASE_SKILL for a in arms}
    curves: dict[str, list[float]] = {a: [] for a in arms}
    evolver_hints: list[str] = []  # transparency: what the evolver actually wrote

    print(f"Evolution-scaling v2 (closed-loop) | solver={MODEL} | evolver={EVOLVER_MODEL}")
    print(f"tasks={len(TASKS)} | cycles={CYCLES} | temp=0")
    print(f"{'cycle':>5} | {'evolve_llm':>10} | {'static':>7} | {'placebo':>7}")
    print("-" * 42)

    for cycle in range(CYCLES):
        row: dict[str, float] = {}
        cycle_failures: list[tuple[str, str]] = []
        for arm in arms:
            answers = [solve(skills[arm], t.question) for t in TASKS]
            scores = [score_answer(answers[i], TASKS[i].expected) for i in range(len(TASKS))]
            mean_q = sum(scores) / len(scores)
            curves[arm].append(mean_q)
            row[arm] = mean_q
            if arm == "evolve_llm":
                # collect this cycle's failures (q, wrong answer) for the evolver
                cycle_failures = [
                    (TASKS[i].question, answers[i]) for i in range(len(TASKS)) if scores[i] < 1.0
                ]
        print(
            f"{cycle:>5} | {row['evolve_llm']:>10.3f} | {row['static']:>7.3f} | {row['placebo']:>7.3f}"
        )

        # Evolution step (spends real evolve-compute) — applied AFTER scoring, for next cycle.
        if cycle < CYCLES - 1:
            hint = evolve_hint(skills["evolve_llm"], cycle_failures)
            if hint:
                skills["evolve_llm"] += "\n" + hint
                evolver_hints.append(f"c{cycle + 1}: {hint}")
            if cycle < len(PLACEBO_FILLER):
                skills["placebo"] += "\n" + PLACEBO_FILLER[cycle]

    def slope(arm: str) -> float:
        c = curves[arm]
        n = len(c)
        if n < 2:
            return 0.0
        xbar = (n - 1) / 2.0
        ybar = sum(c) / n
        num = sum((i - xbar) * (c[i] - ybar) for i in range(n))
        den = sum((i - xbar) ** 2 for i in range(n))
        return num / den if den else 0.0

    gain = curves["evolve_llm"][-1] - curves["evolve_llm"][0]
    beats_static = curves["evolve_llm"][-1] > curves["static"][-1]
    beats_placebo = curves["evolve_llm"][-1] > curves["placebo"][-1]
    supported = gain > 0 and beats_static and beats_placebo and slope("evolve_llm") >= 0

    print("-" * 42)
    for h in evolver_hints:
        print(f"  evolver {h}")
    print(
        f"evolve_llm: {curves['evolve_llm'][0]:.3f} -> {curves['evolve_llm'][-1]:.3f} "
        f"(gain {gain:+.3f}, slope {slope('evolve_llm'):+.4f})"
    )
    print(
        f"final evolve_llm={curves['evolve_llm'][-1]:.3f} static={curves['static'][-1]:.3f} placebo={curves['placebo'][-1]:.3f}"
    )
    print(f"HYPOTHESIS SUPPORTED (evolve-compute scaling): {supported}")

    return {
        "experiment": "evolution_scaling_v2_closedloop",
        "paper": "arXiv 2602.00359 (A-Evolve evolution-scaling hypothesis)",
        "solver": MODEL,
        "evolver": EVOLVER_MODEL,
        "cycles": CYCLES,
        "n_tasks": len(TASKS),
        "curves": curves,
        "evolver_hints": evolver_hints,
        "gain": round(gain, 4),
        "slope": round(slope("evolve_llm"), 5),
        "final": {a: round(curves[a][-1], 4) for a in arms},
        "hypothesis_supported": supported,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    proxy = "--proxy" in sys.argv
    result = run() if proxy else run_closed_loop()
    # Append to the autoresearch winners log (winner = hypothesis_supported).
    out = Path("autoresearch.jsonl")
    rec = {"winner": result["hypothesis_supported"], **result}
    with out.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"\nlogged -> {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
