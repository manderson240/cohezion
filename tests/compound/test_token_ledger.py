"""Falsification-first tests for TokenLedger — the Quarter-on-a-String proof.

Builds RED first: every test is written to FAIL against a vanity / mislabelled
implementation, then GREEN once the honest local-vs-cloud accounting lands.
"""

from __future__ import annotations

import inspect

import pytest

from cohezion.compound.token_ledger import TokenLedger


def test_record_local_adds_local_tokens_and_cost_avoided():
    """(1) record_local raises local_tokens + cost_avoided, leaves cloud untouched."""
    led = TokenLedger()
    led.record_local("lemonade_classify", 800)
    s = led.summary()
    assert s.local_tokens == 800
    assert s.cloud_tokens == 0           # cloud column MUST stay zero for a local row
    assert s.quarters_saved_usd > 0.0    # cost-avoided ("quarters saved") accrues


def test_record_cloud_adds_real_cost_not_savings():
    """(2) record_cloud adds real cloud cost; cost_avoided ("quarters") is unchanged."""
    led = TokenLedger()
    before = led.summary()
    assert before.quarters_saved_usd == 0.0
    led.record_cloud("claude_orchestration", 1200)
    s = led.summary()
    assert s.cloud_tokens == 1200
    assert s.cloud_cost_usd > 0.0        # real dollars spent on cloud orchestration
    assert s.quarters_saved_usd == 0.0   # cloud work saves nothing — no vanity credit
    assert s.local_tokens == 0


def test_local_fraction_computed_across_mix():
    """(3) local_fraction = local / (local + cloud) across a realistic mix."""
    led = TokenLedger()
    led.record_local("npu_route", 3000)
    led.record_local("igpu_gen", 1000)
    led.record_cloud("claude_main_loop", 1000)
    s = led.summary()
    assert s.local_tokens == 4000
    assert s.cloud_tokens == 1000
    assert s.local_fraction == pytest.approx(4000 / 5000)  # 0.8


def test_discriminating_vanity_cloud_mislabelled_as_local():
    """(4) DISCRIMINATING: mislabelling cloud as local inflates local_fraction to a
    vanity 1.0; honest accounting reveals the orchestration leak (fraction < 1.0).

    A ledger that counts orchestration tokens as local would report 100% local and
    fail this assertion — the metric only has value if it distinguishes the two."""
    honest = TokenLedger()
    honest.record_local("lemonade_work", 1000)
    honest.record_cloud("claude_orchestration", 1000)  # the REAL cloud leak

    vanity = TokenLedger()
    vanity.record_local("lemonade_work", 1000)
    vanity.record_local("claude_orchestration", 1000)  # BUG: cloud counted as local

    assert honest.summary().local_fraction < 1.0       # honest exposes the leak
    assert vanity.summary().local_fraction == 1.0       # vanity hides it
    assert honest.summary().local_fraction == pytest.approx(0.5)


def test_surreal_write_uses_surql_set_no_raw_fstring():
    """(5) STRUCTURAL: the SurrealDB write goes through the parameterized _surql_set
    builder — never a hand-built interpolated SET f-string (injection-safe by import)."""
    src = inspect.getsource(TokenLedger._persist_row)
    assert "_surql_set" in src
    assert "SET {" not in src          # no raw f-string SET body
    assert 'SET " + f"' not in src
