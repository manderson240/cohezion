"""The BlueQubit bridge and ARC solver must never return results nobody measured.

Before 2026-09-25 the bridge returned `{"0000": 512, "1111": 512}` when the SDK was
absent, reported `counts == {}` as SUCCESS on every real job (JobResult has
`get_counts()`, not a `counts` attribute), and the solver answered "candidate 0"
without a token or after an error. The fakes below are spec'd classes, not bare
MagicMocks: a MagicMock invents any attribute read, which would hide the `counts` bug.
"""

from __future__ import annotations

import pytest

from cohezion.quantum import QuantumBackendUnavailableError
from cohezion.quantum import bluequbit_arc_qubo_solver as solver_mod
from cohezion.quantum import bluequbit_quantum_bridge as bridge_mod


_COUNTS = {"0110": 700, "1001": 300}


class _FakeJobResult:
    """Only the JobResult surface the code is allowed to use."""

    def __init__(self, counts: dict[str, int] | None) -> None:
        self.job_id = "job-123"
        self._counts = counts

    def get_counts(self) -> dict[str, int] | None:
        return self._counts


class _FakeClient:
    def __init__(self, counts: dict[str, int] | None = _COUNTS, error: Exception | None = None):
        self._counts = counts
        self._error = error

    def run(self, circuit, device, shots):
        if self._error:
            raise self._error
        return _FakeJobResult(self._counts)


class _FakeCircuit:
    def __init__(self, *args) -> None:
        pass

    def __getattr__(self, name):  # h / cx / rz / measure
        return lambda *a, **k: None


class _FakeQiskit:
    QuantumCircuit = _FakeCircuit


def _offline_bridge(monkeypatch) -> bridge_mod.BlueQubitQuantumBridge:
    """Build a bridge without touching the network, as if the SDK were absent."""
    monkeypatch.setattr(bridge_mod, "HAS_BLUEQUBIT", False)
    return bridge_mod.BlueQubitQuantumBridge(api_token="unused")


# --- bridge -------------------------------------------------------------


def test_bridge_raises_when_sdk_absent(monkeypatch) -> None:
    bridge = _offline_bridge(monkeypatch)
    with pytest.raises(QuantumBackendUnavailableError, match="not installed"):
        bridge.run_quantum_kernel(num_qubits=4)


def test_bridge_raise_carries_the_init_failure(monkeypatch) -> None:
    class _BrokenSDK:
        @staticmethod
        def init(**kwargs):
            raise ConnectionError("auth rejected")

    monkeypatch.setattr(bridge_mod, "HAS_BLUEQUBIT", True)
    monkeypatch.setattr(bridge_mod, "bluequbit", _BrokenSDK, raising=False)
    bridge = bridge_mod.BlueQubitQuantumBridge(api_token="t")
    with pytest.raises(QuantumBackendUnavailableError, match="auth rejected") as info:
        bridge.run_quantum_kernel()
    assert isinstance(info.value.__cause__, ConnectionError)


def test_bridge_returns_the_measured_counts(monkeypatch) -> None:
    bridge = _offline_bridge(monkeypatch)
    monkeypatch.setattr(bridge_mod, "HAS_BLUEQUBIT", True)
    bridge.client = _FakeClient()
    res = bridge.run_quantum_kernel(num_qubits=4)
    assert res["status"] == "SUCCESS"
    assert res["counts"] == _COUNTS
    assert res["job_id"] == "job-123"


def test_bridge_refuses_success_without_counts(monkeypatch) -> None:
    bridge = _offline_bridge(monkeypatch)
    monkeypatch.setattr(bridge_mod, "HAS_BLUEQUBIT", True)
    bridge.client = _FakeClient(counts=None)
    with pytest.raises(RuntimeError, match="no measurement counts"):
        bridge.run_quantum_kernel()


def test_bridge_execution_error_propagates(monkeypatch) -> None:
    bridge = _offline_bridge(monkeypatch)
    monkeypatch.setattr(bridge_mod, "HAS_BLUEQUBIT", True)
    bridge.client = _FakeClient(error=TimeoutError("queue full"))
    with pytest.raises(TimeoutError):
        bridge.run_quantum_kernel()


# --- ARC solver ---------------------------------------------------------

_MATRIX = [[0.1, 0.8], [0.8, 0.2]]


@pytest.fixture
def no_token(monkeypatch):
    for var in ("BLUEQUBIT_API_TOKEN", "BLUEQUBIT_API_KEY", "BLUEQUBIT_TOKEN"):
        monkeypatch.delenv(var, raising=False)


def test_solver_raises_without_token(monkeypatch, no_token) -> None:
    monkeypatch.setattr(solver_mod, "HAS_BLUEQUBIT", True)
    solver = solver_mod.BlueQubitARCSolver()
    with pytest.raises(QuantumBackendUnavailableError, match="token"):
        solver.solve_graph_isomorphism_qubo(_MATRIX)


def test_solver_init_failure_becomes_unavailable_with_cause(monkeypatch) -> None:
    class _BrokenSDK:
        @staticmethod
        def init(**kwargs):
            raise ConnectionError("auth rejected")

    monkeypatch.setenv("BLUEQUBIT_API_TOKEN", "t")
    monkeypatch.setattr(solver_mod, "HAS_BLUEQUBIT", True)
    monkeypatch.setattr(solver_mod, "bluequbit", _BrokenSDK, raising=False)
    solver = solver_mod.BlueQubitARCSolver()
    with pytest.raises(QuantumBackendUnavailableError, match="auth rejected"):
        solver.solve_graph_isomorphism_qubo(_MATRIX)


def test_solver_raises_when_sdk_absent(monkeypatch) -> None:
    monkeypatch.setattr(solver_mod, "HAS_BLUEQUBIT", False)
    solver = solver_mod.BlueQubitARCSolver()
    with pytest.raises(QuantumBackendUnavailableError, match="not installed"):
        solver.solve_graph_isomorphism_qubo(_MATRIX)


def test_solver_rejects_empty_matrix(monkeypatch, no_token) -> None:
    monkeypatch.setattr(solver_mod, "HAS_BLUEQUBIT", False)
    with pytest.raises(ValueError):
        solver_mod.BlueQubitARCSolver().solve_graph_isomorphism_qubo([])


def _live_solver(monkeypatch, client: _FakeClient) -> solver_mod.BlueQubitARCSolver:
    monkeypatch.setattr(solver_mod, "HAS_BLUEQUBIT", False)
    solver = solver_mod.BlueQubitARCSolver()
    monkeypatch.setattr(solver_mod, "qiskit", _FakeQiskit, raising=False)
    solver.client = client
    return solver


def test_solver_index_comes_from_measured_counts(monkeypatch) -> None:
    solver = _live_solver(monkeypatch, _FakeClient(counts={"01": 10, "11": 990}))
    res = solver.solve_graph_isomorphism_qubo(_MATRIX)
    assert res["bitstring"] == "11"
    assert res["optimal_candidate_index"] == int("11", 2) % 2
    assert res["job_id"] == "job-123"


def test_solver_execution_error_is_not_answered_with_index_zero(monkeypatch) -> None:
    solver = _live_solver(monkeypatch, _FakeClient(error=TimeoutError("queue full")))
    with pytest.raises(TimeoutError):
        solver.solve_graph_isomorphism_qubo(_MATRIX)


def test_solver_refuses_success_without_counts(monkeypatch) -> None:
    solver = _live_solver(monkeypatch, _FakeClient(counts={}))
    with pytest.raises(RuntimeError, match="no measurement counts"):
        solver.solve_graph_isomorphism_qubo(_MATRIX)
