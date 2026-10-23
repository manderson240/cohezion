# Does the compound loop make session N+1 better than session N?

The root README's headline claim is that Cohezion is "the compound AI engine that gets smarter
every session": `SkillRefiner` version-bumps a skill from execution results, and the refined
skill makes the next session's executions better. This benchmark is the first measurement of
that claim in the repository. It was designed so it could come back **False**, and the result
below is reported as measured, including the parts of the design that changed after the data
came in.

**Verdict (run `20261023T124632Z`, 2026-10-23): not supported by this run.** Over measured
sessions, the refined skill scored 0.884, the placebo skill (same growth, untargeted text)
0.917, and the frozen skill 0.500. Growing the skill file lifted this model by about 0.4
regardless of what the new sections said, and the refiner's content showed no advantage over
the placebo. The comparison is underpowered (see "What this run can and cannot say"), so the
honest statement is "no detectable advantage over placebo", not "no effect".

## What is actually being tested

```
CompoundExecutor.execute_task(skill_name=S)
  -> fetch_experience_guidance(S)   reads "## Learned Refinement" sections from S's PRIME file
  -> execute_fn(guidance)           guidance_to_prompt_text() puts them in the model prompt
  -> RetrospectionEngine            gates should_refine on coherence / health
  -> SkillRefiner.refine()          appends a "## Learned Refinement" section, bumps ## Version
```

Executor, retrospection engine, refiner and refinement reader are the production objects. The
`execute_fn` is the harness's own: it calls the production `guidance_to_prompt_text` and posts
to one pinned model, bypassing the `make_local_execute_fn` tier cascade so the model cannot
change between calls. The cascade's own use of `guidance_to_prompt_text` is covered by a mocked
unit test, not by this run.

A **session** is a fresh process (fresh executor, refiner, guardrail rate limiter, caches) that
runs a fixed set of 16 short-answer tasks. The only state that survives between sessions is the
skill's PRIME file, which is exactly the channel the claim says carries the improvement.

Three arms share the same model, base skill and task set:

| Arm | Refinement | What the PRIME file does |
|---|---|---|
| **treatment** | on (real `SkillRefiner`) | grows by one section after every successful task, so sections accumulate *within* a session as well as across sessions |
| **frozen** | off | never changes: the no-intervention plateau, and the noise floor (each session re-measures the same prompt) |
| **placebo** | off | *after* each session, gains the same *number* of sections the treatment arm gained that session, filled with plausible but untargeted writing advice ("Use correct grammar and spelling.") |

The placebo controls for "any plausible prompt growth helps". Section count is matched; token
length is not (treatment sections run about 15% longer: 575-594 prompt tokens against 493-516).

### Instrument

- **Model**: `llama3.2-1b-FLM` on the XDNA2 NPU through the Lemonade router at `:13305`.
  Temperature 0, `think=false` sent on every request, `max_tokens=96`. Cost $0.
- **Base skill** (the deliberately weak starting policy, shared by all arms): a verbose
  "restate, explain, then answer" instruction that spends the token budget on preamble.
- **Scoring**: deterministic whole-token match against expected terms (`404` does not match
  `4040`; `ss` does not match `class`). Full model outputs are stored in the artifact so every
  pass can be re-derived. The committed run stored only the first 160 characters, so its
  per-task flags are as recorded.
- **Outcome validity**: a transport error (router admission refused, upstream unreachable,
  timeout), an input-guardrail block (the production resource guard refusing a task under CPU
  pressure) or an output-filter block cannot make a returned answer wrong, so those calls are
  excluded from the rate instead of scored 0. A session with fewer than 8 valid calls is
  *unmeasured*. **This rule was written after the first run**: the script that collected the
  data counted every refused call as a failure. The raw figures are kept in the artifact
  (`pooled_raw`) and shown below next to the corrected ones.
- **No ground-truth leakage**: the scorer never feeds back into the loop. The refiner sees only
  the executor's own health metrics, as in production. The flip side is that the refiner's text
  cannot track correctness, so a null result on content is close to mechanical for *this*
  refiner; the run measures this wiring, not compounding in general.
- **Calibration before launch** (falsifiable-eval-harness rule 1: the baseline must sit in the
  30-70% band). Transcript: [`calibration_2026-10-23.txt`](calibration_2026-10-23.txt).

  | `max_tokens` | base-skill pass rate | transport errors | in band? |
  |---|---|---|---|
  | 48 | 0.250 (4/16) | 0 | no |
  | 64 | 0.188 (3/16) | 0 | no |
  | **96** | **0.625 (10/16)** | 0 | **yes** |

  The token cap is therefore part of the instrument: the lift reported below is a lift under a
  96-token budget. `qwen3.5-4b-FLM` (0/11 valid, verbose, admission refused) and
  `gemma4-it-e2b-FLM` (never served) were probed and rejected. This machine is restricted to
  FLM (NPU) models by a project hook; the NPU is single-slot and was shared with another
  client's workload for the whole run (median call latency 20-110 s).

