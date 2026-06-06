"""Discriminating tests for the Chronos unified cron-job agent (2026-06-05).

Chronos DISCOVERS jobs from three real schedulers and presents one read-only view,
then advises which jobs to defer under memory pressure. Each test fails a plausible
wrong implementation:
  - a systemd parser that assumes every .timer has a paired .service (KeyError on orphans),
  - a Hermes parser that ignores the per-job `enabled` flag,
  - a discovery pass that raises (not degrades) when a source file is missing,
  - a resource advisory that returns ALL jobs (ignores deferrable) or ignores enabled,
  - a deferrability heuristic that marks system-critical jobs (vault-backup) as deferrable.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.chronos import (
    ChronosJob,
    ChronosRegistry,
    classify_deferrable,
)
from cohezion.platform.memory_pressure import PressureLevel


def _write_timer(d: Path, name: str, on_calendar: str, exec_start: str | None) -> None:
    (d / f"{name}.timer").write_text(
        f"[Unit]\nDescription={name}\n[Timer]\nOnCalendar={on_calendar}\n[Install]\nWantedBy=timers.target\n"
    )
    if exec_start is not None:
        (d / f"{name}.service").write_text(
            f"[Unit]\nDescription={name}\n[Service]\nExecStart={exec_start}\n"
        )


def test_systemd_parse_pairs_timer_with_service(tmp_path: Path) -> None:
    _write_timer(tmp_path, "vault-backup", "daily", "/usr/bin/python3 /x/vault-backup.py")
    reg = ChronosRegistry(systemd_dir=tmp_path, hermes_jobs=tmp_path / "nope.json")
    jobs = reg.discover_systemd()
    assert len(jobs) == 1
    j = jobs[0]
    assert j.source == "systemd"
    assert j.name == "vault-backup"
    assert j.schedule == "daily"
    assert "vault-backup.py" in j.command


def test_systemd_orphan_timer_without_service_does_not_crash(tmp_path: Path) -> None:
    # A .timer with NO sibling .service is a real on-disk state. The naive impl
    # (service must exist) raises; Chronos must degrade to command="".
    _write_timer(tmp_path, "ngrok-watchdog", "*-*-* *:00:00", exec_start=None)
    reg = ChronosRegistry(systemd_dir=tmp_path, hermes_jobs=tmp_path / "nope.json")
    jobs = reg.discover_systemd()
    assert len(jobs) == 1
    assert jobs[0].name == "ngrok-watchdog"
    assert jobs[0].command == ""  # degraded, not crashed


def test_systemd_enabled_reflects_enabled_units_set(tmp_path: Path) -> None:
    _write_timer(tmp_path, "git-maintenance", "hourly", "/usr/bin/git gc")
    reg = ChronosRegistry(
        systemd_dir=tmp_path,
        hermes_jobs=tmp_path / "nope.json",
        enabled_units={"git-maintenance.timer"},
    )
    assert reg.discover_systemd()[0].enabled is True
    reg2 = ChronosRegistry(
        systemd_dir=tmp_path, hermes_jobs=tmp_path / "nope.json", enabled_units=set()
    )
    assert reg2.discover_systemd()[0].enabled is False


def test_hermes_parse_respects_enabled_flag(tmp_path: Path) -> None:
    jobs_json = tmp_path / "jobs.json"
    jobs_json.write_text(
        '{"jobs": ['
        '{"id": "a1", "name": "research-cycle", "enabled": true,'
        ' "schedule": {"expr": "*/20 * * * *"}, "prompt": "run research", "last_status": "ok"},'
        '{"id": "b2", "name": "paused-job", "enabled": false,'
        ' "schedule": {"expr": "0 * * * *"}, "prompt": "x", "last_status": null}'
        "]}"
    )
    reg = ChronosRegistry(systemd_dir=tmp_path, hermes_jobs=jobs_json)
    jobs = {j.name: j for j in reg.discover_hermes()}
    assert jobs["research-cycle"].enabled is True
    assert jobs["research-cycle"].schedule == "*/20 * * * *"
    assert jobs["research-cycle"].last_status == "ok"
    assert jobs["paused-job"].enabled is False  # wrong impl ignores the flag


def test_discovery_failsoft_when_sources_missing(tmp_path: Path) -> None:
    # Neither source exists. discover_all() must return [] — never raise.
    reg = ChronosRegistry(systemd_dir=tmp_path / "gone", hermes_jobs=tmp_path / "gone.json")
    assert reg.discover_all() == []


def test_classify_deferrable_protects_system_critical() -> None:
    # Research/burst jobs are deferrable; system-critical jobs are NOT.
    assert classify_deferrable("TCRAO-Cohezion-AutoResearch", "bash run_tcrao_cycle.sh") is True
    assert classify_deferrable("forge-night-burst", "bash forge_night_burst_v3.sh") is True
    assert classify_deferrable("vault-backup", "/usr/bin/python3 vault-backup.py") is False
    assert classify_deferrable("cohezion-guardian", "guardian.sh") is False
    # unknown system job → conservative: NOT deferrable (don't defer what we don't understand)
    assert classify_deferrable("upnp-forward", "upnp.sh") is False


def test_resource_advisory_only_deferrable_enabled_at_critical(tmp_path: Path) -> None:
    jobs_json = tmp_path / "jobs.json"
    jobs_json.write_text(
        '{"jobs": ['
        '{"id": "r", "name": "autoresearch", "enabled": true, "schedule": {"expr": "*/7 * * * *"}, "prompt": "p"},'
        '{"id": "rp", "name": "autoresearch-paused", "enabled": false, "schedule": {"expr": "*/9 * * * *"}, "prompt": "p"}'
        "]}"
    )
    _write_timer(
        tmp_path, "vault-backup", "daily", "/usr/bin/python3 vault-backup.py"
    )  # critical, enabled
    reg = ChronosRegistry(
        systemd_dir=tmp_path, hermes_jobs=jobs_json, enabled_units={"vault-backup.timer"}
    )

    # At OK: nothing to defer.
    assert reg.resource_advisory(level=PressureLevel.OK) == []
    # At CRITICAL: only the ENABLED + DEFERRABLE job (autoresearch). Not vault-backup (critical),
    # not autoresearch-paused (disabled).
    advised = reg.resource_advisory(level=PressureLevel.CRITICAL)
    names = {j.name for j in advised}
    assert names == {"autoresearch"}


def test_summary_counts_by_source_and_enabled(tmp_path: Path) -> None:
    jobs_json = tmp_path / "jobs.json"
    jobs_json.write_text(
        '{"jobs": [{"id": "r", "name": "research", "enabled": true, "schedule": {"expr": "*/7 * * * *"}, "prompt": "p"}]}'
    )
    _write_timer(tmp_path, "vault-backup", "daily", "/usr/bin/python3 vault-backup.py")
    reg = ChronosRegistry(
        systemd_dir=tmp_path, hermes_jobs=jobs_json, enabled_units={"vault-backup.timer"}
    )
    s = reg.summary()
    assert s["total"] == 2
    assert s["by_source"]["systemd"] == 1
    assert s["by_source"]["hermes"] == 1
    assert s["enabled"] == 2


def test_chronos_job_is_frozen() -> None:
    j = ChronosJob(
        source="systemd", job_id="x", name="x", schedule="daily", command="", enabled=True
    )
    try:
        j.name = "y"  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised
