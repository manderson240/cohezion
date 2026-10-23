#!/usr/bin/env python3
"""Falsifiable test of the README claim: "skills compound -- session N+1 builds on session N".

The mechanism under test is the production loop, not a re-implementation of it:

    CompoundExecutor.execute_task(skill_name=S)
      -> fetch_experience_guidance(S)  reads "## Learned Refinement" sections from S's PRIME file
      -> execute_fn(guidance)          puts them in the model prompt (guidance_to_prompt_text)
      -> RetrospectionEngine           gates should_refine
      -> SkillRefiner.refine()         appends a new "## Learned Refinement" + bumps ## Version

Executor, retrospection engine, refiner and refinement reader are the production objects. The
execute_fn is this harness's own (it calls the production `guidance_to_prompt_text` and posts to
one pinned model at temperature 0); the production `make_local_execute_fn` cascade is bypassed so
the model does not change between calls.

A "session" is a fresh PROCESS (fresh executor, refiner, guardrail rate limiter, caches) over a
FIXED task set; the only thing that persists between sessions is the skill's PRIME file --
exactly what the claim says carries the improvement. Three arms share the same base skill and
model (temp=0, FLM think=false):

  treatment  refinement ON  -- the real SkillRefiner mutates the PRIME file after each task, so
                               refinements accumulate task by task inside a session as well
  frozen     refinement OFF -- the PRIME file never changes (the no-intervention plateau and,
                               because every session re-measures the same prompt, the noise floor)
  placebo    refinement OFF -- AFTER each session the file gets the SAME NUMBER of new
                               "## Learned Refinement" sections the treatment arm gained that
                               session, filled with plausible but untargeted writing advice.
                               Controls for "any plausible prompt growth helps".

Scoring is a deterministic word-boundary match against expected terms; the scorer never
feeds back into the loop (the refiner sees only the executor's own health metrics, as in
production -- there is no ground-truth leakage by construction).

Outcome validity: a transport error (router refused or unreachable), an input-guardrail block
(production resource guard under CPU pressure) or an output-filter block cannot make a returned
answer wrong, so those calls are EXCLUDED from the rate rather than scored 0. A session with
fewer than MIN_VALID valid calls is UNMEASURED and excluded from the verdict.

Verdict (can return False): over MEASURED sessions, the treatment arm's pooled valid pass rate
must exceed BOTH the frozen arm's and the placebo arm's by more than the frozen arm's own
session-to-session fluctuation, with a non-negative slope. Anything else is "not supported".
This rule replaced an earlier "final session" rule after the first run's final treatment session
was entirely blocked by the resource guard; see docs/benchmarks/compound_loop/README.md.

Run (the full run calibrates first and refuses to launch arms unless the base-skill pass rate is
in the 30-70% band; `--force` overrides):

    uv run python scripts/experiments/compound_loop_evidence.py --calibrate \
        --models llama3.2-1b-FLM --max-tokens 96
    uv run python scripts/experiments/compound_loop_evidence.py --model llama3.2-1b-FLM \
        --max-tokens 96 --sessions 6 --adversarial-gate fail-open

Outputs (docs/benchmarks/compound_loop/): results.ndjson (one record per arm x session plus one
verdict record), final_skill_<arm>.md (the PRIME file each arm ended with).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.compound.executor_helpers.refinement_reader import (  # noqa: E402
    SKILLS_DIR_ENV,
    guidance_to_prompt_text,
)


ROUTER_URL = "http://127.0.0.1:13305/v1/chat/completions"
OUT_DIR = REPO_ROOT / "docs" / "benchmarks" / "compound_loop"
SKILL_NAME = "COMPOUND_EVIDENCE"
SCHEMA_VERSION = 2
ARMS = ("treatment", "frozen", "placebo")
GATE_MODES = ("fail-open", "flm")
CALIBRATION_BAND = (0.30, 0.70)
RESULT_SENTINEL = "RESULT_JSON:"
OUTPUT_FILTER_MARKER = "[Output blocked by content filter]"
STUB_ENV = "COMPOUND_EVIDENCE_STUB_ROUTER"

# A session with fewer valid calls than this is UNMEASURED: on the shared box the production
# resource guard (CPU pressure) and router admission control can refuse most of a session's
# tasks, and a pass rate over 3 answers is not a measurement of the arm.
MIN_VALID = 8

VERDICT_RULE = (
    "supported iff: treatment has >=2 measured sessions (n_valid >= MIN_VALID), its slope over "
    "measured sessions is >= 0, and its pooled valid pass rate over MEASURED sessions exceeds BOTH "
    "frozen's and placebo's measured pooled rate by more than the frozen arm's own max-min "
    "fluctuation across its measured sessions"
)

# Deliberately weak pi0 (same device as scripts/experiments/evolution_scaling.py): a verbose
# policy that spends the token budget on preamble before the keyword. The compounding claim
# is that the loop refines this start.
BASE_SKILL = (
    "You are a thorough teaching assistant. For every question, first restate the question "
    "in your own words, then explain the relevant background and reasoning step by step, "
    "and only afterward give the final answer."
)

# Untargeted-but-plausible advice for the placebo arm (falsifiable-eval-harness rule 2: a
# placebo must control for plausibility, not just length).
PLACEBO_ADVICE = [
    "Use correct grammar and spelling.",
    "Write in complete, well-formed sentences.",
    "Maintain a clear and professional tone.",
    "Organize your response logically.",
    "Be polite and respectful in your wording.",
    "Avoid unnecessary repetition.",
    "Check that your answer addresses the question asked.",
    "Prefer plain language over jargon where possible.",
]


@dataclass(frozen=True)
class Task:
    id: str
    question: str
    expected: tuple[str, ...]


# Expected terms must not appear in the question text, or a model that merely restates the
# question scores a pass. ("merge" alone did: "repeatedly merge sorted sublists" -- hence the
# phrase forms for mergesort.)
TASKS: tuple[Task, ...] = (
    Task("lifo", "What data structure uses last-in-first-out (LIFO) ordering?", ("stack",)),
    Task("http404", "What HTTP status code means 'Not Found'?", ("404",)),
    Task("generator", "What Python keyword makes a function a generator?", ("yield",)),
    Task(
        "binsearch",
        "What is the worst-case time complexity of binary search? Use big-O notation.",
        ("log",),
    ),
    Task("s3", "Which AWS service provides object storage?", ("s3",)),
    Task("tls", "What cryptographic protocol does HTTPS use for encryption?", ("tls",)),
    Task(
        "mergesort",
        "What sorting algorithm repeatedly merges sorted sublists?",
        ("merge sort", "mergesort", "merge-sort"),
    ),
    Task("distinct", "What SQL keyword removes duplicate rows from a result set?", ("distinct",)),
    Task(
        "gitbranch",
        "What git command creates a new branch and switches to it in one step?",
        ("checkout", "switch"),
    ),
    Task("pgport", "What is the default port for PostgreSQL?", ("5432",)),
    Task("len", "What Python built-in function returns the number of items in a list?", ("len",)),
    Task(
        "put",
        "What HTTP method is idempotent and used to replace a resource entirely?",
        ("put",),
    ),
    Task(
        "bfs",
        "What data structure does a breadth-first search use to track the frontier?",
        ("queue",),
    ),
    Task(
        "ports",
        "What Linux command lists open network ports and listening sockets?",
        ("ss", "netstat"),
    ),
    Task("raft", "What consensus algorithm does etcd use?", ("raft",)),
    Task("dns53", "What is the default port for DNS?", ("53",)),
)


def score_answer(text: str, expected: tuple[str, ...]) -> float:
    """1.0 if any expected term appears as a whole token (case-insensitive), else 0.0.

    Word-boundary match, not substring: '404' must not match '4040', 'ss' must not match 'class'.
    """
    low = text.lower()
    for term in expected:
        if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", low):
            return 1.0
    return 0.0


def log(msg: str) -> None:
    """Progress goes to stderr so a worker's stdout carries only its JSON record."""
    print(msg, file=sys.stderr, flush=True)


