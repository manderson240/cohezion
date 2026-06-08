"""Item 92: abstraction_quality() neuron-deposit abstraction-quality audit (TDD red→green).

arXiv 2606.04703 (ExpInternalization): abstract principle-level experience beats
instance-specific detail for stable self-evolution.

Each test fails a plausible wrong implementation:
  - one that flags ANY digit → test_incidental_number_not_flagged
  - one that misses file paths → test_absolute_path_flagged
  - one that misses SHAs → test_sha_flagged
  - one that misses timestamps → test_iso_timestamp_flagged
  - one that flags clean principles → test_abstract_principle_not_flagged
  - one that crashes on empty → test_empty_neurons_returns_empty
"""

from __future__ import annotations

from cohezion.governance.abstraction_quality import abstraction_quality


# ---------------------------------------------------------------------------
# T_path: absolute Unix/Windows path → instance_specific=True
# Fails: an impl that ignores path patterns.
# ---------------------------------------------------------------------------


def test_absolute_path_flagged() -> None:
    """A neuron whose content contains an absolute path is instance-specific."""
    neurons = [
        {
            "name": "n-path-1",
            "content": "Apply the fix at /home/mike/dev/cohezion/src/cohezion/compound/executor.py line 231",
        }
    ]
    result = abstraction_quality(neurons)
    assert len(result) == 1
    flag = result[0]
    assert flag.name == "n-path-1"
    assert flag.instance_specific, "absolute path must flag as instance_specific"


# ---------------------------------------------------------------------------
# T_sha: SHA/hex commit hash → instance_specific=True
# Fails: an impl that ignores hex patterns.
# ---------------------------------------------------------------------------


def test_sha_flagged() -> None:
    """A neuron containing a 40-char SHA or long hex hash is instance-specific."""
    neurons = [
        {
            "name": "n-sha-1",
            "content": "This was fixed in a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9",
        }
    ]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-sha-1"), None)
    assert flag is not None
    assert flag.instance_specific, "40-char SHA must flag as instance_specific"


# ---------------------------------------------------------------------------
# T_timestamp: ISO 8601 timestamp → instance_specific=True
# Fails: an impl that only checks paths and SHAs.
# ---------------------------------------------------------------------------


def test_iso_timestamp_flagged() -> None:
    """A neuron with an ISO timestamp is instance-specific (captures a specific event)."""
    neurons = [
        {
            "name": "n-ts-1",
            "content": "Session 2026-06-07T14:23:45 showed FLUME VAE collapse at beta=0.02",
        }
    ]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-ts-1"), None)
    assert flag is not None
    assert flag.instance_specific, "ISO timestamp must flag as instance_specific"


# ---------------------------------------------------------------------------
# T_uuid: UUID → instance_specific=True
# ---------------------------------------------------------------------------


def test_uuid_flagged() -> None:
    """A neuron with a UUID string is instance-specific (session/record ID)."""
    neurons = [
        {
            "name": "n-uuid-1",
            "content": "Retry from session 550e8400-e29b-41d4-a716-446655440000 using the same params",
        }
    ]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-uuid-1"), None)
    assert flag is not None
    assert flag.instance_specific, "UUID must flag as instance_specific"


# ---------------------------------------------------------------------------
# T_abstract: clean principle neuron → instance_specific=False
# Fails: an impl that always flags or flags on general words.
# ---------------------------------------------------------------------------


def test_abstract_principle_not_flagged() -> None:
    """A neuron of abstracted procedural principle is NOT instance-specific."""
    neurons = [
        {
            "name": "n-principle-1",
            "content": (
                "Use a 2-layer decoder with hidden dimension 4096 to prevent KL collapse. "
                "The cyclic beta schedule must keep the amplitude below 0.01 to stay within "
                "the HIHO equilibrium band. Monitor the KL term across training steps."
            ),
        }
    ]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-principle-1"), None)
    assert flag is not None
    assert not flag.instance_specific, (
        "A principle neuron with only numbers like '2', '4096', '0.01' must NOT be flagged — "
        "kills the naive 'any digit → instance' impl"
    )


# ---------------------------------------------------------------------------
# T_incidental_number: one incidental number below density threshold → NOT flagged
# Fails: a naive 'any digit → instance_specific' impl.
# ---------------------------------------------------------------------------


def test_incidental_number_not_flagged() -> None:
    """A single incidental number in a principled neuron is NOT instance-specific.

    This is the PRIMARY discriminating test: any impl that uses 'contains a digit'
    as the instance-specific signal will fail this test.
    """
    neurons = [
        {
            "name": "n-borderline-1",
            "content": "The optimal learning rate for the HIHO phase is approximately 3 orders of magnitude below the instability threshold",
        }
    ]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-borderline-1"), None)
    assert flag is not None
    assert not flag.instance_specific, (
        "One incidental number ('3 orders of magnitude') must NOT flag as instance_specific"
    )


# ---------------------------------------------------------------------------
# T_empty: empty neuron list → empty result
# Fails: an impl that crashes on empty input.
# ---------------------------------------------------------------------------


def test_empty_neurons_returns_empty() -> None:
    """No neurons → empty AbstractionFlag list, no crash."""
    result = abstraction_quality([])
    assert result == []


# ---------------------------------------------------------------------------
# T_mixed: mixed store — some flagged, some clean
# Fails: an impl that flags ALL or flags NONE.
# ---------------------------------------------------------------------------


def test_mixed_store_partial_flags() -> None:
    """A store with both instance-specific and abstract neurons flags only the former."""
    neurons = [
        {"name": "n-clean", "content": "Always validate Pydantic boundaries before processing"},
        {
            "name": "n-dirty",
            "content": "Found the bug at src/cohezion/cache/semantic_cache.py line 87",
        },
    ]
    result = abstraction_quality(neurons)
    by_name = {f.name: f for f in result}
    assert "n-clean" in by_name
    assert "n-dirty" in by_name
    assert not by_name["n-clean"].instance_specific, "clean principle must not be flagged"
    assert by_name["n-dirty"].instance_specific, "path+line-ref must be flagged"


# ---------------------------------------------------------------------------
# T_no_content: neuron missing 'content' key → not flagged (safe default)
# Fails: an impl that crashes on missing keys.
# ---------------------------------------------------------------------------


def test_neuron_missing_content_skipped() -> None:
    """A neuron dict without a 'content' key is treated as empty content (not flagged)."""
    neurons = [{"name": "n-no-content"}]
    result = abstraction_quality(neurons)
    flag = next((f for f in result if f.name == "n-no-content"), None)
    assert flag is not None
    assert not flag.instance_specific, (
        "missing content → no volatile tokens → not instance_specific"
    )
