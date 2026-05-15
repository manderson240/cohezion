"""Coverage batch Z51: autoharness, sandbox_security, resonance."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/autoharness.py
# ---------------------------------------------------------------------------


class TestAutoHarnessSynthesizer:
    def _make_synthesizer(self, llm_executor=None, max_iterations=3):
        from cohezion.compound.autoharness import AutoHarnessSynthesizer

        if llm_executor is None:
            llm_executor = MagicMock()
            llm_executor.execute_task = AsyncMock(
                return_value="```python\ndef verify_action(state, action): return True\n```"
            )
        return AutoHarnessSynthesizer(llm_executor=llm_executor, max_iterations=max_iterations)

    def test_synthesize_verifier_success_on_first_try(self):
        synth = self._make_synthesizer()
        code_produced = []

        def dummy_env(code):
            code_produced.append(code)
            return True, ""

        result = asyncio.run(synth.synthesize_verifier("Simple env", dummy_env))
        assert "verify_action" in result

    def test_synthesize_verifier_retries_on_failure(self):
        mock_llm = MagicMock()
        call_count = [0]

        async def side_effect(**kwargs):
            call_count[0] += 1
            return "```python\ndef verify_action(state, action): return True\n```"

        mock_llm.execute_task = side_effect
        synth = self._make_synthesizer(llm_executor=mock_llm, max_iterations=3)

        # Fail twice, then succeed
        attempt = [0]

        def dummy_env(code):
            attempt[0] += 1
            return attempt[0] >= 2, "retry"

        result = asyncio.run(synth.synthesize_verifier("env", dummy_env))
        assert call_count[0] >= 2

    def test_synthesize_verifier_exhausts_iterations(self):
        synth = self._make_synthesizer(max_iterations=2)

        def dummy_env(code):
            return False, "always fails"

        result = asyncio.run(synth.synthesize_verifier("env", dummy_env))
        # Returns last generated code even if all iterations fail
        assert isinstance(result, str)

    def test_synthesize_verifier_handles_llm_exception(self):
        mock_llm = MagicMock()
        mock_llm.execute_task = AsyncMock(side_effect=RuntimeError("LLM down"))
        synth = self._make_synthesizer(llm_executor=mock_llm, max_iterations=2)

        def dummy_env(code):
            return False, ""

        result = asyncio.run(synth.synthesize_verifier("env", dummy_env))
        assert result == ""  # no code produced

    def test_synthesize_verifier_response_as_text_attr(self):
        code_str = "```python\ndef verify_action(state, action): return True\n```"

        class MockResponseWithText:
            text = code_str

        mock_llm = MagicMock()
        mock_llm.execute_task = AsyncMock(return_value=MockResponseWithText())

        synth = self._make_synthesizer(llm_executor=mock_llm)

        def dummy_env(code):
            return True, ""

        result = asyncio.run(synth.synthesize_verifier("env", dummy_env))
        assert "verify_action" in result

    def test_synthesize_policy_success(self):
        synth = self._make_synthesizer()
        synth.llm.execute_task = AsyncMock(return_value="```python\ndef predict_action(state): return 0\n```")

        def dummy_env(code):
            return True, ""

        result = asyncio.run(synth.synthesize_policy("Simple env", dummy_env))
        assert "predict_action" in result

    def test_synthesize_policy_no_code_block_returns_raw(self):
        synth = self._make_synthesizer()
        synth.llm.execute_task = AsyncMock(return_value="just some text without code blocks")

        def dummy_env(code):
            return True, ""

        result = asyncio.run(synth.synthesize_policy("env", dummy_env))
        assert "just some text" in result


# ---------------------------------------------------------------------------
# Module 2: security/sandbox_security.py
# ---------------------------------------------------------------------------


class TestSandboxRedTeam:
    def _make_verifier(self):
        from cohezion.security.memory_barrier import MemoryMappedBarrier
        from cohezion.security.sandbox_security import SandboxRedTeam

        return SandboxRedTeam(barrier=MemoryMappedBarrier())

    def test_penetration_result_dataclass(self):
        from cohezion.security.sandbox_security import PenetrationResult

        r = PenetrationResult(probe_id="p1", blocked=True, audit_logged=True)
        assert r.blocked is True
        d = r.to_dict()
        assert d["probe_id"] == "p1"

    def test_sandbox_audit_event_to_dict(self):
        from cohezion.security.sandbox_security import SandboxAuditEvent

        ev = SandboxAuditEvent(allocation_id="a1", event_type="oob", detail="read at 0xDEAD")
        d = ev.to_dict()
        assert d["event_type"] == "oob"

    def test_probe_out_of_bounds_blocked(self):
        verifier = self._make_verifier()
        alloc = verifier._barrier.allocate("proc1", size_bytes=256)
        result = verifier.probe_out_of_bounds_read("proc1", alloc.end_address + 0x1000)
        assert result.blocked is True
        assert result.audit_logged is True

    def test_probe_quota_overflow_blocked(self):
        verifier = self._make_verifier()
        result = verifier.probe_quota_overflow("proc1", requested_bytes=2048, quota_bytes=1024)
        assert result.blocked is True

    def test_run_full_pentest_all_blocked(self):
        verifier = self._make_verifier()
        alloc = verifier._barrier.allocate("proc1", size_bytes=256)
        results = verifier.run_full_pentest("proc1", alloc.base_address, alloc.size_bytes)
        assert len(results) == 4
        blocked_count = sum(1 for r in results if r.blocked)
        assert blocked_count >= 3  # most should be blocked

    def test_audit_events_logged(self):
        verifier = self._make_verifier()
        alloc = verifier._barrier.allocate("p1", size_bytes=256)
        verifier.probe_out_of_bounds_read("p1", alloc.end_address + 1)
        events = verifier.audit_events()
        assert len(events) > 0

    def test_probes_run_counter(self):
        verifier = self._make_verifier()
        alloc = verifier._barrier.allocate("p1", size_bytes=256)
        verifier.probe_out_of_bounds_read("p1", alloc.end_address + 1)
        verifier.probe_quota_overflow("p1", 9999, 100)
        assert verifier.probes_run == 2


# ---------------------------------------------------------------------------
# Module 3: swarm/resonance.py
# ---------------------------------------------------------------------------


class TestResonanceProtocol:
    def test_resonance_state_dataclass(self):
        from cohezion.swarm.resonance import ResonanceState

        state = ResonanceState(agent_id="a1", coherence=0.7)
        assert state.agent_id == "a1"
        assert state.coherence == pytest.approx(0.7)

    def test_resonance_protocol_share_and_get_latest(self):
        from cohezion.swarm.resonance import ResonanceProtocol, ResonanceState

        protocol = ResonanceProtocol()
        state1 = ResonanceState(agent_id="a1", coherence=0.5)
        state2 = ResonanceState(agent_id="a2", coherence=0.8)
        asyncio.run(protocol.share(state1))
        asyncio.run(protocol.share(state2))
        latest = asyncio.run(protocol.get_latest())
        assert latest.agent_id == "a2"

    def test_resonance_get_latest_empty(self):
        from cohezion.swarm.resonance import ResonanceProtocol

        protocol = ResonanceProtocol()
        result = asyncio.run(protocol.get_latest())
        assert result is None

    def test_resonance_calculate_collective_coherence(self):
        from cohezion.swarm.resonance import ResonanceProtocol, ResonanceState

        protocol = ResonanceProtocol()
        asyncio.run(protocol.share(ResonanceState(agent_id="a1", coherence=0.6)))
        asyncio.run(protocol.share(ResonanceState(agent_id="a2", coherence=0.8)))
        coh = asyncio.run(protocol.calculate_collective_coherence())
        assert coh == pytest.approx(0.7)

    def test_resonance_empty_coherence_is_zero(self):
        from cohezion.swarm.resonance import ResonanceProtocol

        protocol = ResonanceProtocol()
        coh = asyncio.run(protocol.calculate_collective_coherence())
        assert coh == pytest.approx(0.0)
