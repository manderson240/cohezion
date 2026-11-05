---
name: verifiable-questions-from-fresh-data
description: |
  Build tool-dependent evaluation questions with one deterministic answer from real data released
  after a model's training cutoff (the Axion 1.0 Stage II recipe, arXiv:2611.03233). Use when:
  (1) you need held-out eval or golden-fixture cases that a model cannot answer from memory,
  (2) populating golden_fixture rows for the SkillRefiner R3 regression gate, (3) you are about to
  call two implementations "independent" because they agree, (4) a question's answer depends on
  how labels, names or timestamps are normalized, (5) you are about to write that questions
  "cannot be memorized". Key insight: two implementations agreeing proves the code, not the
  wording; and the agreement check must cover every entity's score, not just the winner.
author: Claude Code
version: 1.0.0
source: session 2026-11-04 (research/artemis2/verifiable_tasks.py, 4-lens adversarial review)
---

# Verifiable Questions from Fresh Data

## The recipe (Axion 1.0, Stage II)

1. **Filter** real records by a condition (a time window, a file set, a speaker list).
2. **Select one entity by an extreme value**, and require it to beat the runner-up by a stated
   margin (relative or absolute). No margin, no question.
3. **Compute a derived quantity** for that entity with a fixed formula. That is the answer.
4. **Word the question around the fixed answer**, then check it is answerable only with tools.

Grounding in data first published after the cutoff (e.g. a PDS release) means no model trained
earlier has seen the answer. Pick sources with checksums so the answer is reproducible.

## The checks that make it trustworthy

- **Two implementations, sharing no parsing code** (e.g. polars and stdlib `csv` + `datetime`).
  Reject the task unless they agree on:
  - the selected entity;
  - the answer (to a tight relative tolerance);
  - **every entity's selection score.** Comparing only the winner let a bad runner-up through:
    the margin was judged on scores only one side had computed. Compare the full dict.
- **Margin gate.** It is not decoration: a real "widest daily temperature range" candidate was
  3.07 vs 3.04 degC and must be dropped. Keep dropped candidates in the output with the reason.
- **Closed-book probe** (from the paper): drop questions a model answers without tools. If you
  cannot run a model, record `closed_book_probe: not run` per task. Do not imply it was done.

## Traps found by adversarial review

- **Agreement does not validate the question.** Both implementations read `speaker` the same
  way, so both said 71. A careful solver normalizing labels like `Hansen [CAPCOM]` and the typo
  `Hasnen` gets 91 (and 22,859 words, not 21,489). Fix it in the WORDING: state exact-match rules,
  what counts, what does not, and quirks like duplicate files that are still counted.
- **Pin question text to code constants.** If the text says "launch 22:35:12" or "more than 60
  seconds", add a test asserting those strings come from the constants the code uses.
- **Shared constants are shared assumptions.** Window bounds, name lists and thresholds used by
  both implementations are checked by neither. Test them with synthetic data that has a
  planted winner, a planted trap (an excluded label, an out-of-window extreme) and a near-tie.
- **Leakage claims must be scoped.** "Cannot be memorized" holds only for models whose training
  data ends before the release date, and stops holding once you publish answers. Entity choice is
  often a 1-in-2 or 1-in-4 guess. Say so.
- **Deterministic output order.** `group_by` without `maintain_order` reorders score dicts
  between runs; sort keys before writing so regenerated JSON diffs cleanly.

## Mutation-testing the builder (do it, and do it right)

- **Confirm the baseline is green first.** A red baseline makes every mutant read "1 failed",
  which looks like a kill. It fooled this session once.
- **Detect mutants that did not apply** (`cmp` the mutated file against the original; a sed
  pattern that matches nothing tests nothing).
- A mutant that makes the implementations disagree only *rejects* the task. Your tests must
  assert `"rejected_because" not in record` on valid input, or that mutant survives.
- Some mutants are equivalent (removing a defensive sort when input is always ordered). Name
  them rather than writing a test that cannot exist.

## Cohezion wiring

- These tasks fit `prompt_version_registry.golden_fixture` (input, expected_output, deterministic
  validator). `SkillRefiner._ensure_golden_fixtures` already bootstraps fixtures, but from
  LLM-proposed keywords grounded against the skill's CURRENT output: they pin existing behaviour
  (regression), not correctness. Questions with externally verified answers add the other half,
  a fixture that fails when the skill is wrong, not merely when it changes.
- Run the probe on the local tier first (quarter-on-a-string). Axion-35B is a fine-tune of
  Qwen3.6-35B-A3B, the local reasoning model on :13305.

## Reference implementation

`research/artemis2/verifiable_tasks.py` (`pick`, `make_task`, `std_*` readers) and
`tests/unit/research/test_artemis2_verifiable_tasks.py` (synthetic-CSV fixtures, boundary tests).
