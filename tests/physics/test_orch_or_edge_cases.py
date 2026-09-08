"""Edge Case and Boundary Condition Stress Tests for Orch-OR & Durable Bridge.
"""

from __future__ import annotations

import cmath
import math
import pytest
from pathlib import Path
from cohezion.physics.orch_or_runtime_service import (
    OrchORRuntimeService,
    SuperposedPolicyBranch,
    HIHO_EQUILIBRIUM_TARGET,
)
from cohezion.physics.twistor_orch_or import OrchOREngine
from cohezion.data_mesh.durable_precipitation_bridge import (
    DurablePrecipitationBridge,
    DurableWitnessMark,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


def test_edge_case_zero_separation_distance():
    orch = OrchOREngine()
    # separation_distance_nm <= 0 should be guarded or clamped, not ZeroDivisionError
    try:
        res = orch.compute_reduction_time(1000, separation_distance_nm=0.0)
        assert res.gravitational_self_energy_eg > 0.0
    except ZeroDivisionError:
        pytest.fail("ZeroDivisionError on separation_distance_nm=0.0")


def test_edge_case_all_zero_amplitudes():
    service = OrchORRuntimeService()
    b1 = SuperposedPolicyBranch(
        branch_id="zero_amp_1",
        action_type="orch_or_hiho",
        payload={"coherence": 0.50},
        amplitude=0j,
    )
    b2 = SuperposedPolicyBranch(
        branch_id="zero_amp_2",
        action_type="orch_or_hiho",
        payload={"coherence": 0.50},
        amplitude=0j,
    )
    res = service.evaluate_superposition([b1, b2])
    assert res.is_hiho_equilibrium is True
    assert res.final_coherence == 0.50


def test_edge_case_illegal_policy_branch_pruning():
    autoharness = AutoHarnessPolicy()
    # Register strict mass policy
    autoharness.register_policy("strict_physics", lambda s: s.get("mass", 0) > 0)
    service = OrchORRuntimeService(autoharness_policy=autoharness)

    # Branch 1 has higher amplitude but violates strict_physics (mass = -5)
    b_illegal = SuperposedPolicyBranch(
        branch_id="illegal_branch",
        action_type="strict_physics",
        payload={"mass": -5.0, "coherence": 0.50},
        amplitude=10.0 + 0j,
    )
    # Branch 2 is legal (mass = +2.0)
    b_legal = SuperposedPolicyBranch(
        branch_id="legal_branch",
        action_type="strict_physics",
        payload={"mass": 2.0, "coherence": 0.50},
        amplitude=1.0 + 0j,
    )

    res = service.evaluate_superposition([b_illegal, b_legal])
    # The verifier-backed collapse MUST NOT select the illegal branch!
    assert res.collapsed_branch.branch_id == "legal_branch"
    assert res.autoharness_result.allowed is True


def test_edge_case_self_referencing_wikilinks(tmp_path: Path):
    vault_dir = tmp_path / "edge_vault"
    bridge = DurablePrecipitationBridge(vault_dir=vault_dir)

    # Note linking to itself and containing strange wikilinks
    mark = DurableWitnessMark(
        mark_id="self_referential_node",
        title="Self Referential Node",
        content="Linking to [[self_referential_node]] and [[header_target#Section 1]] and [[]].",
    )
    links = bridge._extract_wikilinks(mark.content)
    # Should not include empty link
    assert "" not in links
    assert "header_target" in links
    # Self link should be filtered or handled cleanly without graph circular deadlock
    res = bridge.persist(mark)
    assert res["status"] == "PRECIPITATED"
