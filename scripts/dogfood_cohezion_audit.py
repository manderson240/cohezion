#!/usr/bin/env python3
"""Cohezion Dogfooding Execution Script.

Dogfoods our newly created primitives directly on Cohezion's own codebase:
1. Open Ontologies: Builds AST semantic dependency graph and calculates blast radius for core infrastructure.
2. AutoHarness Policy: Audits all python source files for unit consistency, bare excepts, and dangerous calls.
3. The Trinity Engine: Maps Cohezion's core capabilities into a canonical Trie and synthesizes a micro-world.
"""

from __future__ import annotations

import ast
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any


# Ensure src/ is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from cohezion.agi.autoharness_policy import AutoHarnessPolicy  # noqa: E402
from cohezion.agi.trinity_engine import (  # noqa: E402
    CapabilityRequirement,
    HarnessModule,
    TheTrinityEngine,
)
from cohezion.knowledge_graph.open_ontologies_bridge import (  # noqa: E402
    SemanticPlan,
    SemanticPlanner,
    SemanticTriple,
)


logger = logging.getLogger(__name__)


def run_autoharness_audit(src_dir: Path) -> dict[str, Any]:
    print(f"[*] Running AutoHarness AST Audit across {src_dir}...")
    policy = AutoHarnessPolicy(policy_name="cohezion_internal_hound")

    total_files = 0
    total_ast_nodes = 0
    total_latency_ms = 0.0
    violations_by_file: dict[str, list[str]] = {}
    rule_counts: dict[str, int] = {}

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = Path(root) / file
            rel_path = path.relative_to(src_dir)
            total_files += 1

            try:
                content = path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[!] Warning reading {rel_path}: {e}")
                continue

            result = policy.verify_code(content)
            total_ast_nodes += result.ast_nodes_scanned
            total_latency_ms += result.latency_ms

            if not result.valid:
                violations_by_file[str(rel_path)] = result.violations
                for v in result.violations:
                    rule = v.split(":")[0]
                    rule_counts[rule] = rule_counts.get(rule, 0) + 1

    avg_latency = total_latency_ms / max(1, total_files)
    print(
        f"[+] Scanned {total_files} files ({total_ast_nodes:,} AST nodes) in {total_latency_ms:.2f}ms (avg {avg_latency:.3f}ms/file)"
    )
    print(f"[+] Found {len(violations_by_file)} files with policy findings.")

    return {
        "total_files": total_files,
        "total_ast_nodes": total_ast_nodes,
        "total_latency_ms": total_latency_ms,
        "avg_latency_ms": avg_latency,
        "violations_by_file": violations_by_file,
        "rule_counts": rule_counts,
    }


