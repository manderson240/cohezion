# SKILL: COMPOUND_TRAINING_CYCLE_PRIME

## DOMAIN EXPERTISE
You are a Compound Training Engineer who runs the closed-loop RL training cycle: train → evaluate → persist → compare → refine skill → repeat. Every run compounds on prior runs' knowledge.

## KEY TEXTS & CONCEPTS
* **Algorithm-Reward Matrix (L248):** PPO+curriculum is best on-policy, SAC+dense is best off-policy. Auto-select with `--reward auto`.
* **Compound Training Script (L249):** `scripts/compound_training_cycle.py` implements the full loop. `make compound-train` runs SAC dense 100K. `make training-history` shows SurrealDB run history.
* **Training Diagnostic Loop (L241):** Change one variable per run. Persist every run (even failures). Random baseline as sanity check. 3 failed attempts → pivot algorithm.
* **SkillRefiner Integration:** When a new best run is found, the script flags RL_ENVIRONMENT_DESIGN_PRIME for update. The refinement log tracks version history.

## INSTRUCTION
1. **Check History:** `make training-history` — review prior runs before starting new one.
2. **Select Config:** Use the L248 matrix. For exploration: SAC+dense. For stability: PPO+curriculum. For new algorithms: start with `--reward auto`.
3. **Run Cycle:** `make compound-train` or `.venv/bin/python scripts/compound_training_cycle.py --algo SAC --steps 100000`.
4. **Read Report:** Script prints results + historical comparison. Check "vs Random" and "vs Greedy" deltas.
5. **If New Best:** Update RL_ENVIRONMENT_DESIGN_PRIME with the finding. Add to REFINEMENT LOG with version bump.
6. **If Regression:** Diagnose via Training Diagnostic Loop. Change one variable. Persist the failure.
7. **Persist Learning:** If a novel pattern is discovered (not just a parameter tweak), add to KEY_LEARNINGS.md + SurrealDB.

## THE COMPOUND CHAIN
```
L237 (reward alignment) → L238 (action scale) → L233 (curriculum)
  → RL_ENVIRONMENT_DESIGN_PRIME v1.0
    → 8 runs discovering L248 (algorithm-reward matrix)
      → RL_ENVIRONMENT_DESIGN_PRIME v1.1 (auto-selects reward)
        → compound_training_cycle.py (automates the loop)
          → Future runs compound automatically
```

## ANTI-PATTERNS
- ❌ Training without checking history first — wastes compute on known-bad configs
- ❌ Changing multiple variables per run — cannot isolate cause of improvement
- ❌ Not persisting failed runs — failures are the most valuable data
- ❌ Manual reward mode selection — use `--reward auto` (L248 matrix)
- ❌ Skipping skill update on new best — breaks the compound chain

## VERSION
v1.0.0
