"""F5/F6: a backend that loads but fails at INFERENCE time (OOM, "Already borrowed") is the
explicit unavailable state for that call: encode_or_none -> None, encode -> TextLatentUnavailable.
Never a hash vector, never a raw RuntimeError into unguarded callers, and never a dead encoder."""

from __future__ import annotations

import logging

import numpy as np
import pytest

from cohezion.flume.canonical_latent import CanonicalTextLatent, TextLatentUnavailable
from tests.flume import test_latent_boundary_and_thread_guards as boundary
from tests.flume import test_latent_window_and_degrade as window
from tests.flume.test_canonical_latent_concurrency import real_loader  # noqa: F401


OOM = "DefaultCPUAllocator: can't allocate memory"


class _Flaky:
    """Backend that loads fine; ``exc`` is raised while ``broken`` is set."""

    def __init__(self, exc: BaseException):
        self.exc, self.broken, self.calls = exc, True, 0
        self.max_tokens = 1000

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        if self.broken:
            raise self.exc
        v = np.zeros(384, dtype=np.float32)
        v[len(text) % 384] = 1.0
        return v

    def count_tokens(self, text: str) -> int:
        if self.broken:
            raise self.exc
        return len(text.split())


def _flaky(exc: BaseException | None = None):
    backend = _Flaky(exc or RuntimeError(OOM))
    return CanonicalTextLatent(lambda: backend), backend


def _broken_encoder() -> CanonicalTextLatent:
    return _flaky()[0]


@pytest.mark.parametrize(
    "exc", [RuntimeError(OOM), MemoryError(), OSError("mmap"), ValueError("v")]
)
def test_inference_failure_is_none_counted_and_logged(exc, caplog):
    enc, _ = _flaky(exc)
    with caplog.at_level(logging.WARNING, logger="cohezion.flume.canonical_latent"):
        assert enc.encode_or_none("hello") is None
    assert enc.skipped_calls == 1
    assert "failed at inference" in caplog.text


def test_encode_raises_the_explicit_unavailable_error_not_a_vector():
    enc, _ = _flaky()
    with pytest.raises(TextLatentUnavailable) as ei:
        enc.encode("hello")
    assert OOM in str(ei.value) and isinstance(ei.value.__cause__, RuntimeError)


def test_inference_failure_does_not_mark_the_encoder_dead():
    enc, backend = _flaky()
    assert enc.encode_or_none("hello") is None
    backend.broken = False
    got = enc.encode_or_none("hello")  # next call, no RETRY_AFTER_S wait
    assert got is not None and got.shape == (256,)
    assert enc.is_available()


def test_strict_window_token_count_failure_is_none():
    enc, backend = _flaky()
    backend.broken = False
    assert enc.encode_or_none("one two", strict_window=True) is not None
    backend.broken = True
    assert enc.encode_or_none("one two", strict_window=True) is None


def test_programming_errors_still_propagate():
    enc, _ = _flaky(TypeError("bug in the backend"))
    with pytest.raises(TypeError):
        enc.encode_or_none("hello")


@pytest.mark.parametrize("bad", [None, 123, ["a b", "c d"], b"bytes", {"k": "v"}])
def test_non_str_input_is_none_from_encode_or_none_and_typeerror_from_encode(bad):
    enc, backend = _flaky()
    backend.broken = False
    assert enc.encode_or_none(bad) is None
    assert enc.encode_or_none(bad, strict_window=True) is None
    with pytest.raises(TypeError):
        enc.encode(bad)
    assert backend.calls == 0  # rejected before reaching the backend
    assert enc._proj is None  # the shared projection was not rebuilt for a batch shape


class _SurrogateIntolerant(_Flaky):
    """Like the real HF fast tokenizer: a lone surrogate is a TypeError at the Rust boundary."""

    def __call__(self, text: str) -> np.ndarray:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise TypeError("TextEncodeInput must be Union[...]") from exc
        return super().__call__(text)

    def count_tokens(self, text: str) -> int:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise TypeError("TextEncodeInput must be Union[...]") from exc
        return len(text.split())


LONE_SURROGATE = "bad \ud83d text"


@pytest.mark.parametrize("strict", [False, True])
def test_lone_surrogate_is_none_from_encode_or_none_never_raises(strict):
    backend = _SurrogateIntolerant(RuntimeError(OOM))
    backend.broken = False
    enc = CanonicalTextLatent(lambda: backend)
    assert enc.encode_or_none(LONE_SURROGATE, strict_window=strict) is None
    assert enc.encode_or_none("fine text", strict_window=strict) is not None
    with pytest.raises(TextLatentUnavailable):
        enc.encode(LONE_SURROGATE)


def test_backend_typeerror_on_valid_text_still_propagates_with_strict_window():
    """The surrogate fix must not widen the catch: a TypeError for ordinary text is still a bug."""
    backend = _SurrogateIntolerant(RuntimeError(OOM))
    backend.broken = False

    def bad_count(text: str) -> int:
        raise TypeError("bug")

    backend.count_tokens = bad_count
    enc = CanonicalTextLatent(lambda: backend)
    with pytest.raises(TypeError):
        enc.encode_or_none("fine text", strict_window=True)


def test_list_input_cannot_rebuild_the_shared_projection():
    enc, backend = _flaky()
    backend.broken = False
    before = enc.encode("abc")
    proj = enc._proj
    with pytest.raises(TypeError):
        enc.encode(["a b", "c d"])
    assert enc._proj is proj and np.allclose(enc.encode("abc"), before)


# The unguarded callers named in review, driven by a backend that fails at inference time.
# Their bodies are the existing unavailable-latent tests with `_dead` swapped for the flaky one.
@pytest.mark.parametrize(
    "name",
    [
        "test_journey_logger_complete_survives_unavailable_latent",
        "test_observable_action_proposal_survives_unavailable_latent",
        "test_skill_tracker_event_survives_unavailable_latent",
    ],
)
def test_platform_callers_survive_inference_failure(monkeypatch, name):
    monkeypatch.setattr(boundary, "_dead", _broken_encoder)
    getattr(boundary, name)()


def test_journey_logger_start_survives_inference_failure(monkeypatch):
    monkeypatch.setattr(window, "_dead", _broken_encoder)
    window.test_journey_logger_survives_unavailable_latent()


def test_cache_text_to_embedding_is_none_on_inference_failure(monkeypatch):
    from cohezion.cache import semantic_cache as sc

    monkeypatch.setattr(sc, "get_encoder", _broken_encoder)
    assert sc.SemanticCache._text_to_embedding("anything") is None


def test_journey_tracker_text_to_latent_raises_on_transient_inference_failure():
    """A transient failure while the encoder IS available must not become an untagged hash
    latent (cosine ~ -0.02 to the real one); it raises, as at base. Changed from "degrades to
    its fallback" on the checker's finding N1. No encoder at all still uses the hash path."""
    from cohezion.compound.journey_tracker import JourneyTracker

    jt = JourneyTracker(seed=7)
    jt._flume_encoder = _broken_encoder()
    assert jt._flume_encoder.is_available() is True  # precondition: failure is transient
    with pytest.raises(TextLatentUnavailable):
        jt.text_to_latent("some task")
    jt._flume_encoder = None  # unavailable from the start: pre-existing hash path stays
    assert jt.text_to_latent("some task").shape == (2048,)
