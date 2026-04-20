# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

Rationale: Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Structured Config Files: YAML Frontmatter Markdown

When creating config/state files that humans may read or that integrate with the vault ecosystem, use **YAML frontmatter markdown** (not JSON):

```markdown
---
version: "1.0.0"
structured_data: here
---

# Human-Readable Title

Narrative context, rationale, and documentation below the frontmatter.
```

**Why:** Consistent with vault (`cerebellum/`), skills (`*.md`), `.context/skills/`, and the learned-budgets policy. Vault tools (vault-keeper, Obsidian) can index YAML frontmatter. The markdown body allows narrative context that JSON cannot express.

**When JSON is appropriate:** Internal wire formats (MCP responses, API payloads), files never read by humans, high-frequency machine-to-machine data.

## Systems Engineering V-Model (MANDATORY for non-trivial changes)

Every change has a left branch (what you build) and a right branch (how you verify it). Deterministic gates constrain nondeterministic work.

**Left Branch (Decomposition):**
1. Intent → What problem does this solve?
2. Plan → What's the approach? (spec-plan or inline comment)
3. Architecture → Which files/modules are affected?
4. Implementation → The actual code

**Right Branch (Verification):**
1. Unit tests ← TDD for implementation
2. Integration tests ← Cross-module interaction
3. System validation ← spec-verify or adversarial review
4. Acceptance ← Retrospection: did we deliver what was asked?

**Proof Obligations:** For physics/simulation code, include deterministic invariant checks:
- Energy conservation: `E(t=0) ≈ E(t=final)`
- Unitarity: `|ψ|² = 1` after state transitions
- HIHO stability: `coherence ∈ [0.3, 0.7]` for stable states
- Gauge invariance: `∇·B = 0` for field computations

**Hash-Lock Rule:** Tests written during specification MUST NOT be weakened during implementation. When using /spec, test hashes are checked at verification.

**Traceability:** Every requirement should map to a test (`traces` table in SurrealDB). If you add a feature, add a test. If you add a test, link it to a requirement.

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)
- [ ] Proof obligations pass (if physics/simulation code)
- [ ] Traceability link exists (requirement ↔ test)
