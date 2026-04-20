# SKILL: HALLUCINATION_RESOLVER_PRIME

## DOMAIN EXPERTISE
Expert system for detecting, analyzing, and mitigating AI hallucinations by grounding agentic discourse in "Truth Anchors" derived from live system diagnostics and historical failure modes (Hallucination Tracker).

## KEY TEXTS & CONCEPTS
- **Truth Anchors**: Verified facts about the system (CPU, GPU, RAM, Paths) that serve as a non-negotiable foundation for agent reasoning.
- **Spec-Attribution Bias**: The tendency for AI to attribute idealized or templated specifications (e.g., from documentation or memory) to a live system without verification.
- **Grounding**: The process of validating a claim against a deterministic data source (sysfs, lscpu, native APIs).
- **Adversarial Review**: Proactively hunting for unsupported assumptions in its own or other agents' outputs.

## INSTRUCTION
1. **Identify the Claim**: Extract technical specifications, hardware names, or system paths from the proposed text/output.
2. **Consult Ground Truth**: Invoke the `resolve_claims` tool or `resolver.py` to compare the claim against live diagnostics.
3. **Check the Tracker**: Cross-reference with `HALLUCINATION_TRACKER.md` to see if this is a recurring failure mode.
4. **Precipitate Truth Anchors**: If a discrepancy is found, inject a [TRUTH ANCHORS] block into the context and force a revision.

### Example Claim Verification
```python
from cohezion.reliability.resolver import HallucinationResolver

resolver = HallucinationResolver()
report = resolver.resolve_claims("Optimized for Framework 16 AMD GPU")

if report["is_hallucinating"]:
    print(f"Hallucination Detected: {report['issues']}")
    print(f"Correct Context: {resolver.get_truth_anchors()}")
```

## VERSION
v1.0

## SEE ALSO
- REPO_HYGIENE_PRIME
- PERSISTENT_QUALITY_PRIME
- COHEZION_BRIDGE_PRIME
