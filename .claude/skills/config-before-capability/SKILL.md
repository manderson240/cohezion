---
name: config-before-capability
description: |
  Guard against the single most expensive error in model/system evaluation: concluding a
  CAPABILITY limit from a CONFIGURATION or MEASUREMENT gap. Use when: (1) a model or component
  scores 0 or unexpectedly badly, (2) you are about to write "X cannot do Y" / "X is the
  ceiling" / "X collapses at Z", (3) a result CONFIRMS something you or a source predicted,
  (4) you are auditing config and about to generalise from one layer, (5) any negative
  capability finding is about to be recorded somewhere durable (skill, vault, docs, harness).
  Trigger phrase: you are attributing a bad number to the thing being measured rather than to
  the apparatus measuring it.
author: Claude Code
version: 1.0.0
---

# Configuration Before Capability

## Problem

A bad measurement has at least four possible owners:

1. **The subject** — it genuinely cannot do the thing. (capability)
2. **The harness** — the plumbing discards or corrupts a correct answer. (bug)
3. **The metric** — you measured something adjacent to what you claim. (design flaw)
4. **The configuration** — the subject was run wrong. (setup gap)

Only #1 is a capability finding. The default assumption is almost always #1, and it is
usually wrong. Recording #2–4 as #1 puts a false fact into permanent storage, where it then
gets cited.

## The four instances that produced this skill (one session, 2026-07-28)

| # | Reported | Actual owner | Truth after fixing |
|---|---|---|---|
| 1 | "Bonsai-27B collapses at Q1_0 — 0/8" | **Harness**: shim read only `content`; thinking model put the answer in `reasoning_content` | **8/8**, best-in-class at 3.54 GB |
| 2 | "Asymmetric cascade: 8/8 at 59% latency" | **Metric**: "precision" measured ONLY clean-code controls, never whether a claimed defect was the RIGHT defect | Refuted — 62%/67%, worse than either tier |
| 3 | "NPU ceiling is 56%, architectural" | Concluded before checking config; happened to survive | Ceiling real (confirmed independently) |
| 4 | "Every NPU model runs on bare defaults" | **Layer blindness**: audited recipe layer only; sampling also arrives at the REQUEST layer | False — FLM models get card sampling |

| 5 | "Bonsai-27B 0%, E4B 0% on the public benchmark" | **Harness ×2**: head-only answer parser + `max_tokens` too small for CoT | Numbers were pure artifact; re-run required |

Note #4 occurred while diagnosing #3. Note #5 occurred in a benchmark written *after* this
skill existed, by an author holding it. **Knowing the failure mode does not prevent it. Only
running the checklist does.**

### Why #5 is the most instructive

It had two compounding faults and a built-in disguise:

- The answer parser scanned the FIRST 40 chars. Thinking models emit `<|channel>thought …`
  first, so the head is never the answer.
- `max_tokens=512` truncated mid-reasoning — the model produced 1727 chars of thought and
  never reached a verdict at all.

**The disguise:** the one NON-thinking model in the run (a frontier cloud model) parsed
perfectly and scored 67%. So the output read as "frontier model works, local models are
hopeless" — a clean, plausible capability story. The harness failed *selectively*, on exactly
the class of model under evaluation, which is far more dangerous than failing uniformly.

**Rule:** when one subject parses and others return 0, suspect the PARSER before the subjects.
A uniform failure looks like a bug; a selective one looks like a finding.

## Instance 6 — the one that ran in REVERSE (and got reported before it was caught)

Instances 1–5 were faults caught *before* becoming findings. #6 was not: a definitive negative
conclusion — *"the capability is not there, at chance"* — was **delivered to the user** and then
overturned.

A model scored **exactly 50.0%** (chance) detecting real bugs in SWE-bench snippets. Sober,
statistically clean at n=60, and it matched an expectation that small local models would be weak
on real code. It was recorded as a hard negative result.

The task was **invalid, not hard**. It asked whether `cright[...] = 1` or `= right` is correct
*without ever stating what the function is supposed to do*. Undecidable from the input — a human
expert scores at chance too. SWE-bench ships the originating GitHub issue in `problem_statement`
and it simply wasn't being passed, though a real reviewer always has it.

Same model, same 60 cases, issue text added: **50.0% → 65%, recall 30% → 80%, p ≈ 0.011.**

**A negative result feels rigorous and humble, which is exactly why it escapes the scrutiny a
positive one attracts.** "We measured carefully and it can't do it" reads as intellectual honesty
and therefore gets audited less than "look how well it did."

## The checklist (run BEFORE recording any negative capability finding)

0. **Is the task ANSWERABLE from the input you supply?** Could a competent human, given exactly
   this input and nothing more, succeed? If not, you are measuring task validity, not capability.
   Check what context the real-world version of this task carries — and whether you withheld it.


1. **Dump one raw response.** Not the parsed result — the actual payload. Check every field
   (`content`, `reasoning_content`, `finish_reason`). An empty string is a plumbing symptom
   until proven otherwise.
2. **State what your metric literally measures**, in one sentence, without the word you want it
   to mean. "Precision" that only looks at clean inputs is not precision. If the sentence does
   not match the claim, the metric is the owner.
3. **Enumerate the configuration LAYERS**, then check each. Config is rarely one place: recipe
   vs request, server-side vs client-side, env vs file vs CLI flag. Auditing one layer and
   generalising is failure #4.
4. **Look up the contract; do not probe it by trial.** Reading docs (Context7, the project's own
   `docs/`) costs seconds. Guessing costs a broken config: probing whether `flm_args` accepts
   `--temp` failed the load AND still persisted the invalid flag via `save_options`, leaving a
   model that would fail every subsequent load.
5. **Inspect the failures of a STRONG subject.** If a known-good model also "fails" your cases,
   the cases are suspect. This found an ambiguous benchmark case containing two defects, where
   naming either one was correct but only one was scored.
6. **Widen n before drawing an architectural conclusion.** n=8 was enough to be confidently
   wrong with a validated-looking table; n=22 refuted it.

## The strongest signal: agreement

**Every one of the four errors above was the reading that AGREED with a prior expectation.**

- #1 matched a research claim that Q1_0 collapses formatting.
- #2 matched a prediction I had stated before the run.
- #4 matched the narrative I was already building about config gaps.

Confirmation feels like validation and functions like anaesthesia. **A result that agrees with
what you expected has earned MORE scrutiny, not less** — it is the condition under which a
broken apparatus goes unexamined, because nothing feels wrong.

Corollary: when an external source predicts a failure and you then observe that failure, you
have two hypotheses (the source is right; your apparatus is broken in a way that mimics it),
not one. Cite the source only after excluding the apparatus.

## Wording discipline

Until owners #2–4 are excluded, write findings as apparatus-relative:

- ❌ "Bonsai-27B collapses at Q1_0."
- ✅ "Bonsai-27B returned empty content on all 8 cases via this harness — owner not yet determined."

The second costs four words and cannot become a false permanent fact.

## Verification

Applying this checklist in-session converted a "3.54 GB model is broken" finding into
"3.54 GB model is best-in-class, beating a 120B frontier model on the same cases" — and
retracted a cascade architecture that had already been written into a skill and a vault
decision.

## References

- `gemma4-thinking-mode-output` — the specific empty-`content` plumbing failure (owner #2)
- `local-model-capability-benchmark` — negative controls, paired controls, effective context
- Context7 `/lemonade-sdk/lemonade` — the contract to READ instead of probe
