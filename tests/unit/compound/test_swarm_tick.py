"""swarm_tick — an agentic tick whose work is a local-silicon swarm."""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.compound.swarm_tick import swarm_tick


class _FakeChronos:
    def __init__(self, advised):
        self._advised = advised

    def resource_advisory(self, *, level=None, manager=None):
        return self._advised


class _RecordingOrchestrator:
    """Records plan_team calls; returns a fake TeamPlan."""

    def __init__(self):
        self.calls = []

    def plan_team(self, intent, max_agents=4):
        self.calls.append(intent)
        return SimpleNamespace(name="p", intent=intent, agents=[1, 2], tasks=[1, 2, 3])


class _FakeExecutor:
    def __init__(self):
        self.calls = []

    async def execute(self, plan):
        self.calls.append(plan)
        return SimpleNamespace(status="completed", tasks=[1, 2, 3])


class TestSwarmTick:
    def test_swarm_runs_under_headroom(self):
        orch, ex = _RecordingOrchestrator(), _FakeExecutor()
        r = swarm_tick(
            "federate the data products",
            chronos=_FakeChronos([]),
            orchestrator=orch,
            executor=ex,
        )
        assert r.ran is True
        assert orch.calls == ["federate the data products"]  # swarm planned
        assert len(ex.calls) == 1  # swarm executed
        assert r.work_summary["agents"] == 2
        assert r.work_summary["status"] == "completed"

    def test_swarm_deferred_under_pressure_not_spun_up(self):
        # DISCRIMINATING: under CRITICAL pressure the swarm must NOT be planned or
        # executed (the OOM-safety guarantee). A wrong impl that plans before the
        # Chronos gate would record a call.
        orch, ex = _RecordingOrchestrator(), _FakeExecutor()
        r = swarm_tick(
            "federate the data products",
            chronos=_FakeChronos([SimpleNamespace(name="evo_loop")]),
            orchestrator=orch,
            executor=ex,
        )
        assert r.ran is False
        assert orch.calls == []  # swarm NOT planned under pressure
        assert ex.calls == []  # swarm NOT executed
        assert "evo_loop" in r.deferred_jobs

    def test_knowledge_owner_is_vault_keeper(self):
        r = swarm_tick(
            "x",
            chronos=_FakeChronos([]),
            orchestrator=_RecordingOrchestrator(),
            executor=_FakeExecutor(),
        )
        assert r.knowledge_owner == "vault-keeper"
