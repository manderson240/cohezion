#!/usr/bin/env -S uv run python
"""Cross-substrate code-review benchmark for small local models.

WHY THIS SHAPE. The full `ocr` review prompt is ~6.3k tokens, which excludes every resident
model except the 26B (effective context = ctx_size / -np). That made "compare models across
NPU/iGPU/CPU" look blocked. It is not blocked — it was the wrong probe. A FOCUSED defect
question needs ~200 tokens, so every substrate can answer it and the comparison becomes
possible. Capability is measured per-task, not per-tool.

SCORING. Each case is a real Python defect drawn from `ocr`'s own rule categories, plus
NEGATIVE CONTROLS containing no defect. A model that shouts "bug!" at everything scores well on
recall and fails the controls — which is the failure mode `ocr`'s rules explicitly optimise
against ("a false alarm costs more reviewer trust than a missed minor issue"). Reporting
precision separately from recall is the whole point; a single accuracy number would hide it.

Ground truth for `shape_assumption` is not invented: it is the defect `ocr` itself found in
src/cohezion/knowledge/corpus.py during this session.

Runs models SEQUENTIALLY. Concurrent heavy submission on one iGPU is the documented gfx1151
MES-ring wedge pattern, and it also confounds latency.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))


@dataclass(frozen=True)
class Case:
    name: str
    code: str
    # Any one of these substrings (lowercased) counts as having identified the defect.
    expect: tuple[str, ...] = ()
    # True when the snippet is CLEAN: reporting a defect here is a false positive.
    control: bool = False


CASES: tuple[Case, ...] = (
    Case(
        "mutable_default",
        "def add(item, bucket=[]):\n    bucket.append(item)\n    return bucket",
        ("mutable default", "default argument", "shared", "mutable"),
    ),
    Case(
        "identity_literal",
        "def is_ready(status):\n    return status is 'ready'",
        ("is ", "identity", "==", "interning", "equality"),
    ),
    Case(
        # NOTE: the file is opened with a context manager ON PURPOSE. An earlier version used
        # `open(p).read()`, which ALSO leaks a handle -- so a model that correctly named the
        # resource leak was scored a miss on a case meant to isolate the bare except.
        # One defect per case, or the score measures agreement with the author's pick.
        "bare_except",
        "def load(p):\n    try:\n        with open(p) as f:\n            return f.read()\n"
        "    except:\n        return None",
        ("bare except", "except:", "keyboardinterrupt", "broad", "systemexit"),
    ),
    Case(
        "empty_index",
        "def first_word(text):\n    return text.split()[0]",
        ("empty", "indexerror", "index error", "out of range", "no words"),
    ),
    Case(
        "float_equality",
        "def done(progress):\n    return progress == 1.0",
        ("float", "isclose", "tolerance", "exact equality", "precision"),
    ),
    Case(
        # The real defect ocr found in corpus.py this session.
        "shape_assumption",
        "def dim(vectors):\n    return vectors.shape[1]",
        ("1d", "one-dimensional", "ndim", "indexerror", "index error", "dimension"),
    ),
    Case(
        "dict_missing_key",
        "def name_of(users, uid):\n    return users[uid]['name']",
        ("keyerror", "key error", "missing key", ".get(", "not present", "missing"),
    ),
    Case(
        "zero_division",
        "def mean(xs):\n    return sum(xs) / len(xs)",
        ("zero", "empty", "division", "zerodivision"),
    ),
    Case(
        "loop_var_closure",
        "fns = []\nfor i in range(3):\n    fns.append(lambda: i)",
        ("closure", "late binding", "loop variable", "by reference", "final value", "same value"),
    ),
    Case(
        "assert_validation",
        "def handle(payload):\n    assert payload['user'], 'missing user'\n    return payload",
        ("assert", "-o", "optimi", "stripped", "disabled"),
    ),
    Case(
        "swallowed_exception",
        "def parse(s):\n    try:\n        return int(s)\n    except ValueError:\n        pass",
        ("silent", "swallow", "pass", "returns none", "no log", "discard"),
    ),
    Case(
        "class_mutable_attr",
        "class Cart:\n    items = []\n    def add(self, x):\n        self.items.append(x)",
        ("class-level", "class attribute", "shared", "across instances", "mutable"),
    ),
    Case(
        "resource_leak",
        "def read_all(p):\n    f = open(p)\n    return f.read()",
        ("close", "context manager", "with ", "leak", "not closed"),
    ),
    Case(
        "shadow_builtin",
        "def count(list):\n    return len(list)",
        ("shadow", "builtin", "built-in", "reserved", "overrides"),
    ),
    Case(
        "unreachable_after_return",
        "def f(x):\n    return x * 2\n    print('done')",
        ("unreachable", "dead code", "after return", "never execut"),
    ),
    Case(
        "string_concat_none",
        "def greet(name=None):\n    return 'hi ' + name",
        ("none", "typeerror", "type error", "concat", "null"),
    ),
    # --- negative controls: reporting a defect here is a false positive ---
    Case(
        "control_clean_sum",
        "def total(values):\n    if not values:\n        return 0\n    return sum(values)",
        control=True,
    ),
    Case(
        "control_clean_get",
        "def lookup(d, key):\n    return d.get(key, None)",
        control=True,
    ),
    Case(
        "control_clean_ctx",
        "def read_all(p):\n    with open(p) as f:\n        return f.read()",
        control=True,
    ),
    Case(
        "control_clean_default_none",
        "def add(item, bucket=None):\n    bucket = [] if bucket is None else bucket\n"
        "    bucket.append(item)\n    return bucket",
        control=True,
    ),
    Case(
        "control_clean_isclose",
        "import math\n\ndef done(progress):\n    return math.isclose(progress, 1.0)",
        control=True,
    ),
    Case(
        "control_clean_specific_except",
        "def parse(s):\n    try:\n        return int(s)\n    except ValueError:\n        return None",
        control=True,
    ),
)

PROMPT = (
    "You are a precise code reviewer. Favor precision over recall: only report a defect you are "
    "confident is real. If the code is correct, reply with exactly NO DEFECT.\n\n"
    "Answer in ONE short sentence.\n\n"
    "```python\n{code}\n```"
)

_NO_DEFECT_MARKERS = (
    "no defect",
    "no issue",
    "no bug",
    "looks correct",
    "is correct",
    "no problem",
)


@dataclass
class ModelResult:
    model: str
    substrate: str
    hits: int = 0
    misses: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    errors: int = 0
    latencies: list[float] = field(default_factory=list)
    detail: dict[str, str] = field(default_factory=dict)

    @property
    def recall(self) -> float:
        n = self.hits + self.misses
        return self.hits / n if n else 0.0

    @property
    def control_pass(self) -> float:
        n = self.true_negatives + self.false_positives
        return self.true_negatives / n if n else 0.0

    @property
    def mean_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0


def _said_no_defect(text: str) -> bool:
    return any(m in text.lower() for m in _NO_DEFECT_MARKERS)


def score(case: Case, reply: str) -> str:
    """Return one of hit / miss / false_positive / true_negative."""
    low = reply.lower()
    if case.control:
        return "true_negative" if _said_no_defect(low) else "false_positive"
    if any(e in low for e in case.expect):
        return "hit"
    return "miss"


def _cloud_chat(model: str):
    """Frontier reference tier via `ollama run <model>:cloud`.

    This is the ONE justified cloud escalation in this benchmark. "Approaching SOTA" is a
    COMPARATIVE claim, and no local lane can answer "where do we sit against the field" -- the
    reference point has to come from outside. Everything else here stays local and $0.

    --hidethinking is load-bearing: without it, thinking models emit their CoT to stdout and the
    scorer reads reasoning text instead of the answer.
    """

    def chat(prompt: str) -> str:
        proc = subprocess.run(
            ["ollama", "run", model, "--hidethinking"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        # Strip the ANSI spinner ollama emits even when stdout is redirected.
        return re.sub(
            r"\x1b\[[0-9;?]*[a-zA-Z]|\[\?25[lh]|\[\?2026[lh]|\[[0-9]*G|\[K", "", proc.stdout
        )

    return chat


def run_model(model: str, substrate: str, max_tokens: int) -> ModelResult:
    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    res = ModelResult(model=model, substrate=substrate)
    if substrate == "cloud":
        chat = _cloud_chat(model)
    else:
        # build_gaia_llm_tier (NOT a hand-rolled shim) applies reasoning_format="none" for
        # thinking models; without it they stream everything to reasoning_content and content
        # comes back "".
        chat = build_gaia_llm_tier(model, max_tokens=max_tokens).agent.prompt

    for case in CASES:
        start = time.monotonic()
        try:
            reply = chat(PROMPT.format(code=case.code)) or ""
        except Exception as exc:
            res.errors += 1
            res.detail[case.name] = f"ERROR {exc}"
            continue
        finally:
            res.latencies.append(time.monotonic() - start)

        verdict = score(case, reply)
        if verdict == "hit":
            res.hits += 1
        elif verdict == "miss":
            res.misses += 1
        elif verdict == "false_positive":
            res.false_positives += 1
        else:
            res.true_negatives += 1
        res.detail[case.name] = f"{verdict}: {reply.strip()[:110]}"
    return res


def run_cascade(npu_model: str, igpu_model: str, max_tokens: int) -> ModelResult:
    """Two-tier ASYMMETRIC cascade, specified by measurement rather than assumed.

    Measured on this benchmark (n=8): the NPU tier (gemma4-it-e2b-FLM) has 100% precision
    (2/2 controls) but only 50% recall, at 2.0s. The iGPU tier (Gemma-4-E4B) is 100%/100% at
    6.8s. Those two numbers dictate the gate, and the asymmetry is the whole point:

      - NPU says "defect"    -> TRUST IT. Its precision is perfect, so escalating would spend
                                6.8s to re-confirm something it does not get wrong.
      - NPU says "NO DEFECT" -> ESCALATE. Its recall is only 50%, so a clean verdict is
                                roughly a coin flip and is exactly where it fails.

    A symmetric cascade (escalate everything, or trust everything) throws away one side of that
    asymmetry. This is quarter-on-a-string: the cheap freeze-safe tier answers what it is
    demonstrably good at, and the expensive tier is spent only on its blind spot.
    """
    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    res = ModelResult(model=f"cascade({npu_model}->{igpu_model})", substrate="npu+igpu")
    npu = build_gaia_llm_tier(npu_model, max_tokens=max_tokens).agent.prompt
    igpu = build_gaia_llm_tier(igpu_model, max_tokens=max_tokens).agent.prompt
    escalations = 0

    for case in CASES:
        start = time.monotonic()
        try:
            reply = npu(PROMPT.format(code=case.code)) or ""
            # Escalate ONLY on a clean verdict -- the tier's measured blind spot.
            if _said_no_defect(reply):
                escalations += 1
                reply = igpu(PROMPT.format(code=case.code)) or ""
        except Exception as exc:
            res.errors += 1
            res.detail[case.name] = f"ERROR {exc}"
            res.latencies.append(time.monotonic() - start)
            continue
        res.latencies.append(time.monotonic() - start)

        verdict = score(case, reply)
        if verdict == "hit":
            res.hits += 1
        elif verdict == "miss":
            res.misses += 1
        elif verdict == "false_positive":
            res.false_positives += 1
        else:
            res.true_negatives += 1
        res.detail[case.name] = f"{verdict}: {reply.strip()[:100]}"

    res.detail["_escalations"] = f"{escalations}/{len(CASES)} cases escalated to iGPU"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models",
        default="llama3.2-1b-FLM:npu,Qwen3-0.6B-GGUF:igpu,Gemma-4-E4B-it-GGUF:igpu",
        help="comma-separated model:substrate pairs (RESIDENT models only)",
    )
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--json-out", default="")
    ap.add_argument("--cascade", default="", help="npu_model:igpu_model — run the two-tier gate")
    args = ap.parse_args()

    results: list[ModelResult] = []

    if args.cascade:
        npu_m, _, igpu_m = args.cascade.partition(":")
        print(f"\n### CASCADE {npu_m} -> {igpu_m}", flush=True)
        r = run_cascade(npu_m.strip(), igpu_m.strip(), args.max_tokens)
        results.append(r)
        print(
            f"  recall {r.hits}/{r.hits + r.misses} ({r.recall:.0%})  "
            f"controls {r.true_negatives}/{r.true_negatives + r.false_positives} "
            f"({r.control_pass:.0%})  errors {r.errors}  mean {r.mean_latency:.1f}s",
            flush=True,
        )
        for name, d in r.detail.items():
            print(f"    {name:20s} {d}", flush=True)
        return 0

    for spec in args.models.split(","):
        # rpartition, NOT partition: cloud model ids contain colons
        # ("gpt-oss:120b-cloud:cloud" -> model "gpt-oss:120b-cloud", substrate "cloud").
        model, _, substrate = spec.rpartition(":")
        if not model:  # no colon at all -> the whole spec is the model
            model, substrate = spec, ""
        print(f"\n### {model} [{substrate or '?'}]", flush=True)
        r = run_model(model.strip(), substrate.strip() or "?", args.max_tokens)
        results.append(r)
        print(
            f"  recall {r.hits}/{r.hits + r.misses} ({r.recall:.0%})  "
            f"controls {r.true_negatives}/{r.true_negatives + r.false_positives} "
            f"({r.control_pass:.0%})  errors {r.errors}  mean {r.mean_latency:.1f}s",
            flush=True,
        )
        for name, d in r.detail.items():
            print(f"    {name:20s} {d}", flush=True)

    print(f"\n{'model':32s} {'sub':6s} {'recall':>8s} {'ctrl':>7s} {'mean_s':>8s} {'err':>4s}")
    for r in results:
        print(
            f"{r.model:32s} {r.substrate:6s} {r.recall:>7.0%} {r.control_pass:>7.0%} "
            f"{r.mean_latency:>8.1f} {r.errors:>4d}"
        )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                [
                    {
                        "model": r.model,
                        "substrate": r.substrate,
                        "recall": r.recall,
                        "control_pass": r.control_pass,
                        "mean_latency_s": r.mean_latency,
                        "errors": r.errors,
                        "detail": r.detail,
                    }
                    for r in results
                ],
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
