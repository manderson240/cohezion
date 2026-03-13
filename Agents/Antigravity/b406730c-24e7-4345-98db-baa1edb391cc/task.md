---
type: antigravity-artifact
session_id: b406730c-24e7-4345-98db-baa1edb391cc
date: 2026-03-04
title: "Task"
aspect: doer
neural:
  activation: 0.5
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# Tsunami Simulator Crash Remediation

- [ ] Diagnosed system crash cause
  - [x] Identified `tsunami_simulator.py` synchronous runaway loop
  - [x] Drafted plan to inject `ResourceGuard` and explicit memory cleanup
- [ ] Implement Safety Guards
  - [ ] Integrate `ResourceGuard().wait_for_stability()` in main loop
  - [ ] Add `await asyncio.sleep(0.05)` yielding to the inner batch
  - [ ] Explicitly garbage collect `reps` and `entropies` arrays
- [ ] Verification
  - [ ] Execute `uv run scripts/drivers/tsunami_simulator.py` for 5 epochs
  - [ ] Verify CPU load remains < 75% without locking up the OS
  - [ ] Update `MISSION_JOURNAL.md` with crash remediation details