### Verdict rule (encoded in the script, recomputed by the test)

Supported if and only if, over **measured** sessions:

1. the treatment arm has at least two measured sessions, **and**
2. its least-squares slope is >= 0, **and**
3. its pooled valid pass rate exceeds the frozen arm's by more than the frozen arm's own
   max-min fluctuation, **and**
4. its pooled valid pass rate exceeds the placebo arm's by that same margin.

The first draft compared final-session values; it was replaced by the pooled rule after the
first run's final treatment session was entirely refused by the resource guard (0 valid calls).
Both rules give the same answer on this data. The rule is tested in both directions with
synthetic rows (`tests/benchmarks/test_compound_loop_jsonl.py`), and that test also recomputes
the committed verdict from the committed per-task records, so `claim_supported` cannot be
hand-edited.

## Result

Valid pass rate per session (passes / valid calls, 15 scored tasks). `--` = unmeasured (fewer
than 8 valid calls); the parenthetical says why.

| session | treatment | frozen | placebo |
|---|---|---|---|
| 0 | 0.857 (12/14) | 0.364 (4/11; 3 refused by the resource guard, 1 output-filtered) | -- (4/5; 8 refused by the resource guard, 2 by the router) |
| 1 | 0.857 (12/14) | 0.500 (7/14) | 0.923 (12/13) |
| 2 | 0.933 (14/15) | 0.583 (7/12; 3 router errors) | -- (5/6; 9 refused by the resource guard) |
| 3 | -- (0/0; all 15 refused by the resource guard) | 0.533 (8/15) | 0.909 (10/11; 4 refused by the resource guard) |

| Pooling | treatment | frozen | placebo |
|---|---|---|---|
| **measured sessions, valid calls (the verdict input)** | **0.884** (38/43) | **0.500** (26/52) | **0.917** (22/24) |
| all sessions, valid calls | 0.884 (38/43) | 0.500 (26/52) | 0.886 (31/35) |
| all sessions, every refused call counted as a failure (first-draft metric) | 0.633 (38/60) | 0.433 (26/60) | 0.517 (31/60) |

| Quantity | Value |
|---|---|
| treatment - frozen (measured) | +0.384 |
| placebo - frozen (measured) | +0.417 |
| treatment - placebo (measured) | **-0.033** |
| frozen fluctuation (max - min over its 4 measured sessions) | 0.220 |
| treatment slope over its 3 measured sessions | +0.038 per session |
| refinement sections written by the treatment arm | 46 (15, 15, 16, 0) |
| sessions completed / planned | 4 / 6 |

Under the first-draft metric the ordering is treatment > placebo > frozen (+0.12 over placebo);
under the corrected metric it is placebo > treatment > frozen. The sign of the treatment-placebo
gap depends on how refused calls are handled, which is the clearest sign that the gap is not
resolved by this run. Under every metric the gap to placebo is smaller than the frozen arm's own
fluctuation.

### What this run can and cannot say

- **Can say**: the refined skill did not beat the placebo skill. 46 refinements were written and
  read back into prompts (five at a time), and the loop ran end to end on the local NPU.
- **Can say**: adding `## Learned Refinement` sections of either kind moves this model from
  mostly-failing to mostly-passing under a 96-token cap. The frozen arm's outputs all hit the
  cap mid-preamble (`"To find the default port for PostgreSQL, we need to understand the
  context in which PostgreSQL is used..."`); with sections present the model usually answers
  first (`"The default port for PostgreSQL is 5432."`, 10 tokens). The shift is visible from
  the third section onward in treatment session 0. Whether it is prompt length, markdown
  structure, or the instruction being pushed further from the question was not separated.
- **Cannot say**: that refinement has no effect. With 43 and 24 valid calls the two-proportion
  interval on treatment minus placebo is roughly +/-0.15, and the sessions are not independent
  (same 15 tasks, same plateaued prompt). A real +0.1 refiner effect would not have been
  detected. The verdict is "not supported", not "refuted".
- **Cannot say**: anything about compounding past five sections. The reader caps the prompt at
  the five most recent sections, so the treatment prompt stops changing after the sixth task of
  session 0; the flat treatment curve (0.857, 0.857, 0.933) is the expected shape under that
  cap, and the "session N+1 builds on session N" step is only observed as the difference
  between session 0's first five tasks and everything after.
- **Confounds, disclosed**: arms ran in a fixed order (treatment, frozen, placebo) so host load
  drifts with arm; placebo session 0 was run with zero sections (its growth is applied after
  scoring) and is unmeasured for a different reason; `binsearch` fails in every arm in every
  session (the model answers O(n)), so the ceiling is 14/15; temperature 0 is not
  bit-reproducible on this backend (the same frozen prompt scored 0.36-0.58 across sessions and
  0.625 at calibration); the `mergesort` task was dropped from scoring at finalization because
  its original expected term `merge` matched the frozen arm's restatement of the question
  (fixed in the task set for future runs); the frozen arm's "fluctuation" mixes that
  nondeterminism with changing denominators (11, 14, 12, 15 valid calls).
