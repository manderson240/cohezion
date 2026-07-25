"""HC1 — verify_chain() must detect tampering, not just self-consistency.

BUG (live-proven 2026-07-12, fixed 2026-07-25): verify_chain() validated each hash_chain entry
against its OWN stored prev_hash but never checked that entry[i].prev_hash == entry[i-1].chain_hash.
Deleting a middle row therefore left every survivor internally consistent and the chain still
verified True — the OLIF-mitigation audit trail gave FALSE integrity assurance.

These are DISCRIMINATING tests: each tamper case below PASSES verification under the old
(self-consistency-only) logic and must FAIL under the fixed logic. If someone reverts the linkage
or sequence-continuity check, these go red.
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

import pytest

from cohezion.compound.journey_tracker import JourneyTracker

GENESIS = "0" * 64


def _chain(n: int) -> list[dict]:
    """Build a genuinely valid chain of n entries, exactly as the write side does."""
    out, prev = [], GENESIS
    for i in range(n):
        payload_hash = hashlib.sha256(f"payload-{i}".encode()).hexdigest()
        chain_hash = hashlib.sha256(f"{prev}:{payload_hash}".encode()).hexdigest()
        out.append({
            "sequence": i, "prev_hash": prev,
            "payload_hash": payload_hash, "chain_hash": chain_hash,
        })
        prev = chain_hash
    return out


class _Resp:
    def __init__(self, entries): self._b = json.dumps([{"result": entries, "status": "OK"}]).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _verify_with(entries: list[dict]) -> bool:
    with patch("urllib.request.urlopen", return_value=_Resp(entries)):
        return JourneyTracker().verify_chain("chain-under-test")


def test_intact_chain_verifies() -> None:
    """Control: an untampered chain must still verify (guards against a fix that just returns False)."""
    assert _verify_with(_chain(5)) is True


def test_deleted_middle_row_is_detected() -> None:
    """THE ORIGINAL BUG: every survivor is self-consistent, so only linkage catches this."""
    e = _chain(5)
    tampered = e[:2] + e[3:]                      # drop sequence 2
    for x in tampered:                            # each row still validates against its OWN prev_hash
        assert x["chain_hash"] == hashlib.sha256(
            f"{x['prev_hash']}:{x['payload_hash']}".encode()).hexdigest()
    assert _verify_with(tampered) is False, "deleted middle row must break the chain"


def test_reordered_rows_are_detected() -> None:
    e = _chain(5)
    tampered = [e[0], e[2], e[1], e[3], e[4]]
    assert _verify_with(tampered) is False, "reordering must break the chain"


def test_inserted_forged_row_is_detected() -> None:
    """A forged row that is internally perfect but not linked to its predecessor."""
    e = _chain(4)
    ph = hashlib.sha256(b"forged").hexdigest()
    forged_prev = hashlib.sha256(b"not-the-real-previous-hash").hexdigest()
    forged = {
        "sequence": 2, "prev_hash": forged_prev, "payload_hash": ph,
        "chain_hash": hashlib.sha256(f"{forged_prev}:{ph}".encode()).hexdigest(),
    }
    assert forged["chain_hash"] == hashlib.sha256(
        f"{forged['prev_hash']}:{forged['payload_hash']}".encode()).hexdigest()
    assert _verify_with(e[:2] + [forged] + e[2:]) is False, "forged insert must break the chain"


def test_truncated_head_is_detected() -> None:
    """Dropping the genesis entry: remaining rows are self-consistent but no longer start at genesis."""
    assert _verify_with(_chain(5)[1:]) is False, "missing genesis must break the chain"


def test_payload_mutation_still_detected() -> None:
    """Regression guard for the ORIGINAL check, which must survive the fix."""
    e = _chain(4)
    e[2]["payload_hash"] = hashlib.sha256(b"swapped").hexdigest()
    assert _verify_with(e) is False


@pytest.mark.parametrize("n", [1, 2, 10])
def test_valid_chains_of_various_lengths(n: int) -> None:
    assert _verify_with(_chain(n)) is True
