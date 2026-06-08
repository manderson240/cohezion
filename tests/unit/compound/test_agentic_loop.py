"""Unit tests for the agent-governed loop tick (Chronos + Vault Keeper)."""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.compound.agentic_loop import TickResult, agentic_tick


class _FakeChronos:
    """Stand-in for ChronosRegistry — resource_advisory returns the injected jobs."""

    def __init__(self, advised):
        self._advised = advised

    def resource_advisory(self, *, level=None, manager=None):
        return self._advised


def _job(name):
    return SimpleNamespace(name=name)


class TestAgenticTick:
    def test_defers_under_critical_pressure(self):
        # Chronos advises deferral (CRITICAL) → loop HOLDS heavy work.
        called = []
        r = agentic_tick(
            improvement_fn=lambda ctx: called.append(ctx) or "did work",
            chronos=_FakeChronos([_job("overnight_evo_loop")]),
        )
        assert r.ran is False
        assert "chronos" in (r.deferred_reason or "").lower()
        assert "overnight_evo_loop" in r.deferred_jobs
        # DISCRIMINATING: an impl that ignores Chronos would run the work anyway.
        assert called == []

    def test_runs_with_headroom(self):
        called = []
        r = agentic_tick(
            improvement_fn=lambda ctx: called.append(ctx) or "did work",
            chronos=_FakeChronos([]),  # OK/WARNING → no advisory
            context_fn=lambda: ["ctx-a", "ctx-b"],
        )
        assert r.ran is True
        assert r.work_summary == "did work"
        assert len(called) == 1 and called[0] == ["ctx-a", "ctx-b"]
        assert r.context_count == 2

    def test_knowledge_step_owned_by_vault_keeper(self):
        # DISCRIMINATING: owner is resolved from the REAL specialist registry by
        # capability, not hardcoded. If vault-keeper loses report.vault.health, fails.
        r = agentic_tick(improvement_fn=lambda ctx: "x", chronos=_FakeChronos([]))
        assert r.knowledge_owner == "vault-keeper"

    def test_tick_result_is_observable_for_hitl(self):
        r = agentic_tick(
            improvement_fn=lambda ctx: "x",
            chronos=_FakeChronos([]),
            vault_health_fn=lambda: {"frontmatter_pct": 81},
        )
        # every governance signal is on the result (human-in-the-loop visibility)
        assert isinstance(r, TickResult)
        assert r.vault_health == {"frontmatter_pct": 81}
        assert r.knowledge_owner == "vault-keeper"
        assert isinstance(r.deferred_jobs, list)


class TestSpecialistRouting:
    """The loop routes its knowledge step to ANY specialist by capability."""

    def test_route_capability_resolves_distinct_specialists(self):
        from cohezion.compound.agentic_loop import route_capability

        # DISCRIMINATING: distinct capabilities resolve to DISTINCT owners — a
        # hardcoded-vault-keeper impl would fail the surreal/mcp cases.
        assert route_capability("report.vault.health") == "vault-keeper"
        assert route_capability("audit.surreal.schema") == "surreal-dba"
        assert route_capability("monitor.mcp.health") == "mcp-specialist"

    def test_route_capability_unknown_returns_none(self):
        from cohezion.compound.agentic_loop import route_capability

        assert route_capability("no.such.capability") is None

    def test_tick_routes_knowledge_to_named_capability_owner(self):
        from cohezion.compound.agentic_loop import agentic_tick

        class _FakeChronos:
            def resource_advisory(self, *, level=None, manager=None):
                return []

        r = agentic_tick(
            improvement_fn=lambda ctx: "x",
            chronos=_FakeChronos(),
            capability="audit.surreal.schema",
        )
        assert r.knowledge_owner == "surreal-dba"