# ─────────────────────────────── router client ───────────────────────────────


@dataclass
class ChatResult:
    content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    error: str | None = None
    attempts: int = 0


def chat(model: str, system: str, user: str, max_tokens: int, timeout_s: float) -> ChatResult:
    """One temp=0 call. Retries transport failures (the shared NPU swaps models under us)."""
    if os.environ.get(STUB_ENV):
        # Offline plumbing check (no fleet): canned text that echoes how many refinement
        # sections reached the prompt. Never used for a scored run.
        n = system.count("## Learned Refinement")
        return ChatResult(
            content=f"stub: stack 404 yield (refinements_in_prompt={n})",
            prompt_tokens=len(system) // 4,
            completion_tokens=12,
            latency_s=0.0,
        )
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
            # FLM: the think flag STICKS on the loaded model -- send it on every request.
            "think": False,
            "stream": False,
        }
    ).encode()
    res = ChatResult()
    backoff = (5, 15, 30)
    for attempt in range(1, len(backoff) + 2):
        res.attempts = attempt
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(
                ROUTER_URL, data=payload, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - fixed http URL
                data = json.loads(resp.read())
            res.latency_s = round(time.monotonic() - t0, 3)
            msg = data["choices"][0]["message"]
            res.content = msg.get("content") or msg.get("reasoning_content") or ""
            usage = data.get("usage") or {}
            res.prompt_tokens = int(usage.get("prompt_tokens") or 0)
            res.completion_tokens = int(usage.get("completion_tokens") or 0)
            res.error = None
            return res
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode(errors="replace")
            res.error = f"HTTP {e.code}: {body}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
            res.error = f"{type(e).__name__}: {e}"
        res.latency_s = round(time.monotonic() - t0, 3)
        if attempt <= len(backoff):
            log(f"    [retry {attempt}] {res.error[:100]}")
            time.sleep(backoff[attempt - 1])
    return res


def warmup(model: str, max_wait_s: float = 240.0) -> float:
    """Probe until the model actually serves (load 'success' != serving on FLM). Returns secs."""
    t0 = time.monotonic()
    r = ChatResult(error="not attempted")
    while time.monotonic() - t0 < max_wait_s:
        r = chat(model, "Reply with one word.", "Say: yes", max_tokens=4, timeout_s=90)
        if r.error is None and r.content.strip():
            return round(time.monotonic() - t0, 1)
        time.sleep(8)
    raise RuntimeError(f"{model} never served within {max_wait_s}s: {r.error}")


# ───────────────────────────── skill file plumbing ─────────────────────────────

_REFINEMENT_RE = re.compile(r"^## Learned Refinement \(", re.MULTILINE)
_VERSION_RE = re.compile(r"^## Version: (\d+\.\d+\.\d+)", re.MULTILINE)


def prime_path(skills_dir: Path) -> Path:
    return skills_dir / f"{SKILL_NAME}_PRIME.md"


def write_base_prime(skills_dir: Path) -> Path:
    skills_dir.mkdir(parents=True, exist_ok=True)
    prime = prime_path(skills_dir)
    prime.write_text(
        f"# SKILL: {SKILL_NAME}_PRIME\n\n"
        "## INSTRUCTION\n\n"
        f"{BASE_SKILL}\n\n"
        "## Version: 1.0.0\n\n"
        "## Keywords: benchmark, compound-loop, evidence\n",
        encoding="utf-8",
    )
    return prime


def refinement_count(prime: Path) -> int:
    return len(_REFINEMENT_RE.findall(prime.read_text(encoding="utf-8")))


def prime_version(prime: Path) -> str:
    m = _VERSION_RE.search(prime.read_text(encoding="utf-8"))
    return m.group(1) if m else "unknown"


def append_placebo_sections(prime: Path, n: int, rng: random.Random) -> None:
    """Mirror SkillRefiner._append_refinement's layout with untargeted advice (placebo arm).

    Section COUNT is matched to the treatment arm; token length is not (treatment sections run
    about 15% longer because their recommendation strings are longer).
    """
    for _ in range(n):
        content = prime.read_text(encoding="utf-8")
        version = prime_version(prime)
        parts = version.split(".")
        new_version = ".".join([*parts[:2], str(int(parts[2]) + 1)])
        insight, rec = rng.sample(PLACEBO_ADVICE, 2)
        section = (
            f"\n## Learned Refinement ({datetime.now().isoformat()})\n\n"
            "**From**: Generate operation\n\n"
            f"**Insight**: {insight}\n\n"
            f"**Metrics**: Quality: {rng.randint(60, 99)}.00%, Tokens: 0, "
            f"Duration: {rng.uniform(0.5, 3.0):.2f}s\n\n"
            f"**Confidence**: {rng.randint(50, 95)}.0%\n\n"
            f"**Recommendation**: {rec}\n\n"
        )
        anchor = f"## Version: {version}"
        idx = content.find(anchor)
        content = (
            content[:idx]
            + section
            + f"\n## Version: {new_version}\n"
            + content[idx + len(anchor) + 1 :]
        )
        prime.write_text(content, encoding="utf-8")


# ───────────────────────────────── one session ─────────────────────────────────


def _mock_mcp_client() -> MagicMock:
    """Same shape as scripts/drivers/compound_cycle.py: vault calls are mocked, the loop is real."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_search.return_value = []
    client.vault_write.return_value = "success"
    client.vault_read.return_value = '{"status": "started"}'
    client.vault_log_experiment.return_value = "experiments/benchmark.md"
    client.vault_log_decision.return_value = "decisions/benchmark.md"
    client.vault_extract_pattern.return_value = "patterns/benchmark.md"
    client.vault_edit.return_value = "success"
    return client


@dataclass
class SessionRecord:
    arm: str
    session: int
    n_execute_fn_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_s: float = 0.0
    refinements_before: int = 0
    refinements_after: int = 0
    refinements_in_prompt_max: int = 0
    refine_calls: int = 0
    refine_written: int = 0
    blocked: dict[str, int] = field(default_factory=dict)
    retrospection_insights: int = 0
    prime_version: str = "1.0.0"
    worker_failed: bool = False
    tasks: list[dict[str, Any]] = field(default_factory=list)


def task_is_valid(t: dict[str, Any]) -> bool:
    """A call whose answer never came back from the model is not a measurement of the arm."""
    return not (t.get("guardrail_blocked") or t.get("transport_error") or t.get("output_filtered"))


def recount(tasks: list[dict[str, Any]], n_tasks: int, excluded: tuple[str, ...]) -> dict:
    """Per-session counts derived from the per-task records under the CURRENT validity rules.

    Single source of truth for live runs and for --finalize-from, so a rule change re-derives
    every session the same way and the test can recompute it.
    """
    scored = [t for t in tasks if t["id"] not in excluded]
    n_scored = n_tasks - len(excluded) if not tasks else len(scored)
    valid = [t for t in scored if task_is_valid(t)]
    n_pass = sum(int(bool(t["pass"])) for t in valid)
    n_valid = len(valid)
    return {
        "n_tasks": n_tasks,
        "n_tasks_scored": n_scored,
        "excluded_task_ids": list(excluded),
        "n_pass": n_pass,
        "n_transport_error": sum(1 for t in scored if t.get("transport_error")),
        "n_guardrail_blocked": sum(1 for t in scored if t.get("guardrail_blocked")),
        "n_output_filtered": sum(1 for t in scored if t.get("output_filtered")),
        "n_valid": n_valid,
        "pass_rate": round(n_pass / n_scored, 4) if n_scored else 0.0,
        "pass_rate_valid": round(n_pass / n_valid, 4) if n_valid else None,
    }


def run_session(
    arm: str,
    session: int,
    skills_dir: Path,
    model: str,
    max_tokens: int,
    timeout_s: float,
    gate_mode: str,
) -> SessionRecord:
    os.environ[SKILLS_DIR_ENV] = str(skills_dir)
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.core.compound.retrospection import RetrospectionEngine

    prime = prime_path(skills_dir)
    rec = SessionRecord(arm=arm, session=session, refinements_before=refinement_count(prime))
    mcp = _mock_mcp_client()
    refiner = None
    if arm == "treatment":
        # Same construction as the reference driver (scripts/drivers/compound_cycle.py):
        # refine_interval=1 and no golden-fixture regression gate. The factory's regression
        # gate bootstraps fixtures through a 180s-timeout GGUF call per refine, which is both
        # outside this box's FLM-only policy and too slow for a 3-arm run.
        refiner = SkillRefiner(mcp)
        # The 3-persona adversarial gate defaults to Bonsai-8B (GGUF) and, when that lane is
        # unavailable, ESCALATES to a metered frontier cascade. Neither may happen here.
        #   fail-open: the gate's documented offline path (empty reply == APPROVE) -- the most
        #              favourable condition for the claim: every refinement is promoted.
        #   flm:       the gate is live on the same $0 FLM model as the task.
        if gate_mode == "flm":
            refiner._adversarial_chat_fn = lambda prompt: (
                chat(
                    model, "Follow the instructions in the message exactly.", prompt, 32, timeout_s
                ).content
            )
        else:
            refiner._adversarial_chat_fn = lambda _prompt: ""
        # Instrument the real refiner: count attempts, writes, and which gate blocked.
        # (refine_calls is 17 per 16-task session: one per task plus the MGPO batch refine the
        # executor fires on its 10th execution.)
        _refine, _blocked = refiner.refine, refiner._record_blocked_promotion

        def counted_refine(*a: Any, **kw: Any) -> str | None:
            rec.refine_calls += 1
            out = _refine(*a, **kw)
            if out:
                rec.refine_written += 1
            return out

        def counted_blocked(skill: str, signal: Any, reason: str) -> dict:
            rec.blocked[reason] = rec.blocked.get(reason, 0) + 1
            return _blocked(skill, signal, reason)

        refiner.refine = counted_refine  # type: ignore[method-assign]
        refiner._record_blocked_promotion = counted_blocked  # type: ignore[method-assign]

    executor = CompoundExecutor(
        mcp,
        retrospection_engine=RetrospectionEngine(),
        skill_refiner=refiner,
        enable_skill_refinement=(arm == "treatment"),
    )
    # Every task must be a live model call: a template/semantic-cache hit would return a prior
    # session's answer and make all three arms converge by construction.
    executor._try_template_match = lambda *_a, **_k: None  # type: ignore[method-assign]

    t_session = time.monotonic()
    for task in TASKS:
        call: dict[str, Any] = {}

        def execute_fn(
            guidance: Any, _task: Task = task, _call: dict[str, Any] = call
        ) -> tuple[str, dict]:
            rec.n_execute_fn_calls += 1
            text = guidance_to_prompt_text(guidance)  # production flattening of the guidance dict
            n_ref = (
                len(guidance.get("learned_refinements") or []) if isinstance(guidance, dict) else 0
            )
            rec.refinements_in_prompt_max = max(rec.refinements_in_prompt_max, n_ref)
            system = BASE_SKILL + (f"\n\n{text}" if text else "")
            r = chat(model, system, _task.question, max_tokens, timeout_s)
            _call.update(
                {
                    "transport_error": r.error,
                    "latency_s": r.latency_s,
                    "attempts": r.attempts,
                    "refinements_in_prompt": n_ref,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                }
            )
            rec.prompt_tokens += r.prompt_tokens
            rec.completion_tokens += r.completion_tokens
            return r.content, {"model": model, "tier_used": "npu", "transport_error": r.error}

        result = executor.execute_task(
            task_description=task.question,
            skill_name=SKILL_NAME,
            operation_type="generate",
            execute_fn=execute_fn,
        )
        output = result.output or ""
        guard_blocked = bool(result.metrics.get("blocked_by_guardrails"))
        output_filtered = output.strip() == OUTPUT_FILTER_MARKER
        entry = {
            "id": task.id,
            "success": bool(result.success),
            "guardrail_blocked": guard_blocked,
            "output_filtered": output_filtered,
            "anomaly_score": result.metrics.get("anomaly_score"),
            "output": output,  # full text, so every pass/fail can be re-derived later
            **call,
        }
        entry["pass"] = bool(score_answer(output, task.expected)) if task_is_valid(entry) else False
        rec.retrospection_insights += int(result.metrics.get("retrospection_insights") is not None)
        rec.tasks.append(entry)
        mark = "+" if entry["pass"] else ("!" if not task_is_valid(entry) else "-")
        log(f"    {mark} {task.id:10} {output[:70]!r}")

    rec.wall_s = round(time.monotonic() - t_session, 1)
    rec.refinements_after = refinement_count(prime)
    rec.prime_version = prime_version(prime)
    return rec


def session_json(
    run_id: str,
    model: str,
    max_tokens: int,
    gate_mode: str,
    r: SessionRecord,
    excluded: tuple[str, ...] = (),
) -> dict[str, Any]:
    counts = recount(r.tasks, len(TASKS), excluded)
    if r.worker_failed:
        counts.update(n_pass=0, n_valid=0, pass_rate=0.0, pass_rate_valid=None)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "session",
        "run_id": run_id,
        "ts": datetime.now(UTC).isoformat(),
        "model": model,
        "max_tokens": max_tokens,
        "adversarial_gate": gate_mode,
        "arm": r.arm,
        "session": r.session,
        "worker_failed": r.worker_failed,
        **counts,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "wall_s": r.wall_s,
        "n_execute_fn_calls": r.n_execute_fn_calls,
        "retrospection_insights": r.retrospection_insights,
        "refinements_before": r.refinements_before,
        "refinements_after": r.refinements_after,
        "refinements_added": r.refinements_after - r.refinements_before,
        "refinements_in_prompt_max": r.refinements_in_prompt_max,
        "refine_calls": r.refine_calls,
        "refine_written": r.refine_written,
        "blocked": r.blocked,
        "prime_version": r.prime_version,
        "tasks": r.tasks,
    }


def worker_main(args: argparse.Namespace) -> int:
    """One session in one process; the JSON record is the last stdout line."""
    logging.basicConfig(level=logging.ERROR if args.quiet else logging.WARNING)
    rec = run_session(
        args.worker_arm,
        args.worker_session,
        Path(args.worker_skills_dir),
        args.model,
        args.max_tokens,
        args.timeout,
        args.adversarial_gate,
    )
    row = session_json(args.run_id, args.model, args.max_tokens, args.adversarial_gate, rec)
    print(RESULT_SENTINEL + json.dumps(row), flush=True)
    return 0


def spawn_session(
    arm: str, session: int, skills_dir: Path, args: argparse.Namespace, run_id: str
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-arm",
        arm,
        "--worker-session",
        str(session),
        "--worker-skills-dir",
        str(skills_dir),
        "--run-id",
        run_id,
        "--model",
        args.model,
        "--max-tokens",
        str(args.max_tokens),
        "--timeout",
        str(args.timeout),
        "--adversarial-gate",
        args.adversarial_gate,
    ]
    if args.quiet:
        cmd.append("--quiet")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=False)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith(RESULT_SENTINEL)]
    if proc.returncode != 0 or not lines:
        # A killed worker (observed: SIGKILL on the shared box, rc=-9) is an INSTRUMENT
        # failure, recorded as an UNMEASURED session (n_valid=0) so the run continues and the
        # verdict rule excludes it, instead of aborting hours of measurements.
        log(
            f"!! session worker {arm}/{session} failed (rc={proc.returncode}); recorded as unmeasured"
        )
        prime = prime_path(skills_dir)
        rec = SessionRecord(arm, session, worker_failed=True)
        rec.refinements_before = rec.refinements_after = refinement_count(prime)
        rec.prime_version = prime_version(prime)
        row = session_json(run_id, args.model, args.max_tokens, args.adversarial_gate, rec)
        row["worker_returncode"] = proc.returncode
        return row
    return json.loads(lines[-1][len(RESULT_SENTINEL) :])


# ──────────────────────────────── orchestration ────────────────────────────────


def _slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xbar = (n - 1) / 2.0
    ybar = sum(values) / n
    num = sum((i - xbar) * (values[i] - ybar) for i in range(n))
    den = sum((i - xbar) ** 2 for i in range(n))
    return num / den if den else 0.0


def _pooled(rows: list[dict[str, Any]]) -> float | None:
    valid = sum(r["n_valid"] for r in rows)
    return round(sum(r["n_pass"] for r in rows) / valid, 4) if valid else None


def compute_verdict(
    rows: list[dict[str, Any]], *, sessions_planned: int, run_id: str
) -> dict[str, Any]:
    """Pure verdict over session records. Used by run() and --finalize-from; mirrored by the test.

    Three poolings are recorded so a reader can see what the exclusions do:
      pooled_valid_measured  -- the verdict input: valid calls from MEASURED sessions only
      pooled_valid_all       -- valid calls from every session, measured or not
      pooled_raw             -- n_pass / n_tasks_scored over every session (every refused call
                                counted as a failure; the number the first draft of the rule used)
    """
    sessions = sorted({r["session"] for r in rows})
    by = {(r["arm"], r["session"]): r for r in rows}
    curves: dict[str, list[float | None]] = {}
    curves_valid: dict[str, list[float | None]] = {}
    measured: dict[str, list[int]] = {}
    pooled_measured: dict[str, float | None] = {}
    pooled_all: dict[str, float | None] = {}
    pooled_raw: dict[str, float | None] = {}
    for a in ARMS:
        arm_rows = [by[(a, s)] for s in sessions if (a, s) in by]
        live = [r for r in arm_rows if not r.get("worker_failed")]
        meas = [r for r in live if r["n_valid"] >= MIN_VALID]
        measured[a] = [r["session"] for r in meas]
        curves[a] = [by[(a, s)]["pass_rate"] if (a, s) in by else None for s in sessions]
        curves_valid[a] = [
            round(by[(a, s)]["n_pass"] / by[(a, s)]["n_valid"], 4)
            if (a, s) in by and by[(a, s)]["session"] in measured[a]
            else None
            for s in sessions
        ]
        pooled_measured[a] = _pooled(meas)
        pooled_all[a] = _pooled(live)
        scored = sum(r["n_tasks_scored"] for r in live)
        pooled_raw[a] = round(sum(r["n_pass"] for r in live) / scored, 4) if scored else None
    t_meas = [v for v in curves_valid["treatment"] if v is not None]
    f_meas = [v for v in curves_valid["frozen"] if v is not None]
    noise = round(max(f_meas) - min(f_meas), 4) if len(f_meas) >= 2 else 0.0
    slope = round(_slope(t_meas), 5)
    pt, pf, pp = (pooled_measured[a] for a in ARMS)
    supported = (
        len(t_meas) >= 2
        and pt is not None
        and pf is not None
        and pp is not None
        and slope >= 0
        and pt - pf > noise
        and pt - pp > noise
    )
    treatment_rows = [by[("treatment", s)] for s in sessions if ("treatment", s) in by]
    first = rows[0]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "verdict",
        "run_id": run_id,
        "ts": datetime.now(UTC).isoformat(),
        "model": first["model"],
        "max_tokens": first["max_tokens"],
        "adversarial_gate": first["adversarial_gate"],
        "sessions": len(sessions),
        "sessions_planned": sessions_planned,
        "worker_failures": sum(1 for r in rows if r.get("worker_failed")),
        "n_tasks": first["n_tasks"],
        "n_tasks_scored": first["n_tasks_scored"],
        "excluded_task_ids": first["excluded_task_ids"],
        "min_valid": MIN_VALID,
        "rule": VERDICT_RULE,
        "curves_raw": curves,
        "curves_valid": curves_valid,
        "measured_sessions": measured,
        "pooled_valid_measured": pooled_measured,
        "pooled_valid_all": pooled_all,
        "pooled_raw": pooled_raw,
        "treatment_slope": slope,
        "frozen_noise_floor": noise,
        "treatment_refinements_total": treatment_rows[-1]["refinements_after"]
        if treatment_rows
        else 0,
        "claim_supported": bool(supported),
    }


def write_results(
    out_dir: Path, rows: list[dict[str, Any]], verdict: dict[str, Any], skills: dict[str, Path]
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Newline-delimited JSON. Named .ndjson because this repo routes *.jsonl to Git LFS, which
    # would commit the evidence as a pointer nobody can read on GitHub.
    results_path = out_dir / "results.ndjson"
    with open(results_path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
        fh.write(json.dumps(verdict) + "\n")
    for arm, d in skills.items():
        shutil.copy(prime_path(d), out_dir / f"final_skill_{arm}.md")
    return results_path


def print_summary(verdict: dict[str, Any], results_path: Path) -> None:
    cv = verdict["curves_valid"]
    print("\n" + "=" * 64)
    print(
        f"{'session':>7} | {'treatment':>9} | {'frozen':>7} | {'placebo':>7}   (valid pass rate; -- = unmeasured)"
    )
    for s in range(verdict["sessions"]):
        cells = [f"{cv[a][s]:.3f}" if cv[a][s] is not None else "--" for a in ARMS]
        print(f"{s:>7} | {cells[0]:>9} | {cells[1]:>7} | {cells[2]:>7}")
    for key in ("pooled_valid_measured", "pooled_valid_all", "pooled_raw"):
        p = verdict[key]
        print(f"{key:>22}: T={p['treatment']} F={p['frozen']} P={p['placebo']}")
    print(
        f"treatment slope {verdict['treatment_slope']:+.4f}; frozen noise floor "
        f"{verdict['frozen_noise_floor']:.3f}; refinements written={verdict['treatment_refinements_total']}; "
        f"worker failures={verdict['worker_failures']}; excluded tasks={verdict['excluded_task_ids']}"
    )
    print(f"CLAIM SUPPORTED: {verdict['claim_supported']}")
    print(f"wrote {results_path}")


def finalize_from(
    partial: Path,
    workdir: Path,
    out_dir: Path,
    sessions_planned: int,
    excluded: tuple[str, ...],
) -> bool:
    """Rebuild the verdict from an interrupted run's session records (no new inference).

    Every session's counts are RE-DERIVED from its per-task records with the current validity
    rules (recount), so rows written by an earlier version of this script are scored the same
    way as fresh ones. Per-task pass flags are kept as recorded.
    """
    rows = [
        json.loads(ln)
        for ln in partial.read_text(encoding="utf-8").splitlines()
        if ln.strip() and json.loads(ln).get("record_type") == "session"
    ]
    if not rows:
        raise SystemExit(f"no session records in {partial}")
    for row in rows:
        for t in row["tasks"]:
            t.setdefault("output_filtered", (t.get("output") or "").strip() == OUTPUT_FILTER_MARKER)
            if not task_is_valid(t):
                t["pass"] = False
        row.setdefault("worker_failed", False)
        row.update(recount(row["tasks"], row["n_tasks"], excluded))
        row["schema_version"] = SCHEMA_VERSION
    verdict = compute_verdict(rows, sessions_planned=sessions_planned, run_id=rows[0]["run_id"])
    skills = {arm: workdir / f"skills_{arm}" for arm in ARMS}
    results_path = write_results(out_dir, rows, verdict, skills)
    print_summary(verdict, results_path)
    return bool(verdict["claim_supported"])


def calibrate(models: list[str], max_tokens: int, timeout_s: float) -> dict[str, float]:
    """Single-arm pass-rate probe per model with the base skill. Pick one inside the band."""
    rates: dict[str, float] = {}
    for model in models:
        log(f"\n[calibrate] {model}: warming up ...")
        try:
            w = warmup(model)
        except RuntimeError as e:
            log(f"[calibrate] {model}: NOT SERVING ({e}) -- skipped")
            continue
        log(f"[calibrate] {model}: warm in {w}s")
        hits, errs = 0, 0
        for task in TASKS:
            r = chat(model, BASE_SKILL, task.question, max_tokens, timeout_s)
            if r.error:
                errs += 1
                log(f"    ! {task.id:10} {r.error[:80]}")
                continue
            s = score_answer(r.content, task.expected)
            hits += int(s)
            log(f"    {'+' if s else '-'} {task.id:10} {r.content[:70]!r}")
        valid = len(TASKS) - errs
        rate = hits / valid if valid else float("nan")
        rates[model] = rate
        lo, hi = CALIBRATION_BAND
        band = "IN BAND" if lo <= rate <= hi else "out of band"
        print(
            f"[calibrate] {model} max_tokens={max_tokens}: pass={rate:.3f} "
            f"({hits}/{valid}, {errs} transport) -> {band}"
        )
    return rates


def run(args: argparse.Namespace) -> bool:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    workdir: Path = args.workdir
    if workdir.exists():
        shutil.rmtree(workdir)
    skills = {arm: workdir / f"skills_{arm}" for arm in ARMS}
    for d in skills.values():
        write_base_prime(d)

    print(
        f"compound-loop evidence | run={run_id} model={args.model} max_tokens={args.max_tokens} "
        f"sessions={args.sessions} tasks={len(TASKS)} adversarial_gate={args.adversarial_gate}"
    )
    # Calibration gate (falsifiable-eval-harness rule 1): a saturated instrument has no headroom
    # to show an effect, and a floored one cannot produce trajectories. Refuse unless in band.
    lo, hi = CALIBRATION_BAND
    rate = calibrate([args.model], args.max_tokens, args.timeout).get(args.model)
    if rate is None or not (lo <= rate <= hi):
        msg = f"base-skill pass rate {rate} is outside the {lo:.0%}-{hi:.0%} band"
        if not args.force:
            raise SystemExit(f"{msg}; change --max-tokens or the task set, or pass --force")
        print(f"[warn] {msg}; continuing because --force", flush=True)

    placebo_rng = random.Random(20261022)
    rows: list[dict[str, Any]] = []
    # Session records stream to a partial file as they complete, so an interrupted run can be
    # finalized with --finalize-from instead of being lost.
    partial_path = out_dir / "results.partial.ndjson"
    with open(partial_path, "w", encoding="utf-8") as fh:
        for s in range(args.sessions):
            treatment_added = 0
            for arm in ARMS:
                print(f"\n== session {s} / arm {arm} ==", flush=True)
                row = spawn_session(arm, s, skills[arm], args, run_id)
                if arm == "treatment":
                    treatment_added = row["refinements_added"]
                if arm == "placebo":
                    append_placebo_sections(prime_path(skills[arm]), treatment_added, placebo_rng)
                    row["refinements_after"] = refinement_count(prime_path(skills[arm]))
                    row["refinements_added"] = row["refinements_after"] - row["refinements_before"]
                    row["prime_version"] = prime_version(prime_path(skills[arm]))
                rows.append(row)
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(
                    f"   {arm:9} pass={row['pass_rate']:.3f} valid={row['pass_rate_valid']} "
                    f"(n_valid={row['n_valid']}) transport_err={row['n_transport_error']} "
                    f"guard_blocked={row['n_guardrail_blocked']} filtered={row['n_output_filtered']} "
                    f"refinements {row['refinements_before']}->{row['refinements_after']} "
                    f"(refine calls {row['refine_calls']}, written {row['refine_written']}, "
                    f"blocked {row['blocked']}) wall={row['wall_s']}s",
                    flush=True,
                )

    verdict = compute_verdict(rows, sessions_planned=args.sessions, run_id=run_id)
    results_path = write_results(out_dir, rows, verdict, skills)
    partial_path.unlink(missing_ok=True)
    print_summary(verdict, results_path)
    return bool(verdict["claim_supported"])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--calibrate", action="store_true", help="probe pass rate per --models and exit"
    )
    ap.add_argument("--models", default="llama3.2-1b-FLM", help="comma-separated, for --calibrate")
    ap.add_argument("--model", default="llama3.2-1b-FLM")
    ap.add_argument("--sessions", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=96)
    ap.add_argument("--timeout", type=float, default=120.0, help="per-call timeout seconds")
    ap.add_argument("--adversarial-gate", choices=GATE_MODES, default="fail-open")
    ap.add_argument(
        "--force", action="store_true", help="launch arms even if calibration is out of band"
    )
    ap.add_argument(
        "--workdir",
        type=Path,
        default=Path(os.environ.get("TMPDIR", "/tmp")) / "compound_loop_evidence",
    )
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument(
        "--finalize-from",
        type=Path,
        help="rebuild results.ndjson + verdict from an interrupted run's partial NDJSON "
        "(uses --workdir for the final skill files; no inference)",
    )
    ap.add_argument(
        "--exclude-task",
        action="append",
        default=[],
        help="task id to drop from scoring when finalizing (recorded in the verdict)",
    )
    ap.add_argument("--quiet", action="store_true", help="silence cohezion INFO/WARNING logging")
    # Worker mode (internal): one session in one process.
    ap.add_argument("--worker-arm", choices=ARMS, help=argparse.SUPPRESS)
    ap.add_argument("--worker-session", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--worker-skills-dir", help=argparse.SUPPRESS)
    ap.add_argument("--run-id", default="", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker_arm is not None:
        return worker_main(args)
    logging.basicConfig(level=logging.ERROR if args.quiet else logging.WARNING)
    if args.calibrate:
        rates = calibrate(args.models.split(","), args.max_tokens, args.timeout)
        lo, hi = CALIBRATION_BAND
        in_band = [m for m, r in rates.items() if lo <= r <= hi]
        print(
            f"in-band models: "
            f"{in_band or 'NONE (instrument saturated -- change the task set, not the model)'}"
        )
        return 0 if in_band else 2
    if args.finalize_from is not None:
        ok = finalize_from(
            args.finalize_from,
            args.workdir,
            args.out_dir,
            args.sessions,
            tuple(args.exclude_task),
        )
        return 0 if ok else 1
    return 0 if run(args) else 1


if __name__ == "__main__":
    raise SystemExit(main())
