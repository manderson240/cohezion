# SKILL: AGENTIC_DELIVERY_PRIMITIVES_PRIME

## DOMAIN EXPERTISE
Expertise in structuring and governing end-to-end agentic software delivery systems across four durable stages—Plan, Build, Verify, and Observe—connected by a central Purpose-Driven Knowledge Layer. Rather than treating code generation as a black box, this methodology implements explicit boundary contracts, immutable output artifacts, discrete verification evidence, and materialized memory views that prevent past defects and feed continual learning cycles.

## KEY TEXTS & CONCEPTS
- **Microsoft Command Line SDLC Primitives**: Decomposing agentic delivery into Plan, Build, Verify, and Observe with explicit human and agent jobs to be done.
- **Stage Boundary Contracts**: Formal preconditions and postconditions validating artifacts before allowing progression to adjacent lifecycle stages.
- **Purpose-Driven Materialized Memory**: Avoiding raw context bloat by maintaining indexed views for past mistake avoidance, component constraint retrieval, and utility benchmarking.
- **Engineering Evaluation Test**: Measuring memory utility via $\Delta \text{Efficiency} = \frac{\text{Success}_{\text{with\_mem}} - \text{Success}_{\text{without\_mem}}}{1 + \text{Overhead}}$.
- **Continual Learning Loopback**: Converting verification proof traces and production telemetry into Prioritized Experience Replay buffers for Elastic Weight Consolidation (SLEEP).

## INSTRUCTION

1. **Formulate the Plan Artifact**:
   Define unambiguous intent, hard system constraints, and acceptance criteria. Query the knowledge layer for historical mistakes before writing code.
   ```python
   from cohezion.compound.agentic_delivery_primitives import AgenticSoftwareDeliveryPipeline

   pipeline = AgenticSoftwareDeliveryPipeline()
   plan_art = pipeline.execute_plan(
       component="VaultAdapter",
       intent="Support batch cancellations safely",
       constraints=["Checks-Effects-Interactions", "TokenBalanceHistory sync"],
       acceptance_criteria=["Zero desync across cancelled orders"],
   )
   ```

2. **Execute Build with Contextual Rationale**:
   Translate goals into code within an isolated git worktree, documenting trade-offs and rationale.
   ```python
   def build_adapter(plan_content):
       return {
           "diff_or_code": "function cancelCall(...) { ... }",
           "rationale": "Applied state synchronization before transfer",
           "modified_files": ["VaultAdapter.sol"],
           "evidence": ["Compiled clean with solc 0.8.29"],
       }


   build_art = pipeline.execute_build(plan_art, build_adapter)
   ```

3. **Verify with Formal Invariant Proofs**:
   Validate candidate implementation against acceptance criteria using deterministic verifiers (AutoHarness). Produce discrete, auditable proof traces.
   ```python
   def verify_adapter(build_content):
       # Run AutoHarness invariant checks
       return True, ["Proof: TokenBalanceHistory updated before call"], []


   verify_art = pipeline.execute_verify(build_art, verify_adapter)
   ```

4. **Observe Production Signals and Synthesize Learnings**:
   Monitor runtime metrics, triage anomalies, and export experiences to the SLEEP continual learning consolidation daemon.
   ```python
   def observe_runtime(verify_content):
       return {
           "metrics": {"invocations": 1000, "failures": 0},
           "anomalies": [],
           "synthesized_learnings": ["Sync-before-transfer pattern holds under load"],
       }


   observe_art = pipeline.execute_observe(verify_art, observe_runtime)
   sleep_exp = pipeline.export_sleep_experience(observe_art)
   ```

## VERSION
v0.1

## SEE ALSO
- SLEEP_CONTINUAL_LEARNING_PRIME
- COMPOUND_ENGINEERING_PRIME
- FORMAL_VERIFICATION_PRIME
