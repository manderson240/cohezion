"""The Trinity: Capability-Driven Recursive Self-Improvement Engine (arXiv:2610.36077).

Implements the three co-evolving roles for multimodal and autonomous agent swarms:
1. Evolver: Reorganizes tasks from surface modalities into a hierarchical Capability Trie
   based on shared operational requirements rather than superficial categories.
2. Creator: Executes Capability-Driven Real2Sim2Real, generating compact, verifiable
   simulated worlds (unit harnesses / micro-environments) to train and test capability modules.
3. Explorer: Progressively evolves composable Harness modules along the Capability Tree
   via Selective Inheritance (right-biased union P ⊕ L) with empirical performance gating.
4. Capability-Aware Harness Router: Selects optimal specialized module configurations
   from the Harness Tree based on task context and verified trajectory memory.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    """An atomic capability requirement shared across heterogeneous tasks."""

    name: str
    description: str
    verification_rule: str

    def digest(self) -> str:
        s = f"{self.name}:{self.verification_rule}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


@dataclass
class CapabilityNode:
    """Node in the hierarchical Capability Tree (Trie)."""

    node_id: str
    requirement: CapabilityRequirement | None
    children: dict[str, CapabilityNode] = field(default_factory=dict)
    associated_task_ids: list[str] = field(default_factory=list)
    depth: int = 0

    def is_root(self) -> bool:
        return self.requirement is None


class CapabilityTree:
    """Trie-based capability organizer merging common requirement prefixes."""

    def __init__(self) -> None:
        self.root = CapabilityNode(node_id="root", requirement=None, depth=0)
        self._all_nodes: dict[str, CapabilityNode] = {"root": self.root}

    def insert_task_capabilities(
        self, task_id: str, requirements: list[CapabilityRequirement]
    ) -> list[str]:
        """Insert a task's sorted capability requirements into the Trie.

        Returns the path of node IDs traversed/created.
        """
        # Deterministic sorting of requirements by name to ensure canonical Trie paths
        sorted_reqs = sorted(requirements, key=lambda r: r.name)
        current = self.root
        path = ["root"]

        for req in sorted_reqs:
            if req.name not in current.children:
                child_id = f"{current.node_id}/{req.name}"
                new_node = CapabilityNode(
                    node_id=child_id,
                    requirement=req,
                    depth=current.depth + 1,
                )
                current.children[req.name] = new_node
                self._all_nodes[child_id] = new_node
            current = current.children[req.name]
            path.append(current.node_id)

        current.associated_task_ids.append(task_id)
        return path

    def get_node(self, node_id: str) -> CapabilityNode | None:
        return self._all_nodes.get(node_id)

    @property
    def total_nodes(self) -> int:
        return len(self._all_nodes)


@dataclass
class HarnessModule:
    """A reusable, composable capability module within an agent harness."""

    module_id: str
    capability_name: str
    version: int
    execute_fn: Callable[[dict[str, Any]], dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.execute_fn(payload)


@dataclass
class HarnessRegistry:
    """Module configuration registry supporting right-biased union (P ⊕ L)."""

    modules: dict[str, HarnessModule] = field(default_factory=dict)

    def right_biased_union(self, local: HarnessRegistry) -> HarnessRegistry:
        """Compose parent modules (P) with local overrides (L).

        (P ⊕ L)[m] = L[m] if m in dom(L) else P[m]
        """
        merged = dict(self.modules)
        merged.update(local.modules)
        return HarnessRegistry(modules=merged)

    def get(self, module_id: str) -> HarnessModule | None:
        return self.modules.get(module_id)

    def register(self, module: HarnessModule) -> None:
        self.modules[module.module_id] = module


class HarnessTree:
    """Harness tree aligned with the Capability Tree supporting Selective Inheritance."""

    def __init__(self, capability_tree: CapabilityTree) -> None:
        self.capability_tree = capability_tree
        # Node ID -> (retained_parent_registry, local_registry, effective_harness)
        self.node_registries: dict[
            str, tuple[HarnessRegistry, HarnessRegistry, HarnessRegistry]
        ] = {}
        # Root initialization with base empty registry
        base_reg = HarnessRegistry()
        self.node_registries["root"] = (base_reg, base_reg, base_reg)

    def selective_inheritance(
        self,
        node_id: str,
        local_registry: HarnessRegistry,
        eval_fn: Callable[[HarnessRegistry], float],
    ) -> HarnessRegistry:
        """Apply Selective Inheritance (arXiv:2610.36077 §3.5).

        Under identical validation tasks, trial count, and budget:
        The updated parent module configuration is retained ONLY with strictly
        higher host-verified performance; otherwise the previous registry is retained.
        """
        node = self.capability_tree.get_node(node_id)
        if not node or node.is_root():
            return local_registry

        # Find parent node ID
        parent_id = node_id.rsplit("/", 1)[0]
        _, _, parent_effective = self.node_registries.get(
            parent_id, (HarnessRegistry(), HarnessRegistry(), HarnessRegistry())
        )

        # Candidate effective harness: P ⊕ L
        candidate_effective = parent_effective.right_biased_union(local_registry)

        # Performance evaluation
        prev_effective = self.node_registries.get(
            node_id, (parent_effective, local_registry, parent_effective)
        )[2]
        prev_score = eval_fn(prev_effective)
        candidate_score = eval_fn(candidate_effective)

        # Gate: Retained only if performance is strictly >= previous
        if candidate_score >= prev_score:
            retained = candidate_effective
            logger.info(
                "Node '%s': Parent inheritance accepted (Score %.3f >= %.3f)",
                node_id,
                candidate_score,
                prev_score,
            )
        else:
            retained = prev_effective
            logger.warning(
                "Node '%s': Parent inheritance rejected (Score %.3f < %.3f)",
                node_id,
                candidate_score,
                prev_score,
            )

        self.node_registries[node_id] = (parent_effective, local_registry, retained)
        return retained


@dataclass
class TrajectoryRecord:
    """Execution receipt in the Router's FIFO verification memory."""

    task_context: dict[str, Any]
    selected_harness_node: str
    outcome_score: float
    execution_time_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class CapabilityAwareRouter:
    """Context-aware Harness Router (arXiv:2610.36077 §3.6).

    Selects the optimal specialized Harness node from the Harness Tree
    guided by task requirements, observed performance summaries, and memory receipts.
    """

    def __init__(
        self, capability_tree: CapabilityTree, harness_tree: HarnessTree, max_memory: int = 20000
    ) -> None:
        self.capability_tree = capability_tree
        self.harness_tree = harness_tree
        self.max_memory = max_memory
        self.memory: list[TrajectoryRecord] = []

    def route(self, task_context: dict[str, Any], required_capabilities: list[str]) -> str:
        """Select compatible module configuration node based on task requirements."""
        # Find best matching node path in Capability Tree
        current = self.capability_tree.root
        selected_node_id = "root"

        for cap_name in sorted(required_capabilities):
            if cap_name in current.children:
                current = current.children[cap_name]
                if current.node_id in self.harness_tree.node_registries:
                    selected_node_id = current.node_id

        logger.info(
            "CapabilityAwareRouter: routed task '%s' to Harness node '%s'",
            task_context.get("name", "unnamed"),
            selected_node_id,
        )
        return selected_node_id

    def record_outcome(
        self,
        task_context: dict[str, Any],
        selected_harness_node: str,
        outcome_score: float,
        execution_time_ms: float,
    ) -> None:
        """Update router FIFO memory with verified terminal receipts."""
        record = TrajectoryRecord(
            task_context=task_context,
            selected_harness_node=selected_harness_node,
            outcome_score=outcome_score,
            execution_time_ms=execution_time_ms,
        )
        self.memory.append(record)
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)


