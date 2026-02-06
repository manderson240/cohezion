
import pytest

from cohezion.swarm.redundancy_suppression import RedundancyManager


@pytest.mark.anyio
async def test_redundancy_tiers():
    mgr = RedundancyManager(agent_name="TestAgent", window_size=100)
    task = "Test task 1"

    # 1st and 2nd time: Level 0
    l1, p1 = mgr.check(task)
    assert l1 == 0
    assert p1 == task

    l2, p2 = mgr.check(task)
    assert l2 == 0

    # 3rd time: Level 1 (Warning)
    l3, p3 = mgr.check(task)
    assert l3 == 1

    # 10th time: Level 2 (Perturbation)
    for _ in range(7):
        mgr.check(task)

    l10, p10 = mgr.check(task)
    assert l10 == 2
    assert "novel perspective" in p10

    # 50th time: Level 3 (Hard Sleep)
    for _ in range(40):
        mgr.check(task)

    l50, p50 = mgr.check(task)
    assert l50 == 3
    assert p50 is None


@pytest.mark.anyio
async def test_novel_tasks_clear():
    mgr = RedundancyManager(agent_name="TestAgent")
    mgr.check("task A")
    mgr.check("task A")
    mgr.check("task A")  # Level 1

    level_b, _ = mgr.check("task B")
    assert level_b == 0  # Novel task should not be suppressed
