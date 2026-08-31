from cohezion.agents.gaia_bugfix_agent import BugfixTask, GaiaBugfixAgentManager, GaiaBugfixResult


def test_gaia_bugfix_agent_delegation():
    mgr = GaiaBugfixAgentManager()
    task = mgr.create_kanban_bugfix_item(
        task_id="bug_101",
        title="Fix OOM boundary check in poincare_manifold.py",
        module_path="src/cohezion/physics/poincare_manifold.py",
        severity="high",
    )
    assert isinstance(task, BugfixTask)
    assert task.task_id == "bug_101"
    assert task.kanban_status == "backlog"

    res = mgr.execute_gaia_bugfix(task)
    assert isinstance(res, GaiaBugfixResult)
    assert res.task_id == "bug_101"
    assert res.patch_applied is True
    assert res.verified_by_autoharness is True
    assert res.zk_proof.is_valid is True
    assert res.kanban_status == "done"
