"""ModelEntry.size_gb population from MEASURED GGUF sizes (item 135, 2026-06-07).

Activates the item-132 per-candidate headroom gate in production. Non-fabrication is the whole
point: sizes come from the actual on-disk GGUF file size (a hard measurement), NOT param×quant
guesses. Only the two locally-cached models have a measured figure this tick; everything else
stays None (gate skipped — safe) until its GGUF is measured.

Discriminating: an impl that invents sizes for uncached models would set a non-None size on, e.g.,
a cloud entry or an unmeasured local one — these tests assert those stay None.
"""

from __future__ import annotations

from cohezion.inference.registry import get_registry


def test_measured_models_have_their_gguf_size() -> None:
    reg = get_registry()
    # measured: gemma-4-E2B-it-Q4_K_M.gguf = 2.9 GB, gemma-4-E4B-it-Q4_K_M.gguf = 4.6 GB
    assert reg.models["Gemma-4-E2B-it-GGUF"].size_gb == 2.9
    assert reg.models["Gemma-4-E4B-it-GGUF"].size_gb == 4.6


def test_unmeasured_and_cloud_models_stay_none() -> None:
    reg = get_registry()
    # cloud lanes never carry a local resident size
    assert reg.models["claude-haiku-4-5"].size_gb is None
    # an un-cached local model is NOT guessed — stays None until measured
    assert reg.models["deepseek-r1:70b"].size_gb is None
