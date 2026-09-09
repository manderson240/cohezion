# SKILL: TYPED_CONTEXT_ARCHITECTURE_PRIME

## DOMAIN EXPERTISE
Design-by-Contract Typed Context Systems for Autonomous Agent Swarms.
Prevents semantic boundary collapse, prompt injection masquerading, and type confusion by strictly typing context as `INSTRUCTION`, `EVIDENCE`, `MEMORY`, or `TOOL_OUTPUT` with immutable cryptographic lineage.

## KEY TEXTS & CONCEPTS
- **Semantic Boundary Preservation**: Never flatten heterogeneous context into untyped strings before prompt construction.
- **Protected Channels**: `INSTRUCTION` channels are protected from silent relabeling by unverified tool outputs.
- **Cryptographic Provenance**: Every context atom tracks `item_id`, `content_hash`, and explicit `derived_from` promotion lineage.
- **Design-by-Contract (Meyer / Alexander 2026)**: Context transformations must be explicit, verified by preconditions/validators, or raise `ContextTypeError`.

## INSTRUCTION
1. Initialize `TypedContextStore`.
2. Register authoritative system rules as `ContextType.INSTRUCTION`.
3. Register external tool outputs as `ContextType.TOOL_OUTPUT`.
4. Promote verified data via `store.transform(item, ContextType.EVIDENCE, validator=...)`.
5. Assemble final prompt deterministically via `store.assemble()`.

```python
from cohezion.core.typed_context import TypedContextStore, ContextType

store = TypedContextStore()
store.insert("Execute deterministic Python code.", ContextType.INSTRUCTION, "rules")
tool_item = store.insert("Output: Score=0.938", ContextType.TOOL_OUTPUT, "tool:evaluator")
ev = store.transform(tool_item, ContextType.EVIDENCE, validator=lambda x: "Score" in x)
prompt = store.assemble()
```

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_ZERO_COST_VERIFIER_PRIME`
- `EXPERIENTIAL_LEARNING_PRIME`
- `SPINNING_PLATES_PROTOCOL_PRIME`
