"""Typed Context Runtime System for Cohezion Agents.

Based on Design-by-Contract Context Typing (Alexander, 2026):
Enforces explicit context types (`INSTRUCTION`, `EVIDENCE`, `MEMORY`, `TOOL_OUTPUT`)
with strict provenance tracking, ledger boundary validation, and illegal type promotion rejection.
"""

from __future__ import annotations

import enum
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class ContextType(str, enum.Enum):
    """Core context classifications."""
    INSTRUCTION = "INSTRUCTION"   # Authoritative agent instructions & rules
    EVIDENCE = "EVIDENCE"         # Verified external facts, code ASTs, benchmark results
    MEMORY = "MEMORY"             # Long-term recall from SurrealDB & Obsidian Vault
    TOOL_OUTPUT = "TOOL_OUTPUT"   # Raw runtime outputs from tools, daemons & APIs


class ContextTypeError(Exception):
    """Raised when an illegal context transformation or type confusion occurs."""
    pass


@dataclass(frozen=True)
class ContextItem:
    """Immutable, typed context atom with cryptographic lineage."""
    content: str
    context_type: ContextType
    source: str
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: float = field(default_factory=time.time)
    derived_from: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.strip().encode("utf-8")).hexdigest()[:16]


class TypedContextStore:
    """Provenance ledger and contract-enforced context store."""

    PROTECTED_TYPES = {ContextType.INSTRUCTION}
    ALLOWED_TRANSITIONS = {
        (ContextType.TOOL_OUTPUT, ContextType.EVIDENCE),
        (ContextType.EVIDENCE, ContextType.MEMORY),
        (ContextType.MEMORY, ContextType.EVIDENCE),
    }

    def __init__(self) -> None:
        self._items: list[ContextItem] = []
        # Ledger maps content_hash -> (origin_type, item_id)
        self._ledger: dict[str, tuple[ContextType, str]] = {}

    def insert(
        self,
        content: str,
        context_type: ContextType,
        source: str,
        metadata: dict[str, Any] | None = None,
        _via_transform: bool = False,
        _derived_from: str | None = None,
    ) -> ContextItem:
        """Insert a typed context item, enforcing contract boundaries."""
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Context content cannot be empty")

        key = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()[:16]
        existing = self._ledger.get(key)

        if existing is not None:
            origin_type, origin_id = existing
            if origin_type != context_type:
                if context_type in self.PROTECTED_TYPES and not _via_transform:
                    raise ContextTypeError(
                        f"Type Confusion Detected: Content registered as {origin_type.value} (id={origin_id}) "
                        f"cannot be silently injected into protected {context_type.value} channel!"
                    )

        item = ContextItem(
            content=clean_content,
            context_type=context_type,
            source=source,
            derived_from=_derived_from,
            metadata=metadata or {},
        )

        self._items.append(item)
        if key not in self._ledger:
            self._ledger[key] = (context_type, item.item_id)

        return item

    def transform(
        self,
        item: ContextItem,
        target_type: ContextType,
        validator: Any = None,
    ) -> ContextItem:
        """Explicitly promote/transform context with verification & lineage tracking."""
        pair = (item.context_type, target_type)
        if pair not in self.ALLOWED_TRANSITIONS:
            raise ContextTypeError(
                f"Illegal context transformation: Cannot transform {item.context_type.value} -> {target_type.value}"
            )

        if validator and not validator(item.content):
            raise ContextTypeError(f"Validation failed for transformation {pair}: content rejected")

        return self.insert(
            content=item.content,
            context_type=target_type,
            source=f"transformed:{item.source}",
            metadata=item.metadata,
            _via_transform=True,
            _derived_from=item.item_id,
        )

    def assemble(self) -> str:
        """Deterministically serializes typed context into labeled sections."""
        instructions = [it for it in self._items if it.context_type == ContextType.INSTRUCTION]
        memory = [it for it in self._items if it.context_type == ContextType.MEMORY]
        evidence = [it for it in self._items if it.context_type == ContextType.EVIDENCE]
        tool_outputs = [it for it in self._items if it.context_type == ContextType.TOOL_OUTPUT]

        sections = []

        if instructions:
            sections.append("=== [INSTRUCTIONS & CONTRACTS] ===\n" + "\n\n".join(f"[{i.source}] {i.content}" for i in instructions))
        if memory:
            sections.append("=== [PERSISTENT MEMORY & RECALL] ===\n" + "\n\n".join(f"[{m.source} (id={m.item_id})] {m.content}" for m in memory))
        if evidence:
            sections.append("=== [VERIFIED EVIDENCE & PROOFS] ===\n" + "\n\n".join(f"[{e.source} (id={e.item_id}{f', derived_from={e.derived_from}' if e.derived_from else ''})] {e.content}" for e in evidence))
        if tool_outputs:
            sections.append("=== [RAW RUNTIME TOOL OUTPUTS] ===\n" + "\n\n".join(f"[{t.source}] {t.content}" for t in tool_outputs))

        return "\n\n".join(sections)

    def get_items_by_type(self, context_type: ContextType) -> list[ContextItem]:
        return [it for it in self._items if it.context_type == context_type]

    def audit_summary(self) -> dict[str, Any]:
        return {
            "total_items": len(self._items),
            "ledger_keys": len(self._ledger),
            "counts_by_type": {
                t.value: len([i for i in self._items if i.context_type == t])
                for t in ContextType
            }
        }
