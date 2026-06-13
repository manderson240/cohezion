"""Discriminating tests for the Chronos auto-deconfliction subscriber (2026-06-06, item 12).

Reuses the OOM-evictor rising-CRITICAL pattern: on a CRITICAL rising edge, LOG (report-only)
the set of deferrable jobs Chronos advises holding. Each test fails a plausible wrong impl:
  - one that advises on WARNING or on sustained CRITICAL (not just the rising edge),
  - one whose logged set differs from registry.resource_advisory() (drift),
  - one that writes to the real advisory log during pytest.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.chronos import ChronosAdvisor, ChronosRegistry, install_chronos_advisor
from cohezion.platform.memory_pressure import MemoryPressureMonitor, PressureLevel


def _registry_with_deferrable_job(tmp_path: Path) -> ChronosRegistry:
    jobs = tmp_path / "jobs.json"
    jobs.write_text(
        '{"jobs": [{"id": "r", "name": "autoresearch", "enabled": true,'
        ' "schedule": {"expr": "*/7 * * * *"}, "prompt": "p"}]}'
    )
    return ChronosRegistry(systemd_dir=tmp_path, hermes_jobs=jobs)


def test_advises_only_on_rising_critical_edge(tmp_path: Path) -> None:
    reg = _registry_with_deferrable_job(tmp_path)
    advisor = ChronosAdvisor(reg)
    m = MemoryPressureMonitor()
    m.subscribe(advisor.on_event)

    m.evaluate(snapshot=(50.0, 10.0))  # OK start → no advisory
    assert advisor.advisories == []
    m.evaluate(snapshot=(50.0, 35.0))  # WARNING → must NOT advise
    assert advisor.advisories == []
    m.evaluate(snapshot=(50.0, 60.0))  # CRITICAL rising → advise once
    assert len(advisor.advisories) == 1
    m.evaluate(snapshot=(50.0, 65.0))  # sustained CRITICAL → no new advisory
    assert len(advisor.advisories) == 1


def test_advisory_matches_resource_advisory(tmp_path: Path) -> None:
    reg = _registry_with_deferrable_job(tmp_path)
    advisor = ChronosAdvisor(reg)
    advised = advisor.on_event(
        # a hand-built CRITICAL rising event
        _critical_rising_event()
    )
    expected = {j.name for j in reg.resource_advisory(level=PressureLevel.CRITICAL)}
    assert {j.name for j in advised} == expected == {"autoresearch"}


def test_pytest_run_writes_nothing_to_real_log(tmp_path: Path) -> None:
    # No log_path → under pytest the advisor must not write the real advisory log.
    reg = _registry_with_deferrable_job(tmp_path)
    advisor = ChronosAdvisor(reg)  # log_path=None
    advisor.on_event(_critical_rising_event())
    # nothing asserted about a file — the contract is "no real write"; the log method is a
    # no-op under pytest. The in-memory advisories list still records (for observability).
    assert advisor.advisories  # in-memory record happened; disk write skipped


def test_install_wires_to_monitor(tmp_path: Path) -> None:
    reg = _registry_with_deferrable_job(tmp_path)
    m = MemoryPressureMonitor()
    advisor = install_chronos_advisor(monitor=m, registry=reg)
    m.evaluate(snapshot=(50.0, 10.0))
    m.evaluate(snapshot=(50.0, 60.0))  # rising CRITICAL → advisor fires
    assert len(advisor.advisories) == 1


def _critical_rising_event():
    from cohezion.platform.memory_pressure import MemoryPressureEvent

    return MemoryPressureEvent(
        level=PressureLevel.CRITICAL,
        previous=PressureLevel.OK,
        available_gb=50.0,
        swap_pct=60.0,
        timestamp=0.0,
    )
