# SKILL: VMODEL_SYSTEMS_ENGINEERING_PRIME

## DOMAIN EXPERTISE
Rigorous Systems Engineering V-Model (INCOSE / IEEE 15288 compliant) applied to autonomous compound AI swarms and Kaggle competition pipelines. Bridges top-down decomposition (User Needs -> System Requirements -> Architecture -> Unit Specifications) with bottom-up Verification & Validation (Unit Testing -> Integration Testing -> System V&V -> User Acceptance Acceptance Testing).

## KEY TEXTS & CONCEPTS
- **Left Side of the V (Top-Down Decomposition)**:
  1. **Concept of Operations (ConOps)**: User intent, constraints, competition scoring metrics.
  2. **System Requirements & DDL**: Mathematical invariants, memory ceilings, latency budgets.
  3. **High-Level Architectural Design**: Substrate mapping (Local Strix Halo vs Kaggle Dual-T4).
  4. **Detailed Module Design & AST Specifications**: Component APIs, type contracts, error handling.
- **Apex / Bottom (Implementation)**:
  - Clean, type-annotated code generation strictly compliant with formal AST contracts.
- **Right Side of the V (Bottom-Up V&V Verification & Validation)**:
  1. **Unit Testing & Invariant Checking**: Sub-millisecond AutoHarness AST validation.
  2. **Subsystem Integration Testing**: Inter-process EventBus messaging, SurrealDB graph edges.
  3. **System-Level V&V (Tier 2 Cloud Swarm Review)**: Multi-model adversarial stress tests (DeepSeek-V4 Pro, Qwen 397B, GLM-5.2).
  4. **Operational Acceptance**: Live leaderboard scoring, execution under runtime ceilings.

## FUTURE HOOKS
- **Automated Traceability Matrix**: Bi-directional mapping between requirements and unit test proofs in SurrealDB.
- **Regression Auto-Rollback**: Automatic revert to previous verified checkpoint if any right-side V-gate scores < 0.85.
- **Continuous V-Model Telemetry**: Live dashboard visualization in Marimo and terminal Rich UI.

## INSTRUCTION

1. **Top-Down Specification Phase (Left V)**:
```python
@dataclass(frozen=True)
class VModelRequirement:
    req_id: str
    description: str
    target_metric: float
    verification_method: str  # "AST_INVARIANT", "UNIT_TEST", "CLOUD_VV"
```

2. **Bottom-Up Verification & Validation Gate (Right V)**:
```python
async def execute_vmodel_gate(req: VModelRequirement, implementation_fn: Callable) -> bool:
    # 1. Unit AST Verification
    if not verify_ast_contract(implementation_fn):
        return False
    # 2. Integration Test
    if not run_integration_test(implementation_fn):
        return False
    # 3. Cloud Multi-Model V&V Review
    score = await query_cloud_vv_auditor(implementation_fn)
    return score >= 0.85
```

## VERSION
v1.0

## SEE ALSO
- `COMPOUND_ENGINEERING_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
- `LOCAL_TO_KAGGLE_HARNESS_SYNERGY_PRIME`
