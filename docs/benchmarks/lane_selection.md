# Local inference lane selection — measured on both axes

> **Status 2026-08-16.** The character-based cost table was retracted and REPLACED by a
> full-roster sweep measured on `usage.completion_tokens` with one model resident at a time —
> see "Corrected roster (2026-08-16)" immediately below, which supersedes every older table here.
> The retraction analysis is kept further down because it explains why the old numbers were wrong.
>
> One correction to the retraction itself: it claimed `term` and `ceiling` were "unaffected". That
> was overconfident — `Gemma-4-26B-A4B` measured term 0.67 / ceiling 0.67 in the old run and
> term 1.00 / ceiling 0.33 in the sweep. No mechanism links termination to residency, so the
> honest reading is that **n=3 does not stabilise termination for a borderline lane**, not that
> contention caused it. Two columns were carved out as trustworthy without checking their
> run-to-run stability.

## Corrected roster (2026-08-16) — 14 lanes, exclusive residency, ranked by true generation cost

`scripts/experiments/roster_sweep.py --reps 3`, one model resident at a time, unscored warmup rep
per lane, `ctx_size=16384`, `max_tokens=4000`. `GEN_TOK` is `usage.completion_tokens` (the
provider's count over every generated token, reasoning included — unstrippable). `drop` is
`reasoning_content` the adapter discarded.

| model | term | **GEN_TOK** | rawch | drop | p50 |
|---|---|---|---|---|---|
| llama3.2-3b-FLM | 1.00 | **61** | 303 | 0 | 3.3s |
| SmolLM3-3B-IQ4_XS | 1.00 | **69** | 335 | 0 | **1.5s** |
| Qwen3-Coder-30B-A3B-Instruct | 1.00 | **155** | 835 | 0 | 1.8s |
| Gemma-4-E4B-it | 1.00 | 312 | 1501 | 0 | 9.5s |
| gpt-oss-20b | 1.00 | 399 | 157 | 1693 | 5.4s |
| qwen3-4b-FLM | 1.00 | 420 | 394 | 1662 | 36.2s |
| Gemma-4-E2B-it | 1.00 | 486 | 2210 | 0 | 32.7s |
| Gemma-4-31B-it | 1.00 | 487 | 2122 | 0 | 51.2s |
| Qwen3-8B | 1.00 | 490 | 2424 | 0 | 11.9s |
| Nemotron-3-Nano-30B-A3B | 1.00 | 700 | 377 | 2721 | 11.0s |
| Qwen3.6-35B-A3B-MTP | 1.00 | 2471 | 11369 | 0 | 32.7s |
| Gemma-4-26B-A4B-it | 1.00 | 3033 | 13748 | 0 | 77.6s |
| — EXCLUDED, term < 0.8 — | | | | | |
| deepseek-r1-0528-8b-FLM | **0.33** | 821 | 498 | 3588 | 78.5s |
| lfm2.5-230m-code-exp | **0.00** | 45 | 230 | 0 | 0.1s |

### What changed, and what it cost to learn

**`gpt-oss-20b` vs `Qwen3-8B` finally resolves under clean conditions:** 399 tok / 5.4s against
490 tok / 11.9s. gpt-oss-20b IS cheaper on both — but by **1.2x on tokens**, where the character
columns implied 9.4x. The original default survives; its margin was inflated roughly 8x.

**Character ranking was wrong in both directions.** `gpt-oss-20b` ranked 1st on chars (157) and
is 5th on tokens; `Qwen3-Coder-30B` ranks 3rd on tokens while sitting mid-table on chars. Four
lanes are measured post-strip (`drop > 0`) and their `rawch` is not comparable to the rest.

**The bottleneck moved from cost to accuracy — and has now been closed.** The three cheapest
lanes are `llama3.2-3b-FLM` (61 tok), `SmolLM3-3B` (69) and `Qwen3-Coder-30B` (155) — 2.6x to 8x
cheaper than gpt-oss-20b. `Qwen3-Coder-30B` was already known to be a **fabrication trap** (toy
1.00 collapsing to 0.83 on real code, inventing defects in clean files). The other two were
unmeasured, and were the open question the routing rule hinged on.

### Answered: the cheap end of the roster is decorative

`review_lane_benchmark.py --reps 3`, 5 planted defects + 3 clean controls, executed ground truth,
all four V-model gates (S1/S2/C1/C2) PASS:

| lane | GEN_TOK | **bal acc** | sens | spec | named | parsed |
|---|---|---|---|---|---|---|
| llama3.2-3b-FLM | 61 | **0.74** | 0.60 | 0.89 | 7/15 | 24/24 |
| SmolLM3-3B-IQ4_XS | 69 | **0.67** | 1.00 | **0.33** | 12/15 | 24/24 |
| gpt-oss-20b (default) | 399 | 0.86 | — | — | — | — |

Neither displaces the default. 6.5x cheaper buys 0.74 instead of 0.86, and `llama3.2-3b-FLM`
misses 40% of real defects (sens 0.60) — a lot of false negatives for a review lane.

**`SmolLM3-3B` is exactly the pathology the clean controls exist to catch.** sens=1.00 / spec=0.33
means it found every planted defect AND called two of three clean files buggy. Ranked on detection
rate it would top the board; on balanced accuracy it is barely above chance. This is the concrete
case for why the headline metric is balanced accuracy and why the clean controls are not optional.

**Do not build an ensemble from these two.** Their profiles are complementary — `llama3.2-3b-FLM`
high-specificity/low-sensitivity, `SmolLM3-3B` the inverse — which is exactly the shape that
invites an AND/OR gate. An AND-gate inherits its strictest member: it rescues the worst model and
never beats the best, at double the cost. Recorded so the idea is refused on evidence rather than
re-derived and tried.

### The FLM exclusion rests on a premise that is partly false

`_is_llamacpp_thinking_model` excludes every `*-FLM` id, justified in-code as: *"it has no
`reasoning_content` channel and rejects the arg on some builds — this guard is load-bearing for
the LIVE `deepseek-r1-0528-8b-FLM` NPU reasoning tier"*. Measured `drop` per rep:

| FLM model | dropped chars (3 reps) | term |
|---|---|---|
| llama3.2-3b-FLM | 0, 0, 0 | 1.00 |
| qwen3-4b-FLM | 1475, 1662, 3243 | 1.00 |
| deepseek-r1-0528-8b-FLM | 3588, 7253, 2195 | **0.33** |

The "no `reasoning_content` channel" claim holds for the non-reasoning FLM model and is **false
for both FLM reasoning models — including the one the comment names by name**.

The second claim — that FLM builds reject the argument — is also **not reproduced**. Both accept
`reasoning_format="none"` without error. But it has no effect. Against a llamacpp control, 2 reps
each, `(content_chars, reasoning_chars)`:

| backend | variant | rep 1 | rep 2 |
|---|---|---|---|
| llamacpp (`Gemma-4-26B-A4B`) | baseline | (206, 2474) | (183, 2882) |
| llamacpp | `reasoning_format=none` | (2984, **0**) | (2884, **0**) |
| FLM (`deepseek-r1-0528-8b-FLM`) | baseline | (182, 925) | (180, 759) |
| FLM | `reasoning_format=none` | (238, **933**) | (202, **963**) |

On llamacpp the flag does exactly what the guard intends — reasoning moves into `content` and
`reasoning_content` empties. **On FLM it is accepted and silently ignored.**

**So the exclusion is CORRECT IN EFFECT and wrong in both of its stated reasons.** Adding
`gpt-oss` / `nemotron`-style FLM entries to `_THINKING_MODEL_MARKERS` would achieve nothing on
that backend, because the flag is a no-op there. The comment should say *"the flag is silently
ignored by the FLM backend, so including these ids would be misleading"* — not that the channel
is absent or the argument rejected.

### This settles the `<think>`-normalisation question

There is **no server-side option for FLM lanes**. `reasoning_format="none"` covers llamacpp only.
Any fix that has to work across the whole fleet must therefore be **client-side**: prefer
`content`, fall back to `reasoning_content` when content is empty (already done at
gaia_adapter.py:269), and strip `<think>` blocks when reasoning arrives inline. Choosing between
server-flag and client-normalisation was the open design call; it is now decided by measurement
rather than preference, because only one of the options can cover both backends.

Not claimed: that any of this fixes `deepseek-r1-0528-8b-FLM`'s term 0.33. It returns NON-EMPTY
`content` that merely lacks the marker — a different failure from the empty-content signature the
guard was built for, and one no reasoning-channel change addresses. Tracked on kanban
`t_903e8d2e`.

Two benchmarks, two different questions. Neither answers the other.

- `scripts/experiments/review_lane_benchmark.py` — is the VERDICT right?
  Balanced accuracy over 5 planted defects + 3 clean controls, ground truth EXECUTED
  (no LLM judge). Gates S1/S2/C1/C2 must pass or the run is void.
- `scripts/experiments/lane_termination_benchmark.py` — does a usable ANSWER come out?
  termination_rate, raw output volume, overhead_ratio, ceiling_rate, p50 latency.

## Results (2026-08-16, 3 reps each, max_tokens=4000, evaluative prompt)

| model | bal acc | term | raw chars | overhead | ceiling | p50 |
|---|---|---|---|---|---|---|
| gpt-oss-20b | 0.86 | 1.00 | **205** | **0.06** | 0.00 | **3.9s** |
| Nemotron-3-Nano-30B-A3B-GGUF | **1.00** | 1.00 | **411** | 0.22 | 0.00 | 16.1s |
| Gemma-4-E4B-it-GGUF | n/a | 1.00 | 1449 | 0.81 | 0.00 | 5.7s |
| Gemma-4-E2B-it-GGUF | n/a | 1.00 | 1894 | 0.88 | 0.00 | 18.9s |
| **Qwen3-8B-GGUF** | **1.00** | 1.00 | 1936 | 0.91 | 0.00 | **9.7s** |
| Qwen3.6-35B-A3B-MTP-GGUF | 1.00 | 1.00 | 9688 | 0.93 | 0.00 | 41.2s |
| Gemma-4-26B-A4B-it-GGUF | 0.73 | **0.67** | 17400 | **0.97** | **0.67** | **90.0s** |

`raw chars` = median total generated output. This is the DIRECT cost measure; sorted by it.
`overhead` = fraction of that output which is reasoning the caller discards.
`ceiling` = fraction of reps cut off at the token limit — not finished, truncated.

### The cost columns are invalid — the lanes are not measured the same way

`raw_chars` and `overhead` measure the text `build_gaia_llm_tier` returns. What that text
CONTAINS depends on an undocumented string match in `src/cohezion/inference/gaia_adapter.py`:

```python
_THINKING_MODEL_MARKERS = ("gemma-4", "gemma4", "gemma-3", "qwen3", "deepseek-r1")
```

A matching model is sent `reasoning_format="none"`, which keeps its chain-of-thought INLINE in
`content` — so the benchmark counts all of it. A non-matching model streams reasoning to a
separate `reasoning_content` field that the adapter DROPS (gaia_adapter.py:269 returns `content`,
falling back to `reasoning_content` only when content is empty) — so the benchmark counts only
what survived the strip.

`gpt-oss-20b` and `Nemotron-3-Nano-30B-A3B` match nothing in that tuple. **They are the two lanes
the table calls cheapest, and they are the two measured post-strip.** The 85x spread is
substantially an artifact of which strings are in that tuple.

Measured with `usage.completion_tokens`, which the backend computes over every generated token
and no configuration can strip (contract prompt, n=3 medians, all three resident):

| lane | `raw_chars` rank | true tokens | ratio |
|---|---|---|---|
| Qwen3-8B-GGUF | 5th of 7 (1936) | **315** | **1.0x** |
| gpt-oss-20b | 1st (205) | 594 | 1.9x |
| Nemotron-3-Nano-30B-A3B | 2nd (411) | 886 | 2.8x |

**The ranking inverts.** The lane the table placed 5th is the cheapest generator; the lane it
made the default generates 1.9x more, not 9.4x less. `usage.completion_tokens` is the correct
cost measure and `scripts/experiments/reasoning_channel_probe.py` detects which lanes need it.

Do NOT read a new routing rule off that three-row table. It is n=3 with all three models
resident, so its LATENCY column is contention-contaminated (gpt-oss-20b measures 8.0s here
against 3.9s in the original run). Token counts are contention-independent; wall-clock is not. A
clean re-measurement needs one large model resident at a time.

*How this was found, because the first two attempts were wrong.* The anomaly was Nemotron taking
13.3s to return 173 chars at `max_tokens=4000` but 8.0s to return 2209 at 512 — a larger cap
cannot slow generation. First hypothesis, cold start: refuted, an explicit warmup left p50 at
16.9s. Second, that the contract prompt pushes reasoning into the visible channel: refuted, the
raw API still showed Qwen3-8B hiding 89% under that exact prompt. Only reading gaia_adapter.py
resolved it. Two live inference probes were spent on hypotheses that reading 30 lines of source
would have killed.

## Routing rule — restored, on token-measured evidence

Supersedes both the invalid char-ranked rule and the suspension that followed it.

- **Default: `gpt-oss-20b`** — 399 tok / 5.4s at 0.86 balanced accuracy. Cheapest lane that has a
  measured accuracy score.
- **Escalate to `Qwen3-8B` when a false negative is expensive** — 1.00 accuracy for 1.2x the
  tokens and 2.2x the latency. A real, small premium, not the 9.4x the old table implied.
- **Never route review work to `Qwen3-Coder-30B`** despite it being the cheapest lane with any
  measured accuracy at all (155 tok / 1.8s). Its 0.83 real-code score comes with fabricated
  defects on clean files. Explicitly called out because its cost columns are the most attractive
  on the board and will tempt exactly the wrong choice.
- **Exclude `deepseek-r1-0528-8b-FLM` (term 0.33) and `lfm2.5-230m` (term 0.00)** from structured
  work. Neither reliably emits a parseable answer at any cost.
- **`Gemma-4-26B-A4B` and `Qwen3.6-35B-A3B-MTP` are the two most expensive lanes** (3033 and 2471
  tok) with no measured advantage. Treat "bigger" as a cost, not a capability, until something
  measures otherwise.
- **`llama3.2-3b-FLM` (0.74) and `SmolLM3-3B` (0.67) do NOT displace the default** despite being
  ~6x cheaper — measured, not assumed. `SmolLM3-3B` in particular says BUG to nearly everything
  (spec 0.33). The cheap end of the roster is decorative for review work.

## Live defect: two reasoning lanes are outside the guard

This is not only a measurement problem. `_THINKING_MODEL_MARKERS` exists to prevent documented
defect `4dd925b0081f` — a reasoning model whose `</think>` never closes in-budget returns EMPTY
`content` with `finish_reason='length'`, so a structured prompt gets nothing back.

`gpt-oss-20b` and `Nemotron-3-Nano-30B-A3B` are reasoning models outside that guard, and the
defect reproduces. Same structured prompt at three budgets:

| budget | returned |
|---|---|
| 64 | `'We need to answer: "Is a test suite written ag…'` — 285 chars of raw chain-of-thought |
| 128 | `'VERDICT: insufficient'` |
| 4000 | `'VERDICT: insufficient'` |

At budget 64 `content` came back empty and the line-269 fallback returned `reasoning_content`, so
the caller receives reasoning where it expects a verdict. The fallback prevents a hard failure
and converts it into a silent contract violation — worse for a structured consumer, which will
parse chain-of-thought as an answer.

**The fix is not simply appending `gpt-oss` and `nemotron` to the tuple.** Doing so flips these
lanes to inline reasoning, and at adequate budget the current unguarded behaviour is *better* for
callers: `gpt-oss-20b` returns a clean 21-char `VERDICT: insufficient`, where guarded `Qwen3-8B`
returns 1551 chars the caller must strip `<think>` blocks from. Note also that guarding does not
rescue the low-budget case — guarded `Qwen3-8B` at budget 64 also returns only truncated
`<think>` text. The real fix is likely to normalise BOTH paths to answer-only (strip `<think>`
when inline, prefer `content` when split) rather than to make every lane inline. Left as a
design decision, not made unilaterally.

## Four traps this measurement exposed

**A metric can be invalidated by a config flag three files away.** Nothing about
`overhead_ratio`'s definition is wrong. It was invalidated by a string tuple in the adapter that
decides, per model, whether reasoning is inside the measured text at all. The benchmark had no
way to know, and reported clean numbers with a plausible 85x spread. Prefer a measure the
provider computes and cannot strip — `usage.completion_tokens` — over one derived from returned
text, whenever such a measure exists.



**Accuracy alone is not lane suitability.** The 26B's 0.73 looks mediocre-but-usable; its cost
columns are what disqualify it. Neither benchmark reaches a routing decision alone.

**"Bigger is more capable" is not a routing rule.** The 35B was chosen as the escalation lane on
that instinct and is beaten on every axis by a 6.68GB model. Measure before routing.

**A summary-fed review fabricates.** The 35B scores spec=1.00 (zero false alarms on clean
controls) when handed SOURCE, yet invented a defect in clean code when handed a PROSE SUMMARY of
a large diff. Pass the diff, chunked by hunk if necessary — never a description of it. That
fabrication was a harness defect, not lane unreliability. NOTE: an independent session reported
`Qwen3-8B` fabricating under a find-defects mandate; that report was also summary-fed, so the
same caveat applies to the recommended escalation lane. Feed it source.

## Coverage and what to do next

Seven lanes on termination; seven roster models still have none (`lfm2.5-230m`,
`llama3.2-3b-FLM`, `qwen3-4b-FLM`, `SmolLM3-3B`, `deepseek-r1-0528-8b-FLM`, `Qwen3-Coder-30B`,
`Gemma-4-31B`). Five lanes tie at term=1.00 and are not separated from each other at n=3.

**Do not extend the table before fixing the instrument.** Progress:

1. ~~Detect which lanes are measured post-strip.~~ **DONE** —
   `scripts/experiments/reasoning_channel_probe.py` reports guard status alongside the hidden
   channel, so it flags only lanes the benchmark actually mismeasures. (It must report the guard,
   not just the channel: the guard is applied by the adapter, not the server, so a raw-API probe
   sees a split channel even for guarded models. An earlier version flagged `Qwen3-8B` — the one
   healthy lane of three — for exactly that reason.)
2. ~~Add `usage.completion_tokens` as the cost column.~~ **DONE** — `OrchestrationResult` now
   carries `gen_tokens` and `dropped_reasoning_chars`; the benchmark leads with `GEN_TOK` and
   **prints that its own character columns are incomparable** whenever any lane reports dropped
   reasoning. The benchmark diagnoses itself rather than relying on someone remembering to run a
   separate probe.
3. **NEXT: re-measure the full roster** with ONE large model resident at a time, so latency is
   not contention-contaminated, and rank by `GEN_TOK`.
4. Decide the `<think>`-normalisation design question above before adding markers to the tuple.

Distortion magnitude, measured after the fix (n=2, both lanes resident): by characters
`gpt-oss-20b` looks 20x cheaper than `Qwen3-8B` (166 vs 3281); by tokens ~1.8x (372 vs 668).
Note that this run puts `gpt-oss-20b` ahead on tokens while the earlier n=3 run put it behind
(594 vs 315) — the token measure is right, but at n=2–3 it does not yet separate these two lanes.
That is another reason step 3 is a re-measurement and not a formality.

Note that the escalation lane did not change when Nemotron was added — offered at the time as
weak evidence the table was stabilising. It was not: the table was stable because the instrument
was consistently mismeasuring the same two lanes. Stability under extension is not validity.

The 35B measured is the **MTP** variant (22.1GB); the accuracy roster lists plain
`Qwen3.6-35B-A3B-GGUF`.
