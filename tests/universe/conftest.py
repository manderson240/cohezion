"""Universe test configuration.

Provides a session-scoped fixture that prevents ResourceMonitor from spawning
its infinite _heartbeat_loop inside the anyio event loop during tests.

Root cause: ResourceMonitor.__init__ calls loop.create_task(_heartbeat_loop())
when an event loop is running. anyio's test runner provides a live loop, so
the heartbeat task is created. When the test ends and anyio shuts down the loop,
the still-running heartbeat task blocks loop.run_until_complete() indefinitely.

Fix: patch _register_with_monitor and _deregister_from_monitor in tests that
call run_simulation() so ResourceMonitor is never instantiated during anyio tests.
"""


import pytest


@pytest.fixture(autouse=True)
def mock_resource_monitor_in_sandbox(request):
    """Prevent ResourceMonitor heartbeat from blocking anyio loop teardown.

    Only patches the anyio-marked tests in TestSandboxManagerExecution where
    run_simulation() triggers monitor registration. Sync tests are unaffected.
    """
    if request.node.get_closest_marker("anyio") is None:
        yield
        return

    with (
        pytest.MonkeyPatch().context() as mp,
    ):
        from cohezion.universe import sandbox_manager as sm_mod

        mp.setattr(
            sm_mod.SandboxManager,
            "_register_with_monitor",
            lambda self, instance: None,
        )
        mp.setattr(
            sm_mod.SandboxManager,
            "_deregister_from_monitor",
            lambda self, instance: None,
        )
        yield
