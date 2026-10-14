# SKILL: KAGGLE_GRANDMASTER_ASCENT_PRIME

## DOMAIN EXPERTISE
Autonomous Kaggle Leaderboard Climbing, Active Unexpired Competition Management, Systems Engineering V-Model Verification Gates (VG-1 to VG-4), AutoHarness Invariant Guarding, and Kolmogorov Probability Calibration.

## KEY TEXTS & CONCEPTS
* **Active Competition Filtering Mandate**: Strictly filter all leaderboard audits, submission pipelines, and status reports to currently ACTIVE, unexpired competitions:
  - ARC Prize 2026: ARC-AGI-2 (31.81%, Top 9.5%), ARC-AGI-3 (0.07 / 0.26), Paper Track.
  - RSNA Knee Abnormality Detection (0.939 / 0.943, Top 5.6% Silver Medal, ends Oct 22).
  - Enveda CASMI26 Molecule ID from Mass Spectra (0.328, ends Dec 14).
  - EXPLICIT FILTER: Never report on closed/expired competitions (Biohub 3D Cell Tracking final locked at 0.95387; Kaggriculture closed Sept 30). Exclude Pokémon TCG per mandate.
* **Systems Engineering V-Model Verification Gates**:
  - VG-1 (AST & Schema Gate): Candidate code must pass syntax parsing (`ast.parse()`) and Pydantic schema validation.
  - VG-2 (Local Head-to-Head Gate): 100% win-rate or positive validation margin on offline holdout seeds.
  - VG-3 (Resource Bounds Gate): Strict compliance with remote limits (<9h execution, <20 GB RAM, offline container compatibility).
  - VG-4 (Invariant Proof Gate): AutoHarness proof (D4 dihedral group invariance, Euler characteristic $\chi$, Kolmogorov monotonicity $P(\text{Abnormal}) \ge \max_k P_k$).
* **Probabilistic Calibration vs Rank Blending**:
  - Avoid destructive rank averaging on log-loss metrics (transforms calibrated posteriors into uniform distributions, inflating expected loss to 1.000 nats).
  - Apply finding-specific Dirichlet / Isotonic calibration with Ledoit-Wolf shrinkage prior ($\alpha \in [0.03, 0.05]$).
* **SurrealDB Compound DataMesh Tracking**:
  - Continuous synchronization of submission IDs, public scores, and medal thresholds into SurrealDB (`competition`, `submission_record`, `learning` tables).

## INSTRUCTION

1. **Audit Active Unexpired Competitions**:
   Query active competition states filtering out completed tracks:
   ```bash
   python -c "
   import json
   from pathlib import Path
   data = json.loads(Path('scripts/kaggle/sentinel_status.json').read_text())
   active = {k: v for k, v in data.items() if k in ['arc_agi_2', 'arc_agi_3', 'rsna_knee', 'casmi26']}
   for k, v in active.items():
       print(f'{k}: Score={v.get(\"score\")} SubID={v.get(\"latest_submission_id\")}')
   "
   ```

2. **Run V-Model Verification Gates**:
   Execute deterministic invariant checks before triggering any submission:
   ```python
   from cohezion.arc.submission_guard import verify_arc_invariants
   from cohezion.medical.calibration import enforce_kolmogorov_monotonicity

   # ARC verification
   assert verify_arc_invariants(test_grid)["passed"] is True, "VG-4 Failed on ARC"

   # RSNA verification
   calibrated_probs = enforce_kolmogorov_monotonicity(raw_probs)
   assert calibrated_probs["abnormal"] >= max(calibrated_probs["conditions"].values()), "VG-4 Failed on RSNA"
   ```

3. **Package Submission Kernels with Offline Dependencies**:
   Ensure notebooks are completely self-contained with internet disabled (`"enable_internet": false`) in `kernel-metadata.json`.

4. **Submit via Automated Watcher**:
   Trigger submission only after all gates pass:
   ```bash
   python scripts/kaggle/auto_submit_watcher.py --competition arc-prize-2026
   ```

5. **Log Retrospective Learnings to DataMesh**:
   Persist submission records and error boundaries to SurrealDB and the Obsidian Vault.

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_PRIME.md`
- `AMD_GAIA_ORCHESTRATION_PRIME.md`
- `SURREALDB_DATAMESH_PRIME.md`
- `VMODEL_SYSTEMS_ENGINEERING_PRIME.md`
