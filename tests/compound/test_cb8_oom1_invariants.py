import pytest
from types import SimpleNamespace
from unittest.mock import patch
import inspect

def test_cb8_invariants():
    from cohezion.compound.degradation_detector import DegradationDetector

    d = DegradationDetector()
    assert d.get_recent_alerts() == []
    assert d.get_recent_alerts(n=0) == []

    # append 60 fake alerts (cap enforcement)
    for i in range(60):
        d._alert_history.append(SimpleNamespace(id=i))
    recent = d.get_recent_alerts(5)
    assert len(recent) == 5
    assert recent[-1].id == 59  # newest last
    assert len(d._alert_history) <= d._max_alert_history

    cleared = d.clear_alert_history()
    assert cleared == 50  # count actually removed (post-trim)
    assert len(d._alert_history) == 0


def test_oom1_invariants():
    from cohezion.inference.triune_orchestrator import build_triune_orchestrator
    import cohezion.inference.triune_orchestrator as tri

    # source must contain MemorySnapshot and available_gb
    src = inspect.getsource(build_triune_orchestrator)
    assert "MemorySnapshot" in src
    assert "available_gb" in src

    # mock /proc/meminfo to return 1GB (should fail gate)
    import builtins, io
    real_open = builtins.open

    def meminfo_only(path, *a, **k):
        if str(path) == "/proc/meminfo":
            return io.StringIO("MemAvailable: 1048576 kB\n")
        return real_open(path, *a, **k)

    with patch("builtins.open", side_effect=meminfo_only):
        with pytest.raises(RuntimeError) as exc:
            build_triune_orchestrator(enforce_memory_gate=True)
        assert "available_gb=1.0" in str(exc.value)

    # should not raise when gate disabled
    with patch.object(tri, "build_gaia_native_tier", lambda *args, **kwargs: object()):
        # avoid network calls while testing the OOM gate
        result = build_triune_orchestrator(enforce_memory_gate=False)
        assert isinstance(result, tri.TieredOrchestrator)
