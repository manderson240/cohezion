"""Discriminating tests for measure_gguf_sizes (item 136, 2026-06-07).

Extends item 135 (which populated size_gb only for the 2 locally-cached models) with the
NON-FABRICATED source for the rest: the actual on-disk GGUF file size. A model with no local
GGUF is ABSENT from the result (never guessed), and mmproj projector files are excluded.

Discriminating: an impl that fabricates a size for an uncached model would include "NoSuch" in
the result → test_absent_when_no_gguf fails. An impl that matches mmproj as the model weights
would mis-size → test_mmproj_excluded fails. Sparse files give exact, fast, deterministic sizes.
"""

from __future__ import annotations

import os

from cohezion.inference.model_size_measurer import measure_gguf_sizes


_GIB = 1024**3


def _sparse(path: str, gib: float) -> None:
    with open(path, "wb") as f:
        f.truncate(int(gib * _GIB))


def test_measures_matching_gguf(tmp_path) -> None:
    _sparse(str(tmp_path / "gemma-4-E4B-it-Q4_K_M.gguf"), 4.6)
    out = measure_gguf_sizes(["Gemma-4-E4B-it-GGUF"], search_dirs=[str(tmp_path)])
    assert out["Gemma-4-E4B-it-GGUF"] == 4.6


def test_absent_when_no_gguf(tmp_path) -> None:
    # only an E4B file present; a different model must be ABSENT (not guessed)
    _sparse(str(tmp_path / "gemma-4-E4B-it-Q4_K_M.gguf"), 4.6)
    out = measure_gguf_sizes(["NoSuchModel-70B-GGUF"], search_dirs=[str(tmp_path)])
    assert "NoSuchModel-70B-GGUF" not in out


def test_mmproj_excluded(tmp_path) -> None:
    # a vision model's mmproj projector must NOT be taken as the model weights
    _sparse(str(tmp_path / "mmproj-F16.gguf"), 0.7)
    _sparse(str(tmp_path / "LFM2.5-VL-1.6B-Extract-Q4_K_M.gguf"), 1.2)
    out = measure_gguf_sizes(["LFM2.5-VL-1.6B-Extract-GGUF"], search_dirs=[str(tmp_path)])
    assert out["LFM2.5-VL-1.6B-Extract-GGUF"] == 1.2


def test_e2b_does_not_false_match_e4b(tmp_path) -> None:
    # discriminating: e2b must not match the e4b file (distinct models)
    _sparse(str(tmp_path / "gemma-4-E4B-it-Q4_K_M.gguf"), 4.6)
    out = measure_gguf_sizes(["Gemma-4-E2B-it-GGUF"], search_dirs=[str(tmp_path)])
    assert "Gemma-4-E2B-it-GGUF" not in out


def test_empty(tmp_path) -> None:
    assert measure_gguf_sizes([], search_dirs=[str(tmp_path)]) == {}
    # search dir with no gguf
    os.makedirs(str(tmp_path / "empty"), exist_ok=True)
    assert measure_gguf_sizes(["X-GGUF"], search_dirs=[str(tmp_path / "empty")]) == {}