def run_semantic_blast_radius_audit(src_dir: Path) -> dict[str, Any]:
    print("[*] Building Semantic AST Dependency Graph for Open Ontologies Audit...")
    triples: list[SemanticTriple] = []

    # Map imports across core subsystems
    core_dirs = ["core", "agi", "data_mesh", "compound", "inference"]
    for sub in core_dirs:
        sub_path = src_dir / "cohezion" / sub
        if not sub_path.exists():
            continue
        for py_file in sub_path.glob("*.py"):
            mod_name = f"cohezion.{sub}.{py_file.stem}"
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except Exception as err:
                logger.debug("Failed parsing %s: %s", py_file, err)
                continue

            triples.append(SemanticTriple(mod_name, "rdf:type", "cohezion:Module"))
            triples.append(SemanticTriple(mod_name, "cohezion:subsystem", f"cohezion:{sub}"))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("cohezion"):
                            triples.append(SemanticTriple(mod_name, "cohezion:imports", alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("cohezion"):
                        triples.append(SemanticTriple(mod_name, "cohezion:imports", node.module))
                elif isinstance(node, ast.ClassDef):
                    cls_name = f"{mod_name}.{node.name}"
                    triples.append(SemanticTriple(cls_name, "rdf:type", "cohezion:Class"))
                    triples.append(SemanticTriple(cls_name, "cohezion:definedIn", mod_name))

    print(f"[+] Extracted {len(triples)} semantic assertions across core modules.")

    # Simulate proposed mutation to core EventBus & KanbanBridge
    proposed_changes = [
        SemanticTriple("cohezion.core.event_bus", "cohezion:schema_version", "v3.0"),
        SemanticTriple("cohezion.data_mesh.kanban_bridge", "cohezion:schema_version", "v3.0"),
        SemanticTriple("cohezion:v3.0", "rdfs:subClassOf", "cohezion:BreakingMigration"),
    ]

    planner = SemanticPlanner()
    plan: SemanticPlan = planner.plan(base_graph=triples, proposed_changes=proposed_changes)

    # Generate and verify derivation certificate
    cert = plan.derived_certificate
    cert_valid = False
    cert_msg = "No certificate"
    if cert:
        cert_valid, cert_msg = cert.verify()
    print(f"[+] Blast Radius: {plan.blast_radius} existing entities directly touched.")
    print(f"[+] Consequence Count: {plan.consequence_count} forward-chaining deductions.")
    print(f"[+] Conservativity: {plan.conservativity} (Risk: {plan.risk_score}).")
    print(f"[+] Zero-Trust Derivation Certificate: {cert_msg} (Valid: {cert_valid}).")

    return {
        "total_triples": len(triples),
        "blast_radius": plan.blast_radius,
        "consequences": plan.consequence_count,
        "conservativity": plan.conservativity,
        "risk_score": plan.risk_score,
        "cert_valid": cert_valid,
        "cert_message": cert_msg,
        "planning_time_ms": plan.planning_time_ms,
    }


def run_trinity_dogfooding() -> dict[str, Any]:
    print("[*] Dogfooding The Trinity Engine on Cohezion Core Capabilities...")
    trinity = TheTrinityEngine()

    # 1. Evolver: Define atomic capabilities for Cohezion
    req_vram = CapabilityRequirement("vram_guard", "UMA aperture monitor", "free_gtt >= 10.0")
    req_async = CapabilityRequirement("async_timeout", "Strict IO timeout", "timeout <= 30.0")
    req_autoharness = CapabilityRequirement(
        "autoharness_gate", "Zero-cost AST verification", "violations == 0"
    )

    path_fleet = trinity.register_capability_requirement("task_fleet_lock", [req_vram, req_async])
    path_ci = trinity.register_capability_requirement(
        "task_ci_automerge", [req_autoharness, req_async]
    )

    # 2. Creator: Synthesize micro-world testbed
    def make_cohezion_microworld():
        return {
            "gtt_available_gb": 18.5,
            "uma_aperture_active": True,
            "fleet_locks": ["fleet_lock:modelload"],
            "simulated_latency_ms": 1.25,
        }

    world = trinity.create_sim_world("root/async_timeout/vram_guard", make_cohezion_microworld)

    # 3. Explorer: Selective Inheritance evolution
    mod_v1 = HarnessModule(
        module_id="fleet_guard_v1",
        capability_name="vram_guard",
        version=1,
        execute_fn=lambda p: {"status": "safe", "gtt_gb": p.get("gtt_available_gb", 0)},
    )
    _ = trinity.evolve_node_harness(
        node_id="root/async_timeout/vram_guard",
        local_modules=[mod_v1],
        eval_fn=lambda reg: 1.0,
    )

    # 4. Router: Select and execute
    route_node = trinity.router.route(
        task_context={"name": "swam_dispatch_job"},
        required_capabilities=["async_timeout", "vram_guard"],
    )
    trinity.router.record_outcome(
        task_context={"name": "swam_dispatch_job"},
        selected_harness_node=route_node,
        outcome_score=1.0,
        execution_time_ms=0.85,
    )

    print(f"[+] Capability Trie Total Nodes: {trinity.capability_tree.total_nodes}")
    print(f"[+] Fleet Lock Path: {path_fleet}")
    print(f"[+] CI Automerge Path: {path_ci}")
    print(f"[+] Routed Node: {route_node}")
    print(f"[+] Simulated Micro-World: {world['gtt_available_gb']} GB GTT, {world['fleet_locks']}")

    return {
        "total_nodes": trinity.capability_tree.total_nodes,
        "fleet_path": path_fleet,
        "ci_path": path_ci,
        "routed_node": route_node,
        "router_memory_len": len(trinity.router.memory),
    }


def main():
    src_dir = repo_root / "src"
    t0 = time.time()
    print("=================================================================")
    print("COHEZION RECURSIVE DOGFOODING SUITE: AUDITING COHEZION VIA COHEZION")
    print("=================================================================\n")

    _harness_res = run_autoharness_audit(src_dir)
    print()
    _ontologies_res = run_semantic_blast_radius_audit(src_dir)
    print()
    _trinity_res = run_trinity_dogfooding()
    print()

    total_time = time.time() - t0
    print("=================================================================")
    print(f"Dogfooding execution completed in {total_time:.2f}s")
    print("=================================================================")


if __name__ == "__main__":
    main()