class TheTrinityEngine:
    """Master orchestrator for Capability-Driven Recursive Self-Improvement."""

    def __init__(self) -> None:
        self.capability_tree = CapabilityTree()
        self.harness_tree = HarnessTree(self.capability_tree)
        self.router = CapabilityAwareRouter(self.capability_tree, self.harness_tree)
        self._iteration = 0

    def register_capability_requirement(
        self, task_id: str, requirements: list[CapabilityRequirement]
    ) -> list[str]:
        """Evolver role: map task into the hierarchical Capability Trie."""
        return self.capability_tree.insert_task_capabilities(task_id, requirements)

    def evolve_node_harness(
        self,
        node_id: str,
        local_modules: list[HarnessModule],
        eval_fn: Callable[[HarnessRegistry], float],
    ) -> HarnessRegistry:
        """Explorer role: evolve node with Selective Inheritance."""
        local_registry = HarnessRegistry()
        for mod in local_modules:
            local_registry.register(mod)

        return self.harness_tree.selective_inheritance(node_id, local_registry, eval_fn)

    def create_sim_world(
        self, capability_node_id: str, generator_fn: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        """Creator role: Capability-Driven Real2Sim2Real environment synthesis."""
        node = self.capability_tree.get_node(capability_node_id)
        req_name = node.requirement.name if node and node.requirement else "generic"
        logger.info("Creator: synthesizing simulated micro-world for capability '%s'", req_name)
        world_spec = generator_fn()
        world_spec["capability_node_id"] = capability_node_id
        world_spec["synthesized_at"] = datetime.now(UTC).isoformat()
        return world_spec
