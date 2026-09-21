"""event_log age filters must compare like with like (2026-09-21).

``event_log.timestamp`` is an epoch float for every live writer (6,388 rows in db
``main``, 12,016 in db ``vault``), with a handful of ISO-string / datetime rows from
older writers. SurrealDB orders values of DIFFERENT types by type, not by value, and
a number sorts below a datetime -- measured live::

    RETURN 1790000000 < time::now() - 2h;   -> true
    RETURN 1790000000 > time::now() - 6h;   -> false

So ``timestamp > time::now() - 6h`` silently returns nothing, and the purge in
``scripts/ops/remediate_adversarial_gaps_hybrid.py``
(``DELETE FROM event_log WHERE timestamp < time::now() - 2h``) matched EVERY numeric
row -- it would have deleted the whole live bus, not the stale tail.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cohezion.core.event_log_reader import older_than_predicate


REPO = Path(__file__).resolve().parents[2]


class TestOlderThanPredicate:
    def test_numeric_rows_compare_against_an_epoch_number(self) -> None:
        pred = older_than_predicate(7200, now=1_790_000_000.0)
        assert "type::is_number(timestamp) AND timestamp < 1789992800" in pred

    def test_never_compares_a_numeric_timestamp_to_a_datetime(self) -> None:
        pred = older_than_predicate(7200, now=1_790_000_000.0)
        numeric_clause = pred.split(" OR ")[0]
        assert "time::" not in numeric_clause

    def test_datetime_rows_are_type_guarded(self) -> None:
        pred = older_than_predicate(7200, now=1_790_000_000.0)
        assert "type::is_datetime(timestamp) AND timestamp < time::now() - 7200s" in pred

    def test_string_rows_are_never_matched(self) -> None:
        # Rows whose timestamp is a string cannot be compared safely: a purge keeps them.
        pred = older_than_predicate(7200, now=1_790_000_000.0)
        assert "is_string" not in pred

    def test_rejects_non_positive_age(self) -> None:
        with pytest.raises(ValueError):
            older_than_predicate(0)


# A literal SurrealQL comparison of a timestamp against a time::now() expression.
_BAD = re.compile(r"timestamp\s*[<>]=?\s*time::now\(\)")


def _offenders() -> list[str]:
    hits: list[str] = []
    for root in ("src", "scripts"):
        for path in (REPO / root).rglob("*.py"):
            text = path.read_text(errors="ignore")
            if "event_log" not in text:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                # A datetime comparison is fine when the row is type-guarded as a datetime.
                if _BAD.search(line) and "type::is_datetime(timestamp)" not in line:
                    hits.append(f"{path.relative_to(REPO)}:{lineno}: {line.strip()}")
    return hits


def test_no_event_log_query_compares_timestamp_to_time_now() -> None:
    """Class check: a file touching event_log must not compare timestamp to time::now()."""
    assert _offenders() == []
