# SKILL: MANIFOLD_INTEGRITY_PRIME

## DOMAIN EXPERTISE
Expert in enforcing high-dimensional physical constraints via static analysis of data artifacts. Specializes in ensuring 12D manifold integrity (x, y, z, time + 8 Branes) across all agent-generated data.

## KEY TEXTS & CONCEPTS
* **12D Physics State**: Mandatory physical grounding for every Cohezion artifact.
* **Coherence Check**: Static validation of artifact dimensions and data types.
* **Manifold Compilation**: Treating high-dimensional physics as a hard constraint in the build pipeline.

## INSTRUCTION
1. **Enforce 12D structure**: Every JSON artifact in `data/universe/` must contain a `physics_state` object with all 12 dimensions.
2. **Run Integrity Guards**: Run `make coherence-check` to verify the physical grounding of the codebase.
3. **Fail Fast**: Block commits that introduce dimensionally malformed artifacts.

## VERSION
v1.0 (Physical Law Enforcement)

## SEE ALSO
- MANIFOLD_PHYSICS_OPTIMIZATION_PRIME.md


## AUTO-REFINEMENT (Learning 269)
*   **Insight**: TDD-First for GPU Kernels — Local Verification Saves Remote Submissions (2026-04-07)
*   **Details**: Verified e8m0_unshuffle roundtrip, MFMA 32x32 output layout (every cell written once), and A/B tile loading coverage (1024+4096 bytes) using pure Python before any remote submission. This prevented wasting rate-limited submissions on known-broken code. Rule: for GPU kernels where you can't run locally, verify ALL data flow components that CAN be tested locally (index math, permutations, coverage) before submitting.

---

## Session 89: Repository Integrity & Health (2026-04-07)
*   **Date**: 2026-04-11
