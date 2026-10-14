# SKILL: MONADIC_LOCAL_MARKOV_PLANNING_PRIME

## DOMAIN EXPERTISE
Monadic local Markov planning, state-action penalty routing, SplitMix64 Zobrist state hashing for cycle evasion, and strict prevention of global constraint pollution. Incorporates the critical post-mortem from ARC-AGI-3 (where global color banning caused agent deadlocks) and ARC-AGI-2 (where unverified secondary heuristics destroyed neural outputs).

## KEY TEXTS & CONCEPTS
- **Local State-Action Penalties vs Global Pollution**: Never ban an environmental property, token, or color globally upon collision or error. Instead, attach a local penalty strictly to the $(s, a)$ transition.
- **SplitMix64 Zobrist Hashing**: 64-bit fast deterministic hashing of local spatial coordinates and visit histories to detect loops with $O(1)$ memory lookup.
- **Step Budget Economy**: Preserve quadratic and non-linear score economics ($(H_l/A_l)^2$) by terminating unpromising search branches within tight step ceilings (e.g., 45 steps).
- **Monotonic Improvement Invariant**: Primary high-confidence plans (`attempt_1`) must NEVER be overwritten by speculative secondary heuristics. Secondary plans are placed into `attempt_2` or used only when primary outputs are dummy/invalid.

## INSTRUCTION
1. Initialize local Markov planner:
   ```python
   from cohezion.planning import LocalMarkovPlanner, LocalState, PlanM

   planner = LocalMarkovPlanner(step_budget=45, wall_bump_penalty=100.0)
   state = LocalState.create((start_x, start_y))
   ```
2. Step with local penalties and cycle evasion:
   ```python
   # Record visit and detect cycles
   planner.record_visit(state)
   if planner.is_cycle(state, threshold=3):
       # Backtrack or explore alternate affordance
       pass

   # On collision with boundary:
   planner.penalize_local_action(state, action="UP")
   # Notice: 'UP' is only penalized at this specific state coordinate, NOT globally!
   ```
3. Compose plans monadically while enforcing monotonic improvement:
   ```python
   ensemble_plan = PlanM.monotonic_ensemble(
       primary_plan=neural_agent_plan,
       secondary_plan=symbolic_dsl_plan,
       is_dummy_fn=lambda out: out is None or out == [[0]],
   )
   result = ensemble_plan.run(initial_state)
   ```

## VERSION
v1.0

## SEE ALSO
- `src/cohezion/planning/local_markov.py`
- `src/cohezion/planning/monad.py`
- `tests/planning/test_local_markov_planning.py`
- `src/cohezion/skills/ARC3_GO_EXPLORE_AFFORDANCE_PRIME.md`