- **The run was interrupted**: after 4 complete sessions (4 h 35 min of session wall time) the
  host killed the fifth session's treatment worker (SIGKILL). The orchestrator of that version
  aborted on the dead worker, so no fifth-session record exists; the committed artifact was
  rebuilt from the per-session records with `--finalize-from`. The current script records a
  killed worker as an unmeasured session and continues.

### What the refiner wrote

The treatment arm's final PRIME file is committed as [`final_skill_treatment.md`](final_skill_treatment.md)
(46 sections, version 1.0.46). All 46 carry the identical insight
`high quality execution (low anomaly score); efficient token usage` and one of four
recommendation strings, for example
`Optimize PRIME skill guidance for output quality in generate operations (quality=100%).`
`_generate_learning_signal` derives these from the executor's health metrics (the anomaly
score is 1.0 for any non-empty output; the token count is 0 because no token client is wired),
not from whether the answer was right, and the text is addressed to a skill maintainer, not to
the model. The model sometimes imitates the section format in its answers
(`"## Learned Refinement (...)\n\n**From**: Breadth-First Search (BFS)"`), in both the
treatment and the placebo arm. The 17 refine calls per session are 16 per-task calls plus the
MGPO batch refinement the executor fires on its tenth execution.

## Three wiring facts this benchmark surfaced

1. **The loop was open at its consumption point** (fixed on this branch).
   `fetch_experience_guidance` loaded learned refinements into
   `guidance["learned_refinements"]`, but the production prompt builder
   (`make_local_execute_fn`) read only `guidance["guidance"]`, a key nothing sets. Refinements
   were written and read back into a dict that no prompt consumed.
   `refinement_reader.guidance_to_prompt_text` is now the single flattening used by
   `make_local_execute_fn`, with a discriminating test
   (`tests/compound/test_refinement_prompt_consumption.py`).
2. **226 of 229 PRIME files cannot be refined** (reported, not fixed here).
   `SkillRefiner._append_refinement` inserts before a `## Version: x.y.z` line (fallback
   `## Keywords:`); only 3 skill files carry either anchor, so `refine()` returns `None` for
   the rest. No PRIME file on `main` carries a `## Learned Refinement` section today.
3. **Production refine gates spend real inference and can reach for the cloud.** The
   factory-wired path bootstraps golden fixtures through a 180 s GGUF call per refinement and
   runs a 3-persona adversarial gate on a GGUF model that escalates to a metered frontier
   cascade when the local lane is down. This run follows the reference driver
   (`scripts/drivers/compound_cycle.py`: plain `SkillRefiner`, no regression gate) and pins the
   adversarial gate to `fail-open` (its documented offline path), which promotes every
   refinement: the most favourable condition for the claim. `--adversarial-gate flm` runs the
   gate live on the same NPU model instead.

## Reproduce

```bash
# 1. calibration probe (must print IN BAND)
uv run python scripts/experiments/compound_loop_evidence.py --calibrate \
    --models llama3.2-1b-FLM --max-tokens 96

# 2. the three-arm run; it re-runs the calibration and refuses to launch arms out of band
uv run python scripts/experiments/compound_loop_evidence.py \
    --model llama3.2-1b-FLM --max-tokens 96 --sessions 6 --adversarial-gate fail-open

# 3. schema, recount and verdict-rule guard (also runs the rule on synthetic rows)
uv run pytest tests/benchmarks/test_compound_loop_jsonl.py -q
```

Exit code is 0 when the claim is supported and 1 when it is not. Session records stream to
`results.partial.ndjson`; an interrupted run is finalized with
`--finalize-from <that file> --workdir <the run's workdir>` (the committed run used
`--exclude-task mergesort`, recorded in the verdict). An offline plumbing check with canned
answers is available with `COMPOUND_EVIDENCE_STUB_ROUTER=1`.

Budget: on an idle NPU a call takes 2-5 s, so 6 sessions x 3 arms x 16 tasks is roughly 30-60
minutes; the committed run took 4 h 42 min on a contended NPU.

## Files

| File | Contents |
|---|---|
| `results.ndjson` | newline-delimited JSON: one record per (arm, session) with per-task outputs, plus one `verdict` record. Named `.ndjson` because this repository routes `*.jsonl` to Git LFS, which would commit the evidence as a pointer. |
| `calibration_2026-10-23.txt` | the calibration probes behind the table above |
| `final_skill_treatment.md` | the PRIME file after the treatment arm's last session (46 refiner-written sections) |
| `final_skill_placebo.md` | the PRIME file after the placebo arm's last session (46 placebo sections) |
| `final_skill_frozen.md` | the unchanged base skill |
