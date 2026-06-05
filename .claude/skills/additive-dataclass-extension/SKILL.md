---
name: additive-dataclass-extension
description: Use when adding a new field to an existing, heavily-instantiated dataclass. The pattern: add `Optional[T] = None`, never break existing call sites. Discovered in the WS2A card-aligned registry extension (PR #219) where 14 default ModelEntry records gained a `profile` field with zero test breakage.
when_to_use: |
  - Adding a new field to a `@dataclass` that has ≥ 3 production call sites
  - The new field is "nice to have" but not required for correctness
  - You want to land the change in one PR without breaking 100+ existing tests
when_not_to_use: |
  - The new field is REQUIRED for correctness (e.g. a primary key) — break the signature, not optional
  - The class has zero or one call sites — just edit the signature
  - The field is a discriminated union — use a tagged union pattern, not Optional[T]
decision_tree: |
  Is the new field required for correctness?
  ├─ YES → break the signature, fix all call sites in the same commit
  └─ NO  → Is it a discriminated union over a fixed set of kinds?
            ├─ YES → use a tagged union (Union[A, B] with discriminator)
            └─ NO  → use the additive pattern:
                      field_name: Optional[T] = None
                      # or, for a true default:
                      field_name: T = field(default_factory=...)
worked_example: |
  PR #219 (WS2A) added `profile: CapabilityProfile | None = None` to
  `ModelEntry`. The dataclass was instantiated in 14 places in
  `_build_default_registry` and tested in 422 pre-existing tests.
  All tests passed without modification because:
    1. The new field has a default of `None`
    2. The `from __future__ import annotations` is in place
    3. The `Optional[...]` annotation is a string (forward ref) so
       the import isn't required
  Result: 0 regressions, 1 PR, no migration.
anti_patterns:
  - Adding a required field as the last positional arg. Breaks every
    keyword-only call site that omits later args.
  - Wrapping the existing class in a subclass "to add a field". The
    type system can't see the field without isinstance checks.
  - Using `**kwargs` to "future-proof". Hides fields from linters
    and type checkers.
  - Adding `field(metadata={"deprecated": True})` to an old field
    without removing it. Additive only works for *new* fields.
  - Editing the @dataclass decorator to add a custom `__init__` that
    silently drops the new field. Now your type is a lie.
related_skills:
  - cohezion-dynamic-modularity (module-level additive composition)
  - compound-build (the build ritual that surfaced this pattern)
  - cohezion-extend-availability (the recursive-forge sweep that found
    the 0-production-callers issue)
verification:
  before_landing:
    - `grep -rn "class ModelEntry\|ModelEntry(" src/ --include="*.py" | grep -v test | wc -l`
      should match the call-site count. If < 3, just edit the signature.
    - `pytest tests/ -q` must pass on the pre-change branch.
  after_landing:
    - `pytest tests/ -q` must pass on the post-change branch.
    - No `__init__` was added to the dataclass.
    - The new field has a default of `None` (or a callable factory).
honest_residuals:
  - The Optional[T] default of None means the field is *also* None
    during dataclass __init__ if not provided — your code MUST
    handle the None case. The WS2A registry handled this by checking
    `entry.profile is not None` in `route_by_capability`.
  - Tools like `mypy --strict` will warn about None comparisons. This
    is good — the type is honest about the possibility.
  - If you later make the field required, you cannot remove the
    default without breaking call sites. The pattern is forward-only.
version: 1
captured: 2026-06-04
captured_from: cohezion-internal PR #219 (WS2A card-aligned registry)
