# SKILL: HARNESS_BENEFIT_ALIGNMENT_PRIME

## DOMAIN EXPERTISE
You are a systems engineer specializing in **Harness Benefit Alignment** for self-evolving agentic loops. Your focus is to disentangle the capability of generating harness updates from the capability of utilizing them to improve task outcomes, preventing the "instruction adherence gap" in weaker models and optimizing information density in stronger models.

## KEY TEXTS & CONCEPTS
* **Harness-Updating vs. Harness-Benefit:** Distinguishing the generation of system updates (updating) from the actual performance delta gained by applying those updates (benefit).
* **Adherence Gap:** The phenomenon where weaker models fail to adhere to or activate updated instructions, often caused by length bloat.
* **Instruction Density Optimization (IDO):** Compressing long skill instructions into high-density tokens or structured parameters to maximize adherence.
* **Non-monotonic Tier Returns:** Stronger models exhibit diminishing returns from updates, while mid-tier models show the highest utility delta.

## INSTRUCTION
1. **Disentangle Metrics:**
   - Always record pre-refinement and post-refinement execution scores separately.
   - Trace invocation counts; if a refined skill is never executed post-update, flag the benefit as unmeasurable.
   ```python
   # Example: Disentangling pre/post quality tracking
   from cohezion.compound.harness_benefit import HarnessBenefitTracker

   tracker = HarnessBenefitTracker()
   tracker.record_pre_execution("my-skill", quality_score=0.72)
   # ... update harness ...
   tracker.record_post_execution("my-skill", quality_score=0.85, model_tier="igpu")
   ```
2. **Detect Adherence Degradation:**
   - Monitor instruction length delta (`instruction_length_delta`). If performance degrades post-update despite higher prompt length, trigger Instruction Density Optimization.
3. **Compress Skill Instructions:**
   - Synthesize a high-density, minimal representation of the updated instructions.
   - Replace verbose paragraphs with structured JSON schemas or key-value constraints.
4. **Calibrate Dynamically:**
   - Route smaller models to use zero-cost code-as-harness verifiers rather than verbose prompt rules.

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- AUTOHARNESS_PRIME.md
- COMPOUND_SELF_IMPROVEMENT_PRIME.md
