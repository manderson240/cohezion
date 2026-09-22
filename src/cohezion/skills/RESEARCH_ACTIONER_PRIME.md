---
name: research-actioner
description: "Work-queue actioner lane. Deterministically routes APPLY research cards to implement or experiment, runs one local-inference compound cycle per card, and records a PROPOSED artifact. Describes current behaviour of cohezion.actioner.engine only."
---

# SKILL: RESEARCH_ACTIONER_PRIME

The skill the compound loop runs as `skill_name="research-actioner"`
(`cohezion.actioner.engine.action_item`, driven by `scripts/actioner.py`).
Everything below describes what the code does today, not what it should do.

## DOMAIN EXPERTISE
Draining the research work queue: cards with `relevance=APPLY` in status
`reviewed` or `approved`, oldest first, up to 50 attempted per batch.

## TRIAGE (deterministic, no model involved)
Rules are applied in this order; the first match wins.
1. **RC1 short-circuit**: a card with `type=improvement` routes to `implement`
   without looking at its text (it was already triaged upstream).
2. **Route B, experiment**: title + abstract + description + domain matches
   `train, training, fine-tun, sft, rlhf, dpo, distill, curriculum, eval,
   benchmark, skill-methodology, reward model, dataset`. Checked BEFORE Route A,
   so a card matching both (e.g. "Training a 4B Coding Agent") is an `experiment`.
3. **Route A, implement**: the same text matches `tool, toolchain, config, prompt,
   prompt-pattern, agent, inference, serving, quantiz, cache, caching, rag,
   retrieval, routing, orchestrat, mcp, sandbox, scheduler`.
4. **No match**: route `none`. The card is left untouched in `reviewed` (never
   dropped, never LLM-classified) and recorded in the triage-miss ledger so later
   runs skip it until the rules or the card content change.

Every pattern is wrapped in word boundaries on both sides, so a stem only matches
as a whole word: `quantiz` does not match "quantized" and `fine-tun` does not
match "fine-tuning".

## INSTRUCTION (per routed card)
1. Build the proposal prompt from the card (title, abstract or description, url,
   domain) and ask local inference ($0, :13305 router) for STRICT JSON with exactly
   two keys: `"proposal"` (2-3 sentences: what to do in our stack) and
   `"falsifiable_step"` (one concrete measurable check that could FAIL). No
   markdown fences.
2. Route `experiment` asks for a falsifiable experiment design; route `implement`
   asks for an implementation note. The two JSON keys are the same for both.
3. If the reply is not parseable JSON, the raw text becomes the proposal and the
   falsifiable step is recorded as "(unstructured output)".
4. Append the entry to `~/.cohezion/ada_proposals.jsonl` with `verdict: PROPOSED`.
   The verdict is always PROPOSED: the actioner never claims a result.
5. Route `experiment` also writes a vault note under `experiments/proposed/`.
6. Only after the artifact write succeeds, PATCH the card to `status=actioned`
   with `action_route` set to the route. The card's `notes` are never overwritten.

## FAILURE BEHAVIOUR
- A failed compound cycle raises; the card stays `reviewed` for retry and the
  batch continues with the next card.
- The executor's input guardrails see the task description
  `Action research item <id>: <title>`. Titles such as "... Bypasses Gym Booking
  Limit ..." have been blocked there as an injection pattern. Any failure whose
  message contains "Input blocked by guardrails" or "Potential injection pattern"
  marks the card `rejected` with the reason in its notes. That includes the
  resource guard ("Resources constrained: CPU=..., Memory=..."), so a card can be
  rejected permanently for a transient load spike.
- Artifacts are de-duplicated by card id, so a crash between the artifact write
  and the PATCH makes the re-run a safe no-op.

## VERSION
v1.0 (2026-09-22, documents engine triage revision 2)

## SEE ALSO
- src/cohezion/actioner/engine.py
- src/cohezion/compound/golden_fixtures/research-actioner.json
