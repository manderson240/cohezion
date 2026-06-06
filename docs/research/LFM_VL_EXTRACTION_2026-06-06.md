---
title: "LFM2.5-VL-1.6B-Extract — registration done, mmproj proof = honest NULL"
created: 2026-06-06
owner: "/loop self-improvement (item 4)"
verdict: "REGISTERED as EXTRACTION/VISION specialist (verified_working=False). mmproj proof NOT run (model not downloaded) → honest NULL → sidecar branch of the falsifiable check. Real proof spun out as item 18."
---

# LFM2.5-VL extraction specialist — status

## What item 4 asked
Register `LiquidAI/LFM2.5-VL-1.6B-Extract-GGUF` as the `EXTRACTION`/`VISION` specialist and
**prove** lemonade `--mmproj` (else a `llama-mtmd` sidecar). Falsifiable check:
`for_task(EXTRACTION)` returns it; a 10-image set ≥ a big-VLM baseline at lower VRAM —
**OR honest NULL → sidecar**.

## Done now (additive, deterministic)
- `ModelEntry("LFM2.5-VL-1.6B-Extract-GGUF", lane=IGPU_ROCWMMA, task_affinity={EXTRACTION, VISION},
  priority=25, verified_working=False)` in `inference/registry.py`. `for_task(EXTRACTION)` went
  from `[]` → `[LFM…]`. 4 discriminating tests (incl. a PIN that `verified_working is False`, so a
  premature flip-to-verified without the proof fails).
- Two pin-actual tests updated honestly (EXTRACTION/VISION now populated; the still-empty
  FIM/FUNCTION_CALL/RERANK/OCR_DOC and the OCR_DOC→router fallback still covered).

## NOT done — the empirical proof is honest NULL
The model is **not downloaded** and not served; lemonade `--mmproj` support is **unproven**.
Running a 10-image extraction comparison now would be fabrication. So `verified_working=False`
and the proof is the **NULL → sidecar** branch of the check, spun out as **item 18**:

1. `lemonade pull LiquidAI/LFM2.5-VL-1.6B-Extract-GGUF` (Q4_0 ~696 MB; F16 ~2.34 GB; mmproj-…-F16.gguf).
2. Load the vision projector: try lemonade `--mmproj`; if unsupported → `llama-mtmd` sidecar.
3. 10-image image→YAML extraction set, temp=0, vs a big-VLM baseline; record field-accuracy + VRAM.
4. On pass → `registry.mark_verified("LFM2.5-VL-1.6B-Extract-GGUF")` (flips the pinned test green-for-verified).

## Surfaced for human consideration (NOT done this tick)
Registering LFM as the sole EXTRACTION specialist means `get_best_for_task("extract …")` now returns
it even though `verified_working=False` and it isn't loaded — downstream dispatch is fail-soft
(liveness probe → fallback), but a **`verified_working` routing gate** (skip unverified specialists
when no verified alternative exists) is a *separate behavior change* worth considering. Flagged, not
silently built. Note: 10/14 existing registry entries are also `verified_working=False` (presumed
working but never `mark_verified`'d), so such a gate must be designed carefully, not blanket-applied.

## License
`lfm1.0` — verify commercial terms before any production/commercial use.
