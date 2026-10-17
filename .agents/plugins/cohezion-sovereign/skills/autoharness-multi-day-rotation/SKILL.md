---
name: autoharness-multi-day-rotation
metadata:
  version: "1.0.0"
description: >-
  Champion Anchor Protocol and idempotent multi-day slot rotation for continuous autonomous Kaggle allotment saturation.
---

# SKILL: AUTOHARNESS_MULTI_DAY_ROTATION_PRIME

## DOMAIN EXPERTISE
Expertise in operationalizing the **Champion Anchor Protocol** and idempotent multi-day allotment management across competitive ML tracks. Guarantees non-regressive daily exploration by pinning Slot 1 of every calendar day to the highest-scoring verified state-of-the-art configuration (the Champion), allocating Slots 2 through 5 to orthogonal invariant hypotheses (the Challengers), and restoring notebooks from canonical baseline snapshots (`*.canonical_base.ipynb`) before every submission to prevent multi-version frankenstein corruption.

## KEY TEXTS & CONCEPTS
- **The Champion Anchor Protocol**: When daily submission quotas reset (at 00:00:05 UTC), Slot 1 must ALWAYS dispatch the proven SOTA champion configuration. Never revert to stale historical baselines on new calendar days.
- **Pristine Canonical Snapshot Invariant**: Notebooks and scripts must never be mutated cumulatively in-place across consecutive slots. A pristine `*.canonical_base.ipynb` must be restored before applying each slot's specific invariant patch.
- **Fail-Closed Patch Verification**: Assembly scripts must raise `RuntimeError` immediately if targeted code blocks or replacement anchors are absent, preventing corrupted notebooks from dispatching.
- **Orthogonal Challenger Hypothesis Lattice**: Slots 2 through 5 explore distinct first-principles invariant hypotheses:
  - Slot 2: Conservative calibrated extension of the Champion.
  - Slot 3: Domain-specific structural/anatomical invariant constraint.
  - Slot 4: Alternative mathematical metric/transport formulation.
  - Slot 5: Extreme parameter space or multi-model consensus boundary test.
- **Single-Slot Sequential Progression**: For tracks with 1 submission/day (ARC-2, ARC-3, Gemma-4), advance the active slot index sequentially across days $(s_{t+1} = (s_t \pmod N) + 1)$ without resetting to Slot 1.

## INSTRUCTION
1. Enforce Pristine Baseline Snapshot Reset:
   ```python
   import shutil
   from pathlib import Path

   def reset_to_canonical_base(notebook_path: Path) -> Path:
       base_path = notebook_path.parent / (notebook_path.stem + ".canonical_base.ipynb")
       if not base_path.exists():
           base_path = notebook_path.with_suffix(".canonical_base.ipynb")
       if base_path.exists():
           shutil.copyfile(base_path, notebook_path)
           print(f"Restored {notebook_path.name} from {base_path.name}")
       return notebook_path
   ```

2. Verify Fail-Closed Patch Application:
   ```python
   def apply_idempotent_patch(notebook_json: dict, target_str: str, replacement_str: str, cell_idx: int) -> None:
       src = "".join(notebook_json["cells"][cell_idx]["source"])
       if target_str not in src:
           raise RuntimeError(f"Anchor '{target_str[:40]}...' not found in cell {cell_idx}!")
       updated_src = src.replace(target_str, replacement_str)
       notebook_json["cells"][cell_idx]["source"] = [l + "\n" for l in updated_src.splitlines()]
   ```

3. Pin Slot 1 to Proven Champion:
   ```python
   def get_daily_slot_config(comp_slug: str, slot_num: int, portfolio: dict) -> dict:
       slots = portfolio[comp_slug]["slots"]
       # Slot 1 is permanently anchored to proven Champion
       if slot_num == 1:
           assert "champion" in slots[1].get("name", "").lower() or "sota" in slots[1].get("name", "").lower()
       return slots[slot_num]
   ```

## VERSION
v1.0

## SEE ALSO
- `kaggle-daily-allotment-saturation`
- `lukyanenko-invariant-engineering`
- `harness2-recursive-harnessing`
