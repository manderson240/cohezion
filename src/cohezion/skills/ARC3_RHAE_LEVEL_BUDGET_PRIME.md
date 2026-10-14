# SKILL: ARC3_RHAE_LEVEL_BUDGET_PRIME

## DOMAIN EXPERTISE
You are an autonomous interactive game reasoning engineer and reinforcement search specialist for discrete puzzle environments (ARC-AGI-3). You specialize in Relative Human Action Efficiency (RHAE) scoring optimization, quadratic marginal penalty avoidance, 64-bit SplitMix64 Zobrist state hashing, loop cycle evasion, and fail-fast level budgeting.

## KEY TEXTS & CONCEPTS
- **RHAE Quadratic Scoring Formula**:
  $$\text{RHAE}(l) = \min\left(1.0, \left(\frac{N_{\text{human}}}{N_{\text{AI}}}\right)^2\right)$$
  for each completed level $l$. Uncompleted levels score exactly 0.0.
- **Marginal Step Utility Decay (Theorem RHAE Step Decay)**:
  $$\frac{\partial}{\partial N_{\text{AI}}} \text{RHAE} = -2 \frac{N_{\text{human}}^2}{N_{\text{AI}}^3}$$
  Because utility decays cubically with actions taken, wandering beyond $2 \times N_{\text{human}}$ steps collapses the score to $<0.25$, while $5 \times N_{\text{human}}$ collapses it to $<0.04$.
- **LevelBudget Hard Truncation Invariant**:
  Exploration must be capped at $N_{\text{AI}} \le 35$ steps per level (or $1.8 \times N_{\text{human}}$). Failing fast on unsolvable or deadlocked levels preserves the global time budget (8.5 hours) for easily solvable levels, yielding higher aggregate scorecard integrals.
- **State-Hash Liveness Watchdog**:
  Tracking visited states via $O(1)$ 64-bit Zobrist XOR hashing. Detecting 1-cycle collisions (wall bumping), 2-cycle oscillations ($s_A \leftrightarrow s_B$), and 3-to-6 cycle orbit traps breaks loops early before burning actions.
- **Scorecard Closing Invariant**:
  Wrapping arcade execution in an un-bypassable `try...finally` block guarantees `arcade.close_scorecard(card_id)` is always called, ensuring valid submission parquets even upon timeouts.

## INSTRUCTION

1. **Implement Vectorized 64-Bit SplitMix64 Zobrist Hash**:
   ```python
   import numpy as np

   # Precomputed 64-bit Zobrist table across discrete grid colors
   RNG = np.random.default_rng(20261002)
   ZOBRIST_TABLE = RNG.integers(0, (1 << 62) - 1, size=(64, 64, 10), dtype=np.int64)

   def hash_frame(frame: np.ndarray) -> int:
       h, w = frame.shape
       colors = np.clip(frame, 0, 9)
       r_idx = np.arange(h)[:, None]
       c_idx = np.arange(w)
       return int(np.bitwise_xor.reduce(ZOBRIST_TABLE[:h, :w, :][r_idx, c_idx, colors].ravel()))
   ```

2. **Implement RHAE-Bounded Level Search Loop with Liveness Watchdog**:
   ```python
   def play_environment(env, agent, max_steps=35, max_loops=4):
       obs = env.reset()
       step = 0
       while obs and obs.state not in (GameState.WIN, GameState.GAME_OVER) and step < max_steps:
           # Liveness Watchdog: Breakout if trapped in consecutive cycles
           if getattr(agent, "consecutive_loops", 0) >= max_loops:
               break
           action, data = agent.choose_action(obs)
           obs = env.step(action, data=data)
           step += 1
       return obs, step
   ```

3. **Enforce the Scorecard Closing Invariant**:
   ```python
   card_id = arcade.create_scorecard()
   try:
       for env_info in envs:
           env = arcade.make(env_info.game_id, scorecard_id=card_id)
           play_environment(env, agent, max_steps=35)
   finally:
       # Guaranteed execution ensures scorecard is finalized cleanly
       sc = arcade.close_scorecard(card_id)
   ```

## VERSION
v0.1

## SEE ALSO
- `KAGGLE_COMPETITIVE_EVALUATION_PRIME`
- `ARC3_GO_EXPLORE_AFFORDANCE_PRIME`
