#!/usr/bin/env -S uv run python
"""Defect-detection benchmark derived from SWE-bench_Lite gold patches.

WHAT THIS IS AND IS NOT. This does NOT run SWE-bench. SWE-bench is patch GENERATION evaluated
by running each repo's test suite in a per-instance container. This is a different task built
on the same data: each gold patch identifies code that was genuinely broken (the `-` lines) and
the maintainer-accepted correction (the `+` lines). That gives a PAIRED defect/control sample
whose ground truth was established by upstream maintainers, not by me.

Why it is worth having: my private benchmark has ground truth I chose and a keyword scorer, so
it cannot answer "where do these models sit against the field". This one uses external ground
truth and a BINARY YES/NO decision, which removes scorer-vocabulary bias entirely — a model
cannot lose a point for describing a real defect in words my `expect` tuple lacks.

Known limits, stated up front:
  * Single-hunk patches only, so the snippet is small and self-contained. Real review needs
    cross-file context this does not supply.
  * "Was changed by the gold patch" is not identical to "is a defect" — some hunks are
    refactors or test scaffolding that rode along with the fix. Filtered as best we can.
  * The CONTROL (post-fix code) is assumed defect-free. It is defect-free with respect to THIS
    issue; the file may contain unrelated latent bugs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

PROMPT = (
    "You are a precise code reviewer. Does the following code contain a BUG?\n"
    "Answer with exactly one word: YES or NO.\n\n"
    "```python\n{code}\n```"
)

# Context-supplied variant. The bare PROMPT above may be an UNFAIR task, not just a hard one:
# it shows a snippet with no statement of what the code is supposed to do, so `x = 1` vs
# `x = right` is undecidable without knowing the intent. An expert would also be near chance.
#
# SWE-bench ships the originating GitHub issue in `problem_statement`. Supplying it makes the
# question well-posed -- "given this reported problem, does this code still exhibit it?" -- and
# is closer to real review, where the reviewer has the issue/PR description.
#
# It does NOT leak the answer: the SAME issue text is shown for both halves of a pair, so it
# cannot be used to distinguish them. Only understanding the code can.
PROMPT_CTX = (
    "You are a precise code reviewer. A user reported this issue:\n\n"
    "---\n{issue}\n---\n\n"
    "Does the code below STILL contain the reported bug, or has it been fixed?\n"
    "Answer with exactly one word: YES (still buggy) or NO (fixed / not present).\n\n"
    "```python\n{code}\n```"
)

_YES = ("yes",)
_NO = ("no",)


def _verdict(reply: str) -> bool | None:
    """True=said YES, False=said NO, None=unparseable.

    Takes the LAST standalone yes/no token, not the first.

    A head-only scan was the original implementation and it was WRONG for exactly the models
    under test: with reasoning_format="none" a thinking model emits `<|channel>thought ...`
    first, so the head is reasoning and the answer (if any) comes last. That parser scored
    Bonsai-27B 30/30 unparseable and Gemma-4-E4B 27/30 — pure harness artifact, while the one
    non-thinking model (gpt-oss) parsed fine and thus looked far better than the locals.

    Reasoning text routinely contains both words ("this is not a no-op... so yes"), which is
    why LAST beats first: models reason, then answer.
    """
    toks = re.sub(r"[^a-z ]", " ", reply.lower()).split()
    for t in reversed(toks):
        if t in _YES:
            return True
        if t in _NO:
            return False
    return None


def build_cases(limit: int) -> list[tuple[str, str, bool, str]]:
    """Return (instance_id, code, is_defective, issue_text) from single-hunk gold patches."""
    from datasets import load_dataset

    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    cases: list[tuple[str, str, bool, str]] = []

    for ex in ds:
        patch = ex["patch"]
        # Single file, single hunk only — multi-hunk patches make "the" defect ambiguous.
        if patch.count("diff --git") != 1 or patch.count("\n@@") != 1:
            continue
        if not re.search(r"\.py\b", patch.split("\n", 1)[0]):
            continue

        body = patch.split("@@", 2)[-1]
        lines = body.split("\n")[1:]
        before, after = [], []
        for ln in lines:
            if ln.startswith("-") and not ln.startswith("---"):
                before.append(" " + ln[1:])
            elif ln.startswith("+") and not ln.startswith("+++"):
                after.append(" " + ln[1:])
            elif ln.startswith(" "):
                before.append(ln)
                after.append(ln)

        # Require a real edit on both sides: a pure addition has no "defective version" to show.
        if not before or not after:
            continue
        pre, post = "\n".join(before).strip("\n"), "\n".join(after).strip("\n")
        if not pre.strip() or not post.strip() or pre == post:
            continue
        if len(pre) > 1400 or len(post) > 1400:
            continue

        # Same issue text on BOTH halves — it cannot be used to tell them apart, only the code can.
        issue = (ex["problem_statement"] or "")[:1800]
        cases.append((ex["instance_id"], pre, True, issue))
        cases.append((ex["instance_id"] + "__fixed", post, False, issue))
        if len(cases) >= limit * 2:
            break
    return cases


def _local_chat(model: str, max_tokens: int, temperature: float | None = None):
    """temperature=None uses the model card default (TR1). Pass a value to override.

    Card defaults are tuned for GENERATION, not evaluation. Gemma-4's card specifies temp 1.0,
    which makes a benchmark measure the model PLUS a random number generator: the same model,
    task and budget produced MCC 0.31 and 0.54 on two runs. For measurement you want low
    temperature — but NOT 0.0 on Gemma-family cards, where greedy decoding is documented (TR1)
    to produce degenerate/empty output.
    """
    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    return build_gaia_llm_tier(
        model, max_tokens=max_tokens, temperature=temperature
    ).agent.prompt


def _cloud_chat(model: str):
    def chat(prompt: str) -> str:
        p = subprocess.run(
            ["ollama", "run", model, "--hidethinking"],
            input=prompt, capture_output=True, text=True, timeout=300, check=False,
        )
        return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\[\?25[lh]|\[\?2026[lh]|\[[0-9]*G|\[K", "", p.stdout)

    return chat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="Bonsai-27B-gguf:igpu")
    ap.add_argument("--limit", type=int, default=15, help="instances (x2 for paired controls)")
    # 512 was NOT enough: with reasoning_format="none" the chain-of-thought lands in `content`
    # and counts against this budget. Measured — Gemma-4-E4B produced 1727 chars of reasoning
    # on a single case and was still mid-thought at the cut, so it never emitted an answer and
    # scored a spurious 0%. Local inference is $0; the only cost of headroom is latency.
    ap.add_argument("--max-tokens", type=int, default=3072)
    ap.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="override the model-card temperature; low values make the benchmark reproducible",
    )
    ap.add_argument(
        "--self-consistency",
        type=int,
        default=1,
        help="sample k times per case and take the majority verdict (needs temperature > 0)",
    )
    ap.add_argument("--json-out", default="")
    ap.add_argument(
        "--with-context",
        action="store_true",
        help="supply the originating GitHub issue — makes the task well-posed",
    )
    args = ap.parse_args()

    cases = build_cases(args.limit)
    n_def = sum(1 for c in cases if c[2])
    print(f"cases: {len(cases)} ({n_def} defective + {len(cases) - n_def} fixed controls)\n")

    out = []
    for spec in args.models.split(","):
        model, _, substrate = spec.rpartition(":")
        if not model:
            model, substrate = spec, ""
        chat = (
            _cloud_chat(model)
            if substrate == "cloud"
            else _local_chat(model, args.max_tokens, args.temperature)
        )

        tp = tn = fp = fn = unp = 0
        lat = []
        print(f"-- {model} [{substrate or '?'}]", flush=True)
        # Print per-case. A previous run was killed by a wall-clock timeout mid-model and,
        # because results were only emitted after ALL cases finished, 50 minutes of compute
        # produced ZERO salvageable output. Partial data beats none.
        for _i, (_iid, code, defective, issue) in enumerate(cases, 1):
            t0 = time.monotonic()
            try:
                tmpl = (
                    PROMPT_CTX.format(issue=issue, code=code)
                    if args.with_context
                    else PROMPT.format(code=code)
                )
                if args.self_consistency > 1:
                    # Sample k times and take the majority verdict. Pure inference-time
                    # technique -- no weight changes, no training, $0 on local silicon. Needs
                    # a NON-zero temperature to give independent samples, which is why the
                    # card default (Gemma-4 = 1.0) is useful here rather than a liability.
                    votes = [_verdict(chat(tmpl) or "") for _ in range(args.self_consistency)]
                    yes = sum(1 for x in votes if x is True)
                    no = sum(1 for x in votes if x is False)
                    v = None if yes == no else (yes > no)
                else:
                    v = _verdict(chat(tmpl) or "")
            except Exception:
                v = None
            lat.append(time.monotonic() - t0)
            if v is None:
                unp += 1
            elif defective and v:
                tp += 1
            elif defective and not v:
                fn += 1
            elif not defective and v:
                fp += 1
            else:
                tn += 1
            print(
                f"   [{_i:2d}/{len(cases)}] {'bug ' if defective else 'fixed'} "
                f"-> {'YES' if v else ('NO' if v is False else 'UNPARSEABLE')} "
                f"({lat[-1]:.0f}s)  running: tp={tp} tn={tn} fp={fp} fn={fn} unp={unp}",
                flush=True,
            )

        rec = tp / (tp + fn) if tp + fn else 0.0
        spec_ = tn / (tn + fp) if tn + fp else 0.0
        acc = (tp + tn) / max(1, len(cases))
        print(
            f"{model:32s} [{substrate or '?'}] recall(bug)={rec:.0%} "
            f"specificity(clean)={spec_:.0%} acc={acc:.0%} unparseable={unp} "
            f"mean={sum(lat) / len(lat):.1f}s"
        )
        out.append({"model": model, "substrate": substrate, "recall": rec,
                    "specificity": spec_, "accuracy": acc, "unparseable": unp,
                    "mean_latency_s": sum(lat) / len(lat), "tp": tp, "tn": tn, "fp": fp, "fn": fn})

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
