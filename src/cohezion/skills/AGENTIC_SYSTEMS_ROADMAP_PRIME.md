# SKILL: AGENTIC_SYSTEMS_ROADMAP_PRIME

## DOMAIN EXPERTISE
Architecting, orchestrating, and operationally hardening production multi-agent AI systems across four hierarchical tiers: single cognitive reasoning loops with strict validation, stateful tri-partite memory and cyclic graph flows, typed swarm handoff contracts with debate-critique conflict resolution, and trajectory-level execution observability with circuit breakers.

## KEY TEXTS & CONCEPTS
- **The Failure-Ordering Axiom**: Agentic systems fail hierarchically:
  1. *Level 1 Failure*: Schema invalidity & malformed tool calls.
  2. *Level 2 Failure*: Context drift & uncheckpointed state loss.
  3. *Level 3 Failure*: Unstructured text drift across agent handoffs.
  4. *Level 4 Failure*: Runaway reasoning loops, token exhaustion & unmonitored trajectories.
- **Tri-Partite Memory Hierarchy**:
  - *Working Context*: Active token window (fast, bounded, ephemeral).
  - *Episodic Memory*: Vector/embedding recall of past interaction episodes in SurrealDB.
  - *Semantic Memory*: Structured knowledge graph and entity-relationship models in Markdown MOCs and SurrealDB.
- **Typed Swarm Handoff Contracts**: Replacing unstructured markdown communication between agents with Pydantic contracts (`TaskHandoffContract`) carrying explicit acceptance criteria, input payloads, recursion depth caps, and token expenditure ceilings.
- **Debate-and-Critique Topology**: Pairing generation agents with dedicated adversarial red-team critics, arbitrated via deterministic conflict resolution strategies.
- **Trajectory-Level Evaluation**: Scoring the efficiency and correctness of the full execution graph path rather than merely inspecting terminal output.

## INSTRUCTION

1. **Enforce Level 1 Schema Discipline**:
   - Always validate tool outputs and candidate code with deterministic verifiers (AST compilation and Pydantic schemas) before passing them downstream.
   ```python
   from cohezion.agi.autoharness_policy import AutoHarnessPolicy
   harness = AutoHarnessPolicy()
   is_valid, msg = harness.verify_ast(code)
   ```

2. **Govern Inter-Agent Handoffs via Typed Contracts (Level 3)**:
   - When delegating across swarm agents, instantiate a `TaskHandoffContract` rather than emitting raw conversational text.
   ```python
   from cohezion.swarm.handoff_contract import TaskHandoffContract, AgentRole
   contract = TaskHandoffContract(
       contract_id="handoff_001",
       parent_task_id="task_arc_01",
       source_agent="supervisor",
       source_role=AgentRole.SUPERVISOR,
       target_agent="proposer_npu",
       target_role=AgentRole.PROPOSER,
       task_intent="Synthesize D4 dihedral transformation",
       input_payload={"grid": grid},
       acceptance_criteria=["D4 equivariant", "Passes AST"],
       max_recursion_depth=5,
       max_token_ceiling=8192,
   )
   ```

3. **Check Circuit Breaker Ceilings at Every Graph Node (Level 4)**:
   - In any cyclical or multi-step agent flow, query `contract.can_proceed()` before invoking model generation. If limits are reached, trip the circuit breaker and halt immediately.
   ```python
   can_proceed, reason = contract.can_proceed()
   if not can_proceed:
       # Trip circuit breaker and return fallback state
       contract.status = TaskStatus.CIRCUIT_BROKEN
       return fallback_action(reason)
   ```

4. **Arbitrate Divergences via Structured Conflict Resolution**:
   - When a critic agent rejects a proposer's output, route through `SwarmConflictResolver` using debate-and-critique or adversarial re-querying rather than infinite retry loops.

5. **Log Trajectory-Level Tracing into SurrealDB**:
   - Record every intermediate step with token counts, execution latency, and state hash digests for post-mortem trajectory debugging.

## VERSION
v0.1

## SEE ALSO
- `PROPRIOCEPTIVE_CYBERNETICS_PRIME.md`
- `DETERMINISTIC_IDEMPOTENCE_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `JOURNEY_TRACKING_PRIME.md`
