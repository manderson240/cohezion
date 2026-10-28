"""Unit tests for The Trinity: Capability-Driven RSI Engine (arXiv:2610.36077)."""

from cohezion.agi.trinity_engine import (
    CapabilityAwareRouter,
    CapabilityRequirement,
    CapabilityTree,
    HarnessModule,
    HarnessRegistry,
    HarnessTree,
    TheTrinityEngine,
)


def test_capability_requirement_digest():
    req1 = CapabilityRequirement(
        name="arithmetic_invariance",
        description="Verify arithmetic overflow/truncation",
        verification_rule="x * y / z == expected",
    )
    req2 = CapabilityRequirement(
        name="arithmetic_invariance",
        description="Different description, same name and rule",
        verification_rule="x * y / z == expected",
    )
    assert req1.digest() == req2.digest()
    assert len(req1.digest()) == 12


def test_capability_tree_trie_construction():
    tree = CapabilityTree()
    assert tree.root.is_root()
    assert tree.total_nodes == 1

    req_a = CapabilityRequirement("auth", "Auth verification", "has_permission")
    req_b = CapabilityRequirement("crypto", "Signature verification", "verify_signature")
    req_c = CapabilityRequirement("rate_limit", "Window rate check", "check_rate")

    # Insert Task 1 with {auth, crypto}
    path1 = tree.insert_task_capabilities("task_1", [req_b, req_a])
    # Alphabetical sorting -> auth, crypto
    assert path1 == ["root", "root/auth", "root/auth/crypto"]
    assert tree.total_nodes == 3

    # Insert Task 2 with {auth, rate_limit} -> shares 'root/auth'
    path2 = tree.insert_task_capabilities("task_2", [req_a, req_c])
    assert path2 == ["root", "root/auth", "root/auth/rate_limit"]
    assert tree.total_nodes == 4

    node_auth = tree.get_node("root/auth")
    assert node_auth is not None
    assert "crypto" in node_auth.children
    assert "rate_limit" in node_auth.children

    node_crypto = tree.get_node("root/auth/crypto")
    assert node_crypto is not None
    assert "task_1" in node_crypto.associated_task_ids


def test_harness_registry_right_biased_union():
    mod_a1 = HarnessModule(
        module_id="mod_a",
        capability_name="auth",
        version=1,
        execute_fn=lambda p: {"auth": "v1"},
    )
    mod_b = HarnessModule(
        module_id="mod_b",
        capability_name="crypto",
        version=1,
        execute_fn=lambda p: {"crypto": "v1"},
    )
    mod_a2 = HarnessModule(
        module_id="mod_a",
        capability_name="auth",
        version=2,
        execute_fn=lambda p: {"auth": "v2"},
    )

    parent_reg = HarnessRegistry()
    parent_reg.register(mod_a1)
    parent_reg.register(mod_b)

    local_reg = HarnessRegistry()
    local_reg.register(mod_a2)

    # Union P ⊕ L: local mod_a (v2) should override parent mod_a (v1); mod_b retained
    effective = parent_reg.right_biased_union(local_reg)
    assert effective.get("mod_a").version == 2
    assert effective.get("mod_b").version == 1
    assert effective.get("mod_a").execute({}) == {"auth": "v2"}


def test_harness_tree_selective_inheritance():
    cap_tree = CapabilityTree()
    req = CapabilityRequirement("calc", "Calculation", "rule_1")
    path = cap_tree.insert_task_capabilities("calc_task", [req])
    node_id = path[-1]  # "root/calc"

    harness_tree = HarnessTree(cap_tree)

    # Local module
    local_mod = HarnessModule(
        module_id="calc_mod",
        capability_name="calc",
        version=1,
        execute_fn=lambda p: {"result": 42},
    )
    local_reg = HarnessRegistry()
    local_reg.register(local_mod)

    # 1. Acceptance test: score >= previous score
    retained_1 = harness_tree.selective_inheritance(
        node_id=node_id,
        local_registry=local_reg,
        eval_fn=lambda reg: 0.95,
    )
    assert retained_1.get("calc_mod") is not None
    assert retained_1.get("calc_mod").version == 1

    # 2. Rejection test: score drops below previous score
    # Evaluate with regression: candidate gets 0.40, while previous registry maintained >= 0.95
    regression_mod = HarnessModule(
        module_id="calc_mod",
        capability_name="calc",
        version=2,
        execute_fn=lambda p: {"result": -1},
    )
    regression_reg = HarnessRegistry()
    regression_reg.register(regression_mod)

    retained_2 = harness_tree.selective_inheritance(
        node_id=node_id,
        local_registry=regression_reg,
        eval_fn=lambda reg: 0.40 if reg.get("calc_mod").version == 2 else 0.95,
    )
    # The regression candidate should be rejected, preserving the version 1 module
    assert retained_2.get("calc_mod").version == 1


def test_capability_aware_router():
    cap_tree = CapabilityTree()
    req1 = CapabilityRequirement("nlp", "Text Processing", "parse")
    req2 = CapabilityRequirement("code", "Code Execution", "exec")
    cap_tree.insert_task_capabilities("task_code", [req1, req2])

    harness_tree = HarnessTree(cap_tree)
    # Register dummy harness in the tree
    reg = HarnessRegistry()
    harness_tree.node_registries["root/code/nlp"] = (reg, reg, reg)

    router = CapabilityAwareRouter(cap_tree, harness_tree, max_memory=3)

    # Route with code and nlp capabilities
    selected = router.route(
        task_context={"name": "test_script"},
        required_capabilities=["code", "nlp"],
    )
    assert selected == "root/code/nlp"

    # Memory FIFO bounds test
    router.record_outcome({"task": 1}, "root", 0.8, 10.0)
    router.record_outcome({"task": 2}, "root", 0.9, 12.0)
    router.record_outcome({"task": 3}, "root", 0.95, 8.0)
    assert len(router.memory) == 3

    router.record_outcome({"task": 4}, "root", 0.99, 5.0)
    assert len(router.memory) == 3
    assert router.memory[0].task_context["task"] == 2
    assert router.memory[-1].task_context["task"] == 4


def test_the_trinity_engine_orchestration():
    trinity = TheTrinityEngine()

    # Evolver
    req = CapabilityRequirement("verification", "Formal proofs", "poly_verify")
    path = trinity.register_capability_requirement("bounty_task", [req])
    assert path == ["root", "root/verification"]

    # Creator
    def mock_sim_generator():
        return {"env": "solana_test_validator", "slots": 100}

    world = trinity.create_sim_world("root/verification", mock_sim_generator)
    assert world["capability_node_id"] == "root/verification"
    assert world["env"] == "solana_test_validator"

    # Explorer
    mod = HarnessModule(
        module_id="zkfv_verifier",
        capability_name="verification",
        version=1,
        execute_fn=lambda p: {"status": "proven"},
    )
    retained_harness = trinity.evolve_node_harness(
        node_id="root/verification",
        local_modules=[mod],
        eval_fn=lambda reg: 1.0,
    )
    assert retained_harness.get("zkfv_verifier") is not None

    # Router
    route_node = trinity.router.route({"name": "solana_audit"}, ["verification"])
    assert route_node == "root/verification"
