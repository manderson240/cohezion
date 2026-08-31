---
name: local-model-capability-benchmark
description: |
  How to benchmark local models for CAPABILITY (not just throughput) on Strix Halo,
  and the three traps that produce confidently wrong rankings. Use when:
  (1) choosing between local models for a judgement task (code review, triage,
      classification), (2) a model scores 0/N or unexpectedly badly, (3) comparing
      models across NPU / iGPU / CPU, (4) a model 400s with
      "exceeds the available context size" well below its advertised window,
  (5) you are about to conclude "bigger model = better" or "this model is incapable".
  Complements `lemonade bench` (which measures throughput/latency, not correctness).
author: Claude Code
version: 1.0.0
---

# Local Model Capability Benchmarking

## Problem

Ranking local models by "vibes", by parameter count, or by recall alone produces
rankings that are confidently backwards. Three specific traps, all hit and corrected
in one session (2026-07-28).

## Trap 1 — No negative controls ⇒ inverted ranking

A review/triage benchmark with only defect cases rewards a model that cries wolf.

Measured, same 6 defect probes plus 2 clean-code controls:

| model | recall | controls | verdict |
|---|---|---|---|
| llama3.2-1b-FLM (NPU) | 3/6 (50%) | **0/2 (0%)** | flags defects in clean code |
| Qwen3-0.6B (iGPU) | 2/6 (33%) | **2/2 (100%)** | conservative but honest |

On recall alone the 1B **outranks** Qwen3-0.6B. On controls it is 0% vs 100%. Any
benchmark without clean-code cases would have picked the model that floods a reviewer
with false alarms — the failure mode review tooling explicitly optimises against
("a false alarm costs more reviewer trust than a missed minor issue").

**Rule:** always include negative controls; report precision and recall SEPARATELY.
A single accuracy number hides the trade that matters.

Diagnostic bonus: inspect the *text* of control failures. The 1B's false positives both
began with ` ```python ` — it rewrote the code instead of answering. That is an
**instruction-following** collapse, not a code-understanding one, which is a different
(and more fixable) problem than being "bad at review".

## Trap 2 — Effective context ≠ advertised context

```
effective_context = ctx_size / n_parallel        # -np in llamacpp_args
```

`Gemma-4-E4B` advertises `max_context_window: 131072` but is served at
`ctx_size 4096` with `-np 2` → **2048 usable**. A 6.3k-token prompt 400s with
`exceeds the available context size (2048 tokens)`.

Both numbers are readable BEFORE you send anything:

```bash
curl -s http://localhost:13305/api/v1/health | python3 -c "
import sys,json
for m in json.load(sys.stdin)['all_models_loaded']:
    ro = m.get('recipe_options', {})
    print(m['model_name'], 'ctx=', ro.get('ctx_size'), 'args=', ro.get('llamacpp_args'))"
