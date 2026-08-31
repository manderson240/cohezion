r"""Unit tests for AutoHarness Provisioner Engine."""

from __future__ import annotations

from cohezion.agi.autoharness_provisioner import AutoHarnessProvisioner


def test_autoharness_provisioner_execution() -> None:
    provisioner = AutoHarnessProvisioner()
    harness = provisioner.provision_agent_harness(
        agent_role="Swarm Topology Architect",
        target_model="glm-5.2:cloud",
        domain="architecture",
    )

    assert harness.agent_role == "Swarm Topology Architect"
    assert harness.target_model == "glm-5.2:cloud"
    assert harness.policy_verified is True
    assert harness.zk_proof_valid is True
    assert harness.poincare_state.dim == 2048
    assert len(harness.allowed_tools) == 5
    assert harness.context_payload["sampling_params"]["max_tokens"] == 16384
