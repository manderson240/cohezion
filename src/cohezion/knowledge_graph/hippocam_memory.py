r"""Hippocam: Continual Learning through Structured Memory Consolidation
===================================================================
Synthesizes arXiv:2610.12124:
"Hippocam: Continual Learning through Structured Memory Consolidation in LLM Agents"

Key Formalisms:
1. Nested Intent Stack:
   - I = <i_1, ..., i_d>, where i_j = <p_j, chi_j, b_j>
   - p: Purpose of ongoing work
   - chi: Success / failure exit conditions
   - b: Start index of governed messages

2. Tri-Agent Engine:
   - Janus: Intent Governor handling 4 operations (Continue, Deepen, Close, Shift).
   - Precip: Intent Consolidator decoupling Narrative (episodic execution trace)
     from Knowledge (unbound facts, invariants, lessons) with explicit provenance.
   - Palim: Prefix Consolidator performing recursive abstraction on disused prefixes
     preceding the active working tail while preserving the hierarchical Message Tree.

3. Progressive Recall:
   - Allows agents to dynamically query the message tree via `recall_message(id)`
     to recover fine-grained operational context without context-window saturation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


class IntentOperation(StrEnum):
    """The four intent maintenance operations executed by Janus."""

    CONTINUE = "CONTINUE"  # Preserve stack; current intent remains active
    DEEPEN = "DEEPEN"  # Open a more specific sub-intent within current chain
    CLOSE = "CLOSE"  # Conclude and pop concluded suffix
    SHIFT = "SHIFT"  # Close concluded suffix and push next direction


@dataclass
class Intent:
    """A bounded purpose governing a contiguous region of agent context."""

    intent_id: str
    purpose: str
    exit_conditions: str
    start_message_idx: int
    is_closed: bool = False
    closed_outcome: str | None = None  # SUCCESS, FAILURE, ABANDONED
    closed_at: float | None = None


@dataclass
class ConsolidatedMemoryNode:
    """A node in the hierarchical Hippocam Message Tree."""

    node_id: str
    intent_id: str
    level: int  # 0 = raw, 1 = intent-consolidated, 2+ = prefix-consolidated
    narrative: str  # First-person chronological recount of actions and results
    knowledge: list[dict[str, Any]]  # Unbound facts, invariants, and lessons
    provenance: list[str]  # Source file paths, execution receipts, commit hashes
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class IntentStack:
    """Dynamically maintained nested intent stack I = <i_1, ..., i_d>."""

    def __init__(self) -> None:
        self.stack: list[Intent] = []

    @property
    def current(self) -> Intent | None:
        return self.stack[-1] if self.stack else None

    @property
    def depth(self) -> int:
        return len(self.stack)

    def push(self, intent: Intent) -> None:
        self.stack.append(intent)

    def pop(self) -> Intent | None:
        return self.stack.pop() if self.stack else None

    def close_current(self, outcome: str) -> Intent | None:
        if self.stack:
            curr = self.stack.pop()
            curr.is_closed = True
            curr.closed_outcome = outcome
            curr.closed_at = time.time()
            return curr
        return None


class JanusGovernor:
    """Intent maintenance engine.

    Inspects current context and determines whether to Continue, Deepen, Close, or Shift.
    """

    @staticmethod
    def evaluate_intent(
        stack: IntentStack,
        latest_observation: str,
        current_msg_idx: int,
    ) -> tuple[IntentOperation, str]:
        """Evaluates ongoing work against active exit conditions."""
        current = stack.current
        if current is None:
            return IntentOperation.CONTINUE, "Empty stack."

        obs_lower = latest_observation.lower()

        # Check if exit condition is met
        if any(term in obs_lower for term in ("verified", "success", "completed", "resolved")):
            return IntentOperation.CLOSE, f"Exit condition met for intent '{current.purpose}'."

        if any(term in obs_lower for term in ("subtask", "explore", "drilldown", "sub-problem")):
            return (
                IntentOperation.DEEPEN,
                f"Subtask detected; deepening stack under '{current.purpose}'.",
            )

        if any(term in obs_lower for term in ("blocked", "pivot", "alternative", "shift")):
            return (
                IntentOperation.SHIFT,
                f"Blocker detected; shifting away from '{current.purpose}'.",
            )

        return IntentOperation.CONTINUE, f"Preserving intent '{current.purpose}'."


class PrecipConsolidator:
    """Intent consolidation engine.

    When an intent closes, Precip extracts a self-contained synthesis separating:
    - Narrative: chronological account of actions and outcomes.
    - Knowledge: reusable unbound facts, physical invariants, and rules.
    """

    @staticmethod
    def consolidate_intent(
        closed_intent: Intent,
        raw_messages: list[dict[str, Any]],
        tree_parent_id: str | None = None,
    ) -> ConsolidatedMemoryNode:
        node_id = f"precip_{closed_intent.intent_id}_{int(time.time())}"

        # 1. Synthesize Narrative
        actions_taken = [
            m.get("content", "")[:120]
            for m in raw_messages
            if m.get("role") in ("assistant", "agent")
        ]
        narrative = (
            f"Intent '{closed_intent.purpose}' concluded with status {closed_intent.closed_outcome}.\n"
            f"Actions Executed: {len(actions_taken)} steps. "
            f"Key path: {' -> '.join(actions_taken[:3])}"
        )

        # 2. Extract Reusable Unbound Knowledge
        knowledge: list[dict[str, Any]] = []
        for m in raw_messages:
            content = m.get("content", "")
            if "invariant" in content.lower() or "lesson" in content.lower():
                knowledge.append(
                    {
                        "subject": closed_intent.purpose,
                        "insight": content[:200],
                        "outcome": closed_intent.closed_outcome,
                    }
                )

        # 3. Collect Provenance
        provenance = [m.get("source", "runtime") for m in raw_messages if "source" in m]

        return ConsolidatedMemoryNode(
            node_id=node_id,
            intent_id=closed_intent.intent_id,
            level=1,
            narrative=narrative,
            knowledge=knowledge,
            provenance=list(set(provenance)),
            parent_id=tree_parent_id,
            child_ids=[m.get("id", str(i)) for i, m in enumerate(raw_messages)],
        )


class PalimPrefixTree:
    """Prefix consolidation and progressive recall tree.

    Recursively consolidates disused older memory nodes into higher-level abstractions
    while preserving child references for on-demand inspection via `recall()`.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, ConsolidatedMemoryNode] = {}
        self.root_node_ids: list[str] = []

    def insert(self, node: ConsolidatedMemoryNode) -> None:
        self.nodes[node.node_id] = node
        if node.parent_id is None:
            self.root_node_ids.append(node.node_id)
        elif node.parent_id in self.nodes:
            self.nodes[node.parent_id].child_ids.append(node.node_id)

    def consolidate_prefix(
        self,
        node_ids_to_merge: list[str],
        higher_purpose: str,
    ) -> ConsolidatedMemoryNode | None:
        """Merges multiple level-1 intent nodes into a level-2 abstract semantic node."""
        if not node_ids_to_merge:
            return None

        merged_id = f"palim_prefix_{int(time.time())}"
        merged_knowledge: list[dict[str, Any]] = []
        merged_provenance: list[str] = []
        narrative_summaries: list[str] = []

        for nid in node_ids_to_merge:
            node = self.nodes.get(nid)
            if node:
                merged_knowledge.extend(node.knowledge)
                merged_provenance.extend(node.provenance)
                narrative_summaries.append(node.narrative)

        combined_narrative = (
            f"Prefix consolidation of {len(node_ids_to_merge)} intents under '{higher_purpose}':\n"
            + "\n".join(f"- {s}" for s in narrative_summaries[:5])
        )

        higher_node = ConsolidatedMemoryNode(
            node_id=merged_id,
            intent_id=higher_purpose,
            level=2,
            narrative=combined_narrative,
            knowledge=merged_knowledge,
            provenance=list(set(merged_provenance)),
            child_ids=node_ids_to_merge,
        )

        for nid in node_ids_to_merge:
            if nid in self.nodes:
                self.nodes[nid].parent_id = merged_id

        self.insert(higher_node)
        return higher_node

    def recall(self, node_id: str) -> ConsolidatedMemoryNode | None:
        """Progressive recall: retrieves fine-grained node details and children."""
        return self.nodes.get(node_id)

    def search_knowledge(self, query: str) -> list[dict[str, Any]]:
        """Queries unbound semantic invariants across the memory tree."""
        matches: list[dict[str, Any]] = []
        q_lower = query.lower()
        for node in self.nodes.values():
            for k in node.knowledge:
                if q_lower in str(k).lower():
                    matches.append({**k, "node_id": node.node_id, "level": node.level})
        return matches