```

**Corollary that unblocks cross-substrate work:** capability and context are SEPARATE
axes. A model that cannot hold a 6.3k prompt may still be excellent at the underlying
judgement. Shrink the probe (~200 tokens) and every substrate can participate. A model
being context-starved is not evidence it is incapable — measure capability per-task.

## Trap 3 — A harness bug masquerades as model incapability

`Bonsai-27B-gguf` (3.54 GB, Q1_0) scored **0/8**. That matched a plausible external
research claim: *"at Q1_0/ternary, tool output formatting collapses before you see any
capacity advantage."* Tempting, citable, and **wrong**.

The raw response showed `finish_reason='length', content=0, reasoning_content=456` —
a thinking model whose id matched no entry in `_THINKING_MODEL_MARKERS`, so
`reasoning_format="none"` was never applied. After fixing the fallback, the same model
on the same prompts scored **8/8**.

**Rule:** a 0/N score is a HARNESS HYPOTHESIS first and a model verdict second. Before
recording any negative capability finding, dump one raw response and check
`content` / `reasoning_content` / `finish_reason`. See `gemma4-thinking-mode-output`.

This trap is worse when an external source predicts the failure — confirmation makes a
harness bug feel like a validated result.

## Method that works

1. **Probes**: ~6 real defects + ≥2 clean controls, ~200 tokens each. Draw ground truth
   from defects a trusted reviewer actually found in YOUR code, not invented ones.
2. **Build chat_fn with `build_gaia_llm_tier()`**, never a raw shim.
3. **Generous `max_tokens`** (≥512, often 4096). With `reasoning_format="none"` the CoT
   lands in `content` and counts against the budget; a frugal cap truncates mid-thought
   and reads as a wrong answer. Local inference is $0 — headroom costs only latency.
4. **Run models SEQUENTIALLY.** Concurrent heavy iGPU submission is the gfx1151 MES-ring
   wedge pattern AND confounds latency. If another job is running, your timings are void.
5. **Use only resident or bounded-`ctx_size` models** (N3). Never auto-load a heavy model
   at `ctx_size=0`.

Reference implementation: `scripts/review_bench.py`.

## Verification (2026-07-28, Strix Halo, n=8 per model)

| model | size | recall | controls | mean | usable ctx |
|---|---|---|---|---|---|
| llama3.2-1b-FLM (NPU) | — | 50% | 0% | 0.8s | 2048 |
| Qwen3-0.6B | 0.36 GB | 33% | 100% | 1.4s | 4096 |
| Bonsai-8B (Q1_0) | 1.08 GB | 50% | 100% | **0.4s** | 16384 |
| **Bonsai-27B (Q1_0)** | **3.54 GB** | **100%** | **100%** | 17.7s | 8192 |
| **Gemma-4-E4B** | 5.56 GB | **100%** | **100%** | 6.8s | 2048 |
| Gemma-4-26B-A4B | 16.9 GB | 100% | **50%** | 9.3s | 16384 |

**Size is not the ordering variable.** The 16.9 GB model is beaten by both a 5.56 GB and
a 3.54 GB one. Default to the smallest model that passes the gate, not the largest that
fits.

**Caveat, always state it:** n=8. One control flip moves control_pass by 50 points. This
is a reusable harness and a strong signal, not a settled ranking. Widen the case set
before treating any ordering as decisive.

## Levers that raise capability WITHOUT touching weights

Measured on issue-grounded SWE-bench_Lite defect detection. Every gain below is
inference-time — no fine-tuning, no OOM exposure, $0 on local silicon:

| lever | effect | mechanism |
|---|---|---|
| **Task validity** (supply the issue text) | MCC 0.00 → 0.31 | the bare task was UNANSWERABLE |
| **Self-consistency k=3** | 0.31 → 0.54 | majority vote over independent samples |
| **Family scaling** (E4B → 26B-A4B) | 0.54 → 0.93 (n=27, provisional) | bigger sibling, same family |

**Exhaust these BEFORE reaching for fine-tuning.** I twice concluded "the only remaining lever
is RFT" and was wrong both times — a 3-sample vote and a sibling model recovered most of the
distance at zero training cost.

### Self-consistency MULTIPLIES existing signal; it cannot CREATE it

| model | k=1 | k=3 |
|---|---|---|
| Gemma-4-E4B (has signal) | 0.31 | **0.54** |
| gemma4-e2b NPU (response bias) | ~0.05 | **0.05** |

The NPU model answers "not buggy" to ~95% of cases (recall 7%, spec 95%). Majority voting over
a biased model just makes the bias more consistent. **Check that a tier has non-zero MCC before
spending 3x inference on ensembling it.**

### Temperature is a defect for measurement and a FEATURE for ensembling

Non-zero temperature makes single-shot benchmarks irreproducible — but it is the *enabling
mechanism* for self-consistency, since independent samples require it. Same parameter, opposite
sign, depending on whether you are measuring once or voting.

### "Coding-specialised" does NOT mean good at code review

| model | size | MCC (k=3) |
|---|---|---|
| Gemma-4-E4B (general) | 5.56 GB | **0.54** |
| Qwen3-Coder-30B-A3B (coding) | 17.3 GB | **0.03** |

Coder models are trained to GENERATE plausible code. Judging whether code is correct is a
different objective, and specialisation appears to hurt it (recall 78% / spec 24% — it calls
almost everything buggy). Delegated research specifically recommended this model class; measuring
it refuted the recommendation. **Research has been reliable on MECHANISM and consistently wrong
on MODEL RANKINGS — weight it accordingly.**

### Process trap: stopping generating hypotheses ≠ running out of them

The 0.93 configuration was found AFTER twice declaring the ceiling reached. The untested config
was the winning model's own larger sibling — already benchmarked on the private set, never
carried across to the public task. Before concluding a ceiling, enumerate what remains untested;
"I have stopped thinking of new experiments" is not evidence that none exist.

## ⚠️ THE HEADLINE FINDING: this benchmark does not transfer to real code

Everything below measures recognition of **textbook defect patterns in short curated snippets**.
That is a real capability and the rankings below are internally sound. It is NOT defect
detection in real code, and the gap is total:

| benchmark | ground truth | Gemma-4-E4B |
|---|---|---|
| private, 22 curated cases | author-chosen | **21/22 (95%)** |
| SWE-bench_Lite gold patches, n=60 | upstream maintainers | **50.0% — exactly chance** |

The n=60 breakdown is `tp=9 tn=21 fp=9 fn=21`: 30% recall / 70% specificity. That is not a weak
signal, it is a **response bias** — the model answers NO to 42 of 60 cases irrespective of
content. A biased coin produces the same shape. There is no discrimination happening.

**A benchmark can be internally rigorous — paired controls, discriminating cases, neutralization-
verified, externally calibrated — and still have near-zero external validity for the task you
actually care about.** Internal rigour buys you a trustworthy *ranking*; it does not buy you
evidence that the measured skill is the skill you need.

Before citing any capability number, state which of the two you have. They are not
interchangeable, and the curated one is dramatically more flattering.

## External calibration: local models vs frontier (same 22 cases)

"Approaching SOTA" is a COMPARATIVE claim, so it needs a reference point from outside your own
harness. Running the identical cases through frontier cloud models is the cheap way to get one.

| model | tier | recall | controls | total |
|---|---|---|---|---|
| **Bonsai-27B-gguf (3.54 GB)** | local iGPU | **100%** | **100%** | **22/22** |
| Gemma-4-E4B (5.56 GB, tuned) | local iGPU | 94% | 100% | 21/22 |
| gpt-oss:120b-cloud | frontier | 81% | 100% | 19/22 |
| glm-5.2:cloud | frontier | 56% | 100% | 15/22 |
| gemma4-it-e2b-FLM | local NPU | 56% | 67% | 13/22 |

**Read this carefully — it is weaker than it looks.** The local 3.54 GB model outscoring a 120B
frontier model does NOT mean it is a better code reviewer. It means:

1. **These cases are short, isolated, single-defect snippets.** They test recognition of textbook
   defect patterns, not review of real code with cross-file context. Frontier models are not
   optimised for this shape and were given no review-specialised prompt.
2. **The scorer is keyword-based.** A model that describes a defect in words outside the `expect`
   tuple is scored a miss. That is scorer vocabulary, not model capability.
3. **Ambiguous cases punish the wrong model.** Verified: the original `bare_except` case used
   `open(p).read()`, which ALSO leaks a file handle. gpt-oss named the resource leak -- correct! --
   and was scored a miss. One defect per case, or you are measuring agreement with the author's pick.
4. Frontier "misses" that were real: `NO DEFECT` on `shape_assumption` and `dict_missing_key`.

**Always inspect the MISSES of a strong model before believing a favourable result.** A result
that flatters your own conclusion is exactly when the harness deserves the most scrutiny.

## ⚠️ RETRACTED: the n=8 cascade below was REFUTED at n=22

**Read this before the cascade section.** The cascade described next was built on n=8 and
looked excellent (8/8 at 59% of iGPU latency). Widening to n=22 destroyed it:

| config | recall | controls | mean | n=8 verdict | n=22 verdict |
|---|---|---|---|---|---|
| Bonsai-27B alone | 100% | 100% | 17.0s | 8/8 | **22/22 — best** |
| Gemma-4-E4B alone | 94% | 100% | 6.5s | 8/8 | 21/22 |
| NPU→iGPU cascade | **62%** | **67%** | 4.3s | "8/8 at 4.0s" | **worse than either tier** |

**Root cause — a measurement design flaw, not bad luck.** "Precision" was computed ONLY over
clean-code controls (2 of them at n=8). It never asked whether a defect claimed on a DEFECTIVE
snippet was the CORRECT defect. So "NPU precision = 100%" actually meant "did not cry wolf on
two clean snippets" — not "its defect claims are right". Trusting its positives then BLOCKS
escalation precisely where it confidently names the wrong defect.

**`"reports a defect" ≠ "reports the right defect".`** Score those separately or the number is
not precision at all.

The NPU tier's control score itself fell 100% (2/2) → 67% (4/6) once controls included the
CORRECTED versions of defect snippets. It flagged `bucket = [] if bucket is None else bucket`
(the correct fix for mutable defaults) and a properly-scoped `except ValueError` — surface
pattern-matching, which paired controls expose and unpaired ones cannot.

**Lessons that generalise:**
1. n=8 is not enough to specify a routing architecture. It was enough to be confidently wrong.
2. Include PAIRED controls: for every defect case, a corrected version of the same code.
3. Before trusting a tier's positives, verify its positives are CORRECT, not merely non-spurious.

**Current recommendation:** Bonsai-27B-gguf (3.54 GB) alone for accuracy, Gemma-4-E4B for
speed. No cascade until a tier's positive-correctness is measured directly.

## The (refuted) n=8 cascade — kept as a worked example of the trap

Do not assume a cascade shape. Read it off the precision/recall split, which is usually
ASYMMETRIC — and that asymmetry is the whole design.

Measured tiers:

| tier | model | recall | precision (controls) | latency |
|---|---|---|---|---|
| NPU | gemma4-it-e2b-FLM | 50% | **100%** | 2.0s |
| iGPU | Gemma-4-E4B | 100% | 100% | 6.8s |

The NPU tier is *perfectly precise but half-blind*. So the gate is asymmetric:

- NPU says **"defect"** → **TRUST IT**. Precision is 100%; escalating spends 6.8s
  re-confirming something it does not get wrong.
- NPU says **"NO DEFECT"** → **ESCALATE**. Recall is 50%; a clean verdict is where it fails.

Result (`scripts/review_bench.py --cascade npu_model:igpu_model`):

| config | recall | controls | mean latency |
|---|---|---|---|
| NPU alone | 50% | 100% | 2.0s |
| iGPU alone | 100% | 100% | 6.8s |
| **NPU → iGPU cascade** | **100%** | **100%** | **4.0s** |

**Same 8/8 as the best single model at 59% of its latency**, with 5 of 8 cases resolved
entirely on the NPU — the substrate whose hang does not freeze the display. A symmetric
cascade (escalate everything, or trust everything) discards one side of the asymmetry
and buys nothing.

Generalisation: whenever a cheap tier has HIGH PRECISION and LOW RECALL, escalate only
its negative verdicts. If instead it has high recall and low precision, escalate only its
positives. Measure which, then gate accordingly.

## References

- `gemma4-thinking-mode-output` — the empty-content fix this depends on
- `lemonade bench --backend vulkan|cpu --scenarios coding` — throughput half; complementary
- https://lemonade-server.ai/docs/ — recipe_options / llamacpp_args reference
- harness N3 — ctx_size / RAM-floor OOM rules
