# SKILL: PHOENIX_REBIRTH_REPRODUCTION_PRIME

## DOMAIN EXPERTISE
Specification-Driven Disposable Code Resurrection, The Deletion Test ("Burn to Ashes"), AutoHarness AST Verification, and Deterministic Re-Synthesis from Formal Schemas, DDLs, and Contracts.

## KEY TEXTS & CONCEPTS
- **The Phoenix Architecture Principle** (Polvara, Veribaz, Goecke 2026): Code is transient and disposable ($S_{\text{spec}} \xrightarrow{\text{AutoHarness}} \text{Code}_{\text{new}}$). True permanent assets are formal specifications, DDL schemas, OpenAPI contracts, and test oracles.
- **The Deletion Test**: If a module accumulates entropy, bugs, or technical debt, delete the source code completely and re-synthesize it from its formal specification.
- **Machine-Readable DDL & Protocol Grounding**:
  - SurrealDB DDL schema definitions (`schemas/surrealdb/*.surql`).
  - Hardware aperture FleetLock invariants.
  - Python typing protocols and API boundaries (`src/cohezion/contracts.py`).
- **AutoHarness Zero-Cost Invariant Certification**: Verification contracts ($0\text{ ms}$ AST bytecode checks) that must pass before any regenerated code is accepted.

## INSTRUCTION

1. **Perform The Deletion Test on Failing Subsystems**:
   ```python
   from cohezion.agi.phoenix_architecture import PhoenixArchitectureEngine
   engine = PhoenixArchitectureEngine()
   result = engine.execute_deletion_and_rebirth(
       module_name="cohezion.subsystem.contract",
       specification_name="target_invariant_spec",
       failing_code=failing_source_code
   )
   assert result.verified_by_oracle is True, "Regenerated code failed AutoHarness policy"
   ```

2. **Ground Resurrection in Strict DDL and Typed Schemas**:
   Always reference the concrete machine-readable schema files under `schemas/` and `src/cohezion/contracts.py` rather than free-form natural language markdown.

3. **Verify Zero-Knowledge Safety Proofs**:
   Ensure every resurrected module generates a valid ZKFV proof ($\pi_{\text{safety}}$) validating all algebraic constraints.

## VERSION
v1.0.0

## SEE ALSO
- [AUTOHARNESS_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/AUTOHARNESS_PRIME.md)
- [SPINNING_PLATES_PROTOCOL_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SPINNING_PLATES_PROTOCOL_PRIME.md)
- [MULTI_PERSPECTIVE_REVIEW_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/MULTI_PERSPECTIVE_REVIEW_PRIME.md)
