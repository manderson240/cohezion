import pytest
from cohezion.reliability.oom_guard import OOMGuard, MemoryState

def test_oom_guard_get_memory_state():
    state = OOMGuard.get_memory_state()
    assert isinstance(state, MemoryState)
    assert state.available_gb > 0.0
    assert state.total_gb > 0.0
    assert isinstance(state.is_safe, bool)
