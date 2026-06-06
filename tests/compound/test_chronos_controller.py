"""Discriminating tests for the Chronos control surface (2026-06-06, item 13).

Permission-gated + outward-facing (it can stop a real systemd timer). DRY-RUN by default;
real action only behind apply=True; system-critical jobs refused. Each test fails a plausible
wrong impl:
  - a dry-run that actually executes (the default must NEVER touch the system),
  - one that pauses a system-critical job (vault-backup/guardian) even though it's non-deferrable,
  - one that ignores apply=True (never executes),
  - one that emits the wrong systemctl verb (stop vs start).
"""
from __future__ import annotations

from cohezion.compound.chronos import ChronosController, ChronosJob


DEFERRABLE = ChronosJob(
    source="systemd", job_id="autoresearch.timer", name="autoresearch",
    schedule="*/7 * * * *", command="bash run_autoresearch.sh", enabled=True,
)
CRITICAL = ChronosJob(
    source="systemd", job_id="vault-backup.timer", name="vault-backup",
    schedule="daily", command="python3 vault-backup.py", enabled=True,
)
HERMES_JOB = ChronosJob(
    source="hermes", job_id="h1", name="research-cycle", schedule="*/20 * * * *",
    command="run", enabled=True,
)


def _recording_controller():
    calls: list[list[str]] = []
    return ChronosController(runner=lambda cmd: (calls.append(cmd), 0)[1]), calls


def test_dry_run_emits_command_without_executing() -> None:
    ctl, calls = _recording_controller()
    r = ctl.pause(DEFERRABLE)  # apply defaults False
    assert r.command == ["systemctl", "--user", "stop", "autoresearch.timer"]
    assert r.applied is False and r.refused is False
    assert calls == []  # THE guarantee: dry-run never runs the command


def test_apply_true_executes_the_command() -> None:
    ctl, calls = _recording_controller()
    r = ctl.pause(DEFERRABLE, apply=True)
    assert r.applied is True
    assert calls == [["systemctl", "--user", "stop", "autoresearch.timer"]]


def test_critical_job_is_refused_even_with_apply() -> None:
    ctl, calls = _recording_controller()
    r = ctl.pause(CRITICAL, apply=True)
    assert r.refused is True and r.applied is False
    assert r.command is None
    assert calls == []  # a system-critical job is never touched


def test_resume_uses_start_verb() -> None:
    ctl, calls = _recording_controller()
    r = ctl.resume(DEFERRABLE, apply=True)
    assert r.command == ["systemctl", "--user", "start", "autoresearch.timer"]
    assert calls == [["systemctl", "--user", "start", "autoresearch.timer"]]


def test_non_systemd_source_is_refused() -> None:
    ctl, calls = _recording_controller()
    r = ctl.pause(HERMES_JOB, apply=True)
    assert r.refused is True and calls == []  # hermes control not wired → refuse, don't fake


def test_pause_resume_roundtrip_on_deferrable_unit() -> None:
    ctl, calls = _recording_controller()
    ctl.pause(DEFERRABLE, apply=True)
    ctl.resume(DEFERRABLE, apply=True)
    assert calls == [
        ["systemctl", "--user", "stop", "autoresearch.timer"],
        ["systemctl", "--user", "start", "autoresearch.timer"],
    ]
