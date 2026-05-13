"""Tests for ARC grid processing pipeline.

V-Model:
- Unit verification: encode/decode roundtrip, validate_grid, batch ops
- System validation: verify_pipeline_sanity property-based checks
- Integration: full workflow with synthetic ARC task
"""

import json
from pathlib import Path

import pytest

from cohezion.arc.codec import grids_equal
from cohezion.arc.grid_pipeline import (
    batch_decode,
    batch_encode,
    decode_from_latent,
    decode_grid,
    encode_grid,
    grid_hash,
    grid_summary,
    validate_grid,
    verify_pipeline_sanity,
    verify_roundtrip,
)


# ---------------------------------------------------------------------------
# Unit Verification
# ---------------------------------------------------------------------------


class TestValidateGrid:
    def test_valid_grid(self):
        g = [[1, 2], [3, 4]]
        ok, msg = validate_grid(g)
        assert ok, msg

    def test_empty_grid(self):
        ok, msg = validate_grid([])
        assert not ok
        assert "empty" in msg.lower()

    def test_oversized(self):
        g = [[0] * 31 for _ in range(31)]
        ok, msg = validate_grid(g)
        assert not ok
        assert "max" in msg.lower()

    def test_non_rectangular(self):
        g = [[1, 2], [3]]
        ok, msg = validate_grid(g)
        assert not ok
        assert "mismatch" in msg.lower()

    def test_invalid_color(self):
        g = [[1, 10], [3, 4]]
        ok, msg = validate_grid(g)
        assert not ok
        assert "out of range" in msg.lower()
        g2 = [[1, -1], [3, 4]]
        ok2, _msg2 = validate_grid(g2)
        assert not ok2


class TestEncodeDecode:
    def test_roundtrip_identity(self):
        g = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        enc = encode_grid(g)
        dec = decode_grid(enc)
        assert grids_equal(g, dec)

    def test_batch_roundtrip(self):
        grids = [
            [[1]],
            [[0, 0], [0, 0]],
            [[i % 10 for i in range(10)] for _ in range(10)],
        ]
        encs = batch_encode(grids)
        decs = batch_decode(encs)
        assert len(grids) == len(decs)
        for a, b in zip(grids, decs):
            assert grids_equal(a, b)

    def test_grid_hash_deterministic(self):
        g = [[1, 2], [3, 4]]
        h1 = grid_hash(g)
        h2 = grid_hash(g)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_grid_summary(self):
        g = [[1, 1], [2, 2]]
        s = grid_summary(g)
        assert s["shape"] == (2, 2)
        assert s["unique_colors"] == [1, 2]
        assert s["color_count"] == 2
        assert len(s["hash"]) == 16


class TestVerifyRoundtrip:
    def test_verify_pass(self):
        ok, msg = verify_roundtrip([[5, 5], [5, 5]])
        assert ok
        assert "OK" in msg

    def test_verify_sanity(self):
        result = verify_pipeline_sanity()
        assert result["all_ok"]
        for key, val in result["results"].items():
            assert val["ok"], f"{key} failed: {val['msg']}"


class TestDecodeFromLatent:
    @pytest.mark.skipif(encode_grid is None, reason="numpy missing")
    def test_latent_reconstruction_shape(self):
        g = [[1, 2], [3, 4]]
        enc = encode_grid(g)
        latent = enc["latent_256"]
        if latent is not None:
            dec = decode_from_latent(latent, (2, 2))
            assert isinstance(dec, list)
            assert len(dec) == 2
            assert len(dec[0]) == 2


# ---------------------------------------------------------------------------
# System Validation: Synthetic ARC Task
# ---------------------------------------------------------------------------


class TestSyntheticTask:
    def test_encode_task(self):
        from cohezion.arc.codec import encode_task

        task = {
            "train": [
                {"input": [[0, 1], [1, 0]], "output": [[1, 0], [0, 1]]},
            ],
            "test": [
                {"input": [[1, 1], [0, 0]]},
            ],
        }
        out = encode_task(task)
        assert "train" in out
        assert "test" in out
        assert out["train"][0].get("_encoded_input") is not None

    def test_pattern_extract_invert(self):
        from cohezion.arc.pattern_extractor import PatternExtractor

        # 3x3 task where invert is the ONLY single-op solution (asymmetric grids)
        task = {
            "train": [
                {
                    "input": [[0, 0, 0], [0, 1, 0], [1, 0, 1]],
                    "output": [[1, 1, 1], [1, 0, 1], [0, 1, 0]],
                },
                {
                    "input": [[1, 1, 0], [0, 0, 1], [1, 0, 0]],
                    "output": [[0, 0, 1], [1, 1, 0], [0, 1, 1]],
                },
            ],
            "test": [{"input": [[0, 0, 1], [1, 0, 0]]}],
        }
        extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
        rules = extractor.extract(task)
        assert len(rules) > 0
        assert any("invert" in r.name for r in rules)

    def test_submission_structure(self):
        import tempfile

        from cohezion.arc.submission import SubmissionBuilder

        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            out_dir = Path(td)
            # Minimal challenge file
            (data_dir / "arc-agi_test_challenges.json").write_text(
                json.dumps(
                    {
                        "t1": {
                            "train": [{"input": [[1]], "output": [[1]]}],
                            "test": [{"input": [[1]]}],
                        }
                    }
                )
            )
            builder = SubmissionBuilder(
                data_dir=data_dir,
                output_path=out_dir / "submission.json",
                max_depth=1,
                budget=100,
            )
            sub = builder.build(verbose=False)
            assert "t1" in sub
            assert "attempt_1" in sub["t1"][0]
            assert "attempt_2" in sub["t1"][0]
