"""TDD tests for the Mycelium recursion-loop fix (shared singleton).

The recursion gap: the WRITER (CompoundExecutor Step 10.6) and the READER
(api/services/mycelium_api) each construct their OWN MyceliumRegistry(), so
skills synthesized on the write side are invisible to the read side — the loop
never closes. The fix is a shared get_instance() singleton (mirroring
SemanticCache.get_instance, harness CA2).

These tests are written FIRST and MUST fail before the fix lands:
  - test_get_instance_exists / returns_singleton  -> AttributeError until added
  - test_executor_and_api_share_registry          -> different ids until both wired
  - test_recursion_readback                        -> reader sees 0 skills until fixed
"""

from __future__ import annotations

import time

import pytest

from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module singleton between tests for isolation."""
    MyceliumRegistry.reset_instance()
    yield
    MyceliumRegistry.reset_instance()


def test_get_instance_exists():
    """MyceliumRegistry must expose a get_instance() classmethod (CA2 pattern)."""
    assert hasattr(MyceliumRegistry, "get_instance"), "get_instance() classmethod missing"


def test_get_instance_returns_singleton():
    """Two get_instance() calls return the same object."""
    a = MyceliumRegistry.get_instance()
    b = MyceliumRegistry.get_instance()
    assert a is b, "get_instance() must return the same singleton object"
    assert isinstance(a, MyceliumRegistry)


def test_direct_construction_still_isolated():
    """Direct MyceliumRegistry() must stay independent (test isolation preserved)."""
    s = MyceliumRegistry.get_instance()
    direct = MyceliumRegistry()
    assert direct is not s, "explicit construction must not return the singleton"


def test_executor_and_api_share_registry():
    """The executor's registry and the api's registry must be the SAME object.

    This is the heart of the fix: writer and reader point at one singleton, so a
    skill synthesized via the writer is visible via the reader.
    """
    from cohezion.api.services import mycelium_api

    # reader side
    reader = mycelium_api._get_registry()
    # writer side (what the executor obtains)
    writer = MyceliumRegistry.get_instance()
    assert reader is writer, "api reader and registry singleton must be the same object"


def test_recursion_readback_via_singleton():
    """Direct: ingest via the singleton, audit, READ BACK through the api reader.

    Proves reader/writer share state; the REAL executor path is covered by
    test_real_writer_path_closes_loop below.
    """
    from cohezion.api.services import mycelium_api

    writer = MyceliumRegistry.get_instance()
    for i in range(3):
        writer.ingest_entry(
            JournalEntry(
                entry_id=f"t-{i}",
                content=f"experience {i}",
                domain="routing",
                timestamp=time.time(),
            )
        )
    writer.run_audit()

    reader = mycelium_api._get_registry()
    assert reader is writer, "precondition: reader must share the singleton"
    assert "ROUTING_SYNTHESIZED" in reader.skills
    assert len(reader.skills) >= 1


def test_real_writer_path_closes_loop():
    """END-TO-END through the REAL writer: PostExecutionOrchestrator._run_mycelium.

    This is the test that catches the actual production bug: the executor's
    post-execution path must write into the SAME registry the api reader reads.
    It drives the real _run_mycelium method (domain='pattern' -> PATTERN_SYNTHESIZED)
    rather than calling the singleton directly, so a bare MyceliumRegistry() at the
    write site would make this fail.
    """
    from types import SimpleNamespace

    from cohezion.api.services import mycelium_api
    from cohezion.compound.post_execution import PostExecutionOrchestrator

    # Minimal executor stub — _run_mycelium only touches self._ex._mycelium_registry.
    fake_executor = SimpleNamespace()
    orch = PostExecutionOrchestrator(fake_executor)

    # Drive the real writer path 10x so the %10 audit cadence fires.
    for i in range(10):
        orch._run_mycelium(success=True, skill_name=f"skill_{i}", task_description=f"task {i}")

    # The reader (api) must see the skill synthesized by the real writer path.
    reader = mycelium_api._get_registry()
    assert "PATTERN_SYNTHESIZED" in reader.skills, (
        "reader must see the skill synthesized via the REAL executor writer path "
        "(post_execution._run_mycelium) — proves both writer sites use the singleton"
    )


def test_writer_path_failure_does_not_synthesize():
    """_run_mycelium with success=False must not ingest (guard correctness)."""
    from types import SimpleNamespace

    from cohezion.compound.post_execution import PostExecutionOrchestrator

    orch = PostExecutionOrchestrator(SimpleNamespace())
    orch._run_mycelium(success=False, skill_name="x", task_description="y")
    assert len(MyceliumRegistry.get_instance().skills) == 0
