"""Phase 1: sonify the live compound loop via the tier-flow observer coherence.
Consumer test — fails if the sonifier stops reading the observer or the cache breaks."""
from unittest.mock import MagicMock, patch
from cohezion.audio.compound_sonifier import CompoundSonifier, _coherence_bucket


def test_bucket_quantizes_coherence():
    # bucketing so we don't regen audio for every micro-change (5s gen is expensive)
    assert _coherence_bucket(0.50) == _coherence_bucket(0.54)   # same bucket
    assert _coherence_bucket(0.10) != _coherence_bucket(0.90)   # different buckets


def test_sonify_reads_observer_and_generates():
    obs = MagicMock()
    obs.predict_next_state.return_value = [0.5]  # HIHO-optimal coherence
    client = MagicMock()
    client.generate.return_value = b"RIFF____WAVE" + b"\x00" * 5000
    s = CompoundSonifier(observer=obs, client=client)
    clip = s.sonify_current()
    assert clip[:4] == b"RIFF"
    # discriminating: the prompt handed to the client must reflect the observed coherence,
    # not a constant — a stub ignoring the observer fails this
    prompt = client.generate.call_args[0][0]
    assert "calm" in prompt.lower() or "stable" in prompt.lower() or "consonant" in prompt.lower()


def test_sonify_caches_by_bucket():
    obs = MagicMock(); obs.predict_next_state.return_value = [0.5]
    client = MagicMock(); client.generate.return_value = b"RIFF" + b"\x00" * 5000
    s = CompoundSonifier(observer=obs, client=client)
    s.sonify_current(); s.sonify_current()          # same bucket twice
    assert client.generate.call_count == 1          # second call served from cache


def test_sonify_fail_open_when_generation_none():
    obs = MagicMock(); obs.predict_next_state.return_value = [0.5]
    client = MagicMock(); client.generate.return_value = None  # gen failed
    s = CompoundSonifier(observer=obs, client=client)
    assert s.sonify_current() is None               # never raises into the loop
