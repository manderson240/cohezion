"""F8: the calibration and diagnostic scripts must not feed a None embedding to np.dot."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from pathlib import Path

import numpy as np
import pytest

from cohezion.flume.canonical_latent import TextLatentUnavailable


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, SCRIPTS / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _NoLatentCache:
    """Cache with one L2 entry whose encoder reports the latent unavailable."""

    def __init__(self, *a, **k):
        self._l2_matrix = np.ones((1, 4), dtype=np.float32)
        self._l2_keys = ["k"]
        self.l2_cache = {}

    def _text_to_embedding(self, text):
        return None


def test_calibration_refuses_to_sweep_without_a_latent(monkeypatch):
    mod = _load("calibration/run_cache_calibration.py")
    monkeypatch.setattr(mod, "SemanticCache", _NoLatentCache)
    with pytest.raises(TextLatentUnavailable):
        asyncio.run(
            mod.evaluate_cache_threshold(
                [{"prompt": "p" * 60, "response": "r"}], {"similarity_threshold": 0.8}
            )
        )


def test_semantic_discrimination_diagnostic_reports_and_returns_without_a_latent(
    monkeypatch, caplog
):
    mod = _load("phase2_vae_diagnostic.py")
    monkeypatch.setattr(mod, "SemanticCache", _NoLatentCache)
    monkeypatch.setattr(mod, "get_encoder", lambda: None)
    with caplog.at_level(logging.ERROR):
        mod.diagnostic_semantic_discrimination()
    assert "text latent unavailable" in caplog.text


class _NoEncoder:
    """The real cold state: an encoder object whose latent is unavailable."""

    def encode_or_none(self, text, strict_window=False):
        return None


def _cold_calibration(monkeypatch, tmp_path):
    """Load the real script with the REAL SemanticCache but no encoder (nothing faked in the cache)."""
    import cohezion.cache.semantic_cache as sc

    monkeypatch.setattr(sc, "get_encoder", lambda: _NoEncoder())
    monkeypatch.setenv("HOME", str(tmp_path))
    return _load("calibration/run_cache_calibration.py")


SAMPLES = [{"prompt": f"prompt number {i} " * 6, "response": f"answer {i}"} for i in range(4)]


def test_calibration_evaluate_refuses_when_l2_stays_empty_cold(monkeypatch, tmp_path):
    mod = _cold_calibration(monkeypatch, tmp_path)
    with pytest.raises(TextLatentUnavailable):
        asyncio.run(mod.evaluate_cache_threshold(SAMPLES, {"similarity_threshold": 0.4}))


def test_calibration_main_cold_saves_no_profile(monkeypatch, tmp_path):
    """Real main(), real SemanticCache, no encoder: must exit nonzero and save nothing."""
    mod = _cold_calibration(monkeypatch, tmp_path)
    saved = []
    monkeypatch.setattr(mod, "load_local_logs", lambda min_len=0: iter(SAMPLES))
    monkeypatch.setattr(mod, "save_calibration_profile", lambda *a, **k: saved.append(a))
    real_sweep = mod.run_parameter_sweep

    swept = []

    async def sweep_no_ram_gate(samples, fn, grid, min_ram_mb=0):
        swept.append(1)
        return await real_sweep(samples, fn, grid, min_ram_mb=0)

    monkeypatch.setattr(mod, "run_parameter_sweep", sweep_no_ram_gate)
    with pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert saved == []
    assert swept == []  # refused BEFORE the sweep, not merely after it found nothing


def test_calibration_main_never_saves_when_no_threshold_is_valid(monkeypatch, tmp_path):
    """Probe passes but every candidate errors (e.g. L2 stays empty): still nothing is saved."""
    mod = _cold_calibration(monkeypatch, tmp_path)
    saved = []
    monkeypatch.setattr(mod.SemanticCache, "_text_to_embedding", staticmethod(lambda t: object()))
    monkeypatch.setattr(mod, "load_local_logs", lambda min_len=0: iter(SAMPLES))
    monkeypatch.setattr(mod, "save_calibration_profile", lambda *a, **k: saved.append(a))
    real_sweep = mod.run_parameter_sweep

    async def sweep_no_ram_gate(samples, fn, grid, min_ram_mb=0):
        return await real_sweep(samples, fn, grid, min_ram_mb=0)

    async def zero_hits(samples, cand):
        return {
            "total_lookups": 4,
            "hits": 0,
            "valid_hits": 0,
            "collisions": 0,
            "hit_rate_pct": 0.0,
            "collision_rate_pct": 0.0,
            "valid_hit_rate_pct": 0.0,
        }

    monkeypatch.setattr(mod, "run_parameter_sweep", sweep_no_ram_gate)
    monkeypatch.setattr(mod, "evaluate_cache_threshold", zero_hits)
    with pytest.raises(SystemExit):
        asyncio.run(mod.main())
    assert saved == []


# --- over-window queries are skipped and counted, an encoder outage still fails ---------------


class _WindowedEncoder:
    """Healthy deterministic encoder; any text containing LONG is over the window (None, as the
    real encode_or_none(strict_window=True) reports it). ``down`` flips it to a real outage."""

    def __init__(self):
        self.down = False

    def is_available(self):
        return not self.down

    def exceeds_token_limit(self, text):
        return "LONG" in text

    def encode_or_none(self, text, strict_window=False):
        import hashlib

        from cohezion.flume.canonical_latent import LATENT_DIM

        if self.down or "LONG" in text or "FLAKY" in text:
            return None
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "little")
        v = np.random.default_rng(seed).standard_normal(LATENT_DIM).astype(np.float32)
        return v / np.linalg.norm(v)


def _healthy_main(monkeypatch, tmp_path, samples, encoder=None):
    import cohezion.cache.semantic_cache as sc

    enc = encoder or _WindowedEncoder()
    monkeypatch.setattr(sc, "get_encoder", lambda: enc)
    monkeypatch.setenv("HOME", str(tmp_path))
    mod = _load("calibration/run_cache_calibration.py")
    saved = []
    monkeypatch.setattr(mod, "load_local_logs", lambda min_len=0: iter(samples))
    monkeypatch.setattr(mod, "save_calibration_profile", lambda *a, **k: saved.append(a))
    real_sweep = mod.run_parameter_sweep

    async def sweep_no_ram_gate(s, fn, grid, min_ram_mb=0):
        return await real_sweep(s, fn, grid, min_ram_mb=0)

    monkeypatch.setattr(mod, "run_parameter_sweep", sweep_no_ram_gate)
    return mod, enc, saved


def _dup_samples(n=4):
    out = []
    for i in range(n):
        p = f"distinct calibration prompt number {i} about topic {i * 7}"
        out += [{"prompt": p, "response": f"a{i}"}, {"prompt": p, "response": f"a{i}"}]
    return out


@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_over_window_prompt_is_skipped_counted_and_calibration_completes(
    monkeypatch, tmp_path, capsys, position
):
    samples = _dup_samples()
    long_one = {"prompt": "LONG " + "word " * 400, "response": "r"}
    idx = {"first": 0, "middle": len(samples) // 2, "last": len(samples)}[position]
    samples.insert(idx, long_one)
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, samples)
    asyncio.run(mod.main())  # must NOT sys.exit
    out = capsys.readouterr().out
    assert "Skipped 1 sample(s)" in out
    assert len(saved) == 1 and saved[0][0] == "semantic_cache"


def test_all_samples_over_window_fails_saying_so_and_saves_nothing(monkeypatch, tmp_path, caplog):
    samples = [{"prompt": f"LONG {i} " + "w " * 300, "response": "r"} for i in range(3)]
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, samples)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert "All samples were skipped" in caplog.text
    assert "encoder" not in caplog.text.lower().replace("encoder window", "")
    assert saved == []


def test_encoder_down_at_start_still_fails_and_saves_nothing(monkeypatch, tmp_path):
    enc = _WindowedEncoder()
    enc.down = True
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, _dup_samples(), encoder=enc)
    with pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert saved == []


def test_encoder_dying_mid_partition_is_an_outage_not_a_skip(monkeypatch, tmp_path, caplog):
    """The probe passes, then the encoder goes down: every later None is an outage."""
    samples = _dup_samples()
    enc = _WindowedEncoder()
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, samples, encoder=enc)
    real = enc.encode_or_none
    calls = []

    def dies_after_probe(text, strict_window=False):
        calls.append(1)
        if len(calls) > 3:
            enc.down = True
        return real(text, strict_window)

    enc.encode_or_none = dies_after_probe
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert "went down mid-run" in caplog.text  # reported as an outage, not as skipped samples
    assert saved == []


def test_failed_inference_on_a_short_prompt_is_not_a_skip(monkeypatch, tmp_path, caplog):
    """A transient failure returns None with the encoder still up: it must not read as a skip."""
    samples = [*_dup_samples(), {"prompt": "FLAKY short prompt", "response": "r"}]
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, samples)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert "inference failed" in caplog.text
    assert saved == []


def test_unencodable_prompt_is_skipped_without_asking_for_a_token_count(
    monkeypatch, tmp_path, capsys
):
    samples = [*_dup_samples(), {"prompt": "lone surrogate \ud800 prompt", "response": "r"}]
    enc = _WindowedEncoder()
    real = enc.encode_or_none
    enc.encode_or_none = lambda text, strict_window=False: (
        None if "\ud800" in text else real(text, strict_window)
    )
    # The real exceeds_token_limit raises TypeError on a surrogate.
    enc.exceeds_token_limit = lambda text: (_ for _ in ()).throw(TypeError("surrogate"))
    mod, _, saved = _healthy_main(monkeypatch, tmp_path, samples, encoder=enc)
    asyncio.run(mod.main())
    assert "Skipped 1 sample(s)" in capsys.readouterr().out
    assert len(saved) == 1


def test_encoder_dying_during_the_sweep_saves_nothing(monkeypatch, tmp_path, caplog):
    """The filter passes, then the encoder dies: rows that did finish must not pick a threshold."""
    mod, enc, saved = _healthy_main(monkeypatch, tmp_path, _dup_samples())
    real_eval = mod.evaluate_cache_threshold

    async def dies_at_the_third_threshold(samples, candidate):
        if candidate["similarity_threshold"] >= 0.5:
            enc.down = True
        return await real_eval(samples, candidate)

    monkeypatch.setattr(mod, "evaluate_cache_threshold", dies_at_the_third_threshold)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert "threshold(s) errored" in caplog.text
    assert saved == []
