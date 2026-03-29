# TDD + Compound Engineering Specification

**Version**: 1.0  
**Origin**: Retrospective 2026-02-24 (IDE Error Resolution Sprint)  
**Status**: ACTIVE

> Every line of code must prove it can breathe before it's committed.

---

## 1. The Problem This Solves

Premium model tokens were burned fixing errors that a 3-second automated check would have caught. Code was written aspirationally — referencing functions that don't exist, calling constructors without required args, assigning `None` to non-optional fields. The codebase accumulated **silent technical debt** because nothing enforced basic validity at creation time.

## 2. Core Principle: Fail at Write Time, Not Discovery Time

```
┌─────────┐    ┌────────┐    ┌─────────────┐    ┌────────────┐    ┌────────┐
│  WRITE  │───>│ IMPORT │───>│ INSTANTIATE │───>│ TYPE-CHECK │───>│ COMMIT │
└─────────┘    └────────┘    └─────────────┘    └────────────┘    └────────┘
                  0.5s            0.5s               5s              ✓
```

No code advances to the next stage until the current stage passes.

---

## 3. The Three Gates

### Gate 1: Import Gate (0.5s)

**Every module must be importable.** If `import cohezion.compound.persistence` throws, the code is broken.

**Implementation**: `tests/smoke/test_imports.py`

```python
"""Auto-discover and import every module in src/cohezion/."""
import importlib
import pkgutil
import cohezion

def test_all_modules_importable():
    """Every .py file under src/cohezion/ must import without error."""
    failures = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        cohezion.__path__, prefix="cohezion."
    ):
        try:
            importlib.import_module(modname)
        except Exception as e:
            failures.append(f"{modname}: {e}")
    assert not failures, f"Import failures:\n" + "\n".join(failures)
```

**What this catches**:

- Ghost functions (referencing APIs that don't exist)
- Missing dependencies
- Circular imports that crash at import time
- Syntax errors

### Gate 2: Instantiation Gate (0.5s)

**Every public class must be constructable** with minimal valid args.

**Implementation**: `tests/smoke/test_instantiation.py`

```python
"""Verify key classes can be instantiated with minimal args."""
from cohezion.compound.journey_tracker import TrajectoryPoint, JourneyTracker
from cohezion.compound.persistence import CompoundPersistence
from cohezion.compound.exp_persistence.accumulator import PersistenceAccumulator
from cohezion.branding import get_theme

def test_trajectory_point_creation():
    point = TrajectoryPoint(
        coherence=0.5, efficiency=0.5,
        operation_type="test", task_description="test"
    )
    assert point.metadata is None  # Default works

def test_compound_persistence_creation():
    p = CompoundPersistence()
    assert p is not None

def test_branding_theme():
    theme = get_theme()
    assert "success" in theme or hasattr(theme, "styles")
```

**What this catches**:

- Dataclass field default violations
- Missing required constructor arguments
- Type annotation mismatches caught at runtime

### Gate 3: Type Gate (5s)

**Type checker must pass on changed files.**

**Implementation**: Add to `pyproject.toml` or CI

```toml
[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "basic"  # "strict" is aspirational
reportMissingImports = true
reportMissingTypeStubs = false
```

**Pre-commit command**:

```bash
uv run pyright --pythonversion 3.13 <changed-files>
```

**What this catches**:

- None-access without guards
- Unparameterized generics
- Type mismatches in function calls

---

## 4. Compound Engineering Integration

### 4.1. Every New Feature Gets a Smoke Test

When writing a new module `src/cohezion/foo/bar.py`:

1. **Write the import test FIRST** (10 seconds):

   ```python
   # In tests/smoke/test_imports.py or tests/unit/foo/test_bar.py
   def test_bar_importable():
       from cohezion.foo.bar import BarClass
   ```

2. **Write the instantiation test SECOND** (30 seconds):

   ```python
   def test_bar_creatable():
       obj = BarClass(required_arg="test")
       assert obj is not None
   ```

3. **Then write the module.** The tests will fail (TDD red phase). Make them pass (green). Refactor.

### 4.2. Compound Skill Extraction Pattern

When a fix reveals a reusable pattern, extract it:

```
Fix Session → Retrospective → Pattern Detection → Skill Registration → Prevention
```

From this session, the extracted skill is:

- **IMPORT_VALIDATION_PRIME**: Auto-validate all imports before commit
- Register in `src/cohezion/skills/import_validation/`

### 4.3. Token Efficiency Hierarchy

Route work to the cheapest sufficient tool:

| Check               | Tool                      | Token Cost    | Time        |
| ------------------- | ------------------------- | ------------- | ----------- |
| Import validity     | `python -c "import ..."`  | 0 (local)     | 0.5s        |
| Instantiation       | `pytest tests/smoke/ -x`  | 0 (local)     | 1s          |
| Type checking       | `pyright <file>`          | 0 (local)     | 5s          |
| Lint                | `ruff check <file>`       | 0 (local)     | 1s          |
| Full test suite     | `pytest -x`               | 0 (local)     | 30s         |
| Code review         | Local SLM (Qwen/DeepSeek) | Low           | 10s         |
| Architecture review | Premium model             | High          | Minutes     |
| Bug fixing session  | Premium model             | **Very High** | **30+ min** |

**Rule**: Never spend premium tokens on problems detectable by free local checks.

---

## 5. Enforcement Implementation

### 5.1. Pre-Commit Hook (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: local
    hooks:
      - id: smoke-imports
        name: Smoke Import Check
        entry: uv run pytest tests/smoke/test_imports.py -x -q
        language: system
        pass_filenames: false
        stages: [commit]

      - id: smoke-instantiation
        name: Smoke Instantiation Check
        entry: uv run pytest tests/smoke/test_instantiation.py -x -q
        language: system
        pass_filenames: false
        stages: [commit]

      - id: ruff-check
        name: Ruff Lint
        entry: uv run ruff check
        language: system
        types: [python]
```

### 5.2. Agent Workflow Rule

Add to `CODING_STANDARDS.md` §5:

```markdown
## 5. Validation Before Commit (MANDATORY)

Every code change MUST pass these gates before commit:

1. **Import Gate**: `uv run python -c "from <module> import <thing>"`
2. **Instantiation Gate**: `uv run pytest tests/smoke/ -x -q`
3. **Lint Gate**: `uv run ruff check <changed-files>`
4. **Test Gate**: `uv run pytest <related-tests> -x`

Agents MUST run these checks inline during development, not as an afterthought.
The pattern is: WRITE → VERIFY → COMMIT, never WRITE → COMMIT → HOPE.
```

---

## 6. Context Awareness Protocol

### 6.1. Before Writing Code That References Another Module

```
STOP → CHECK → WRITE
```

1. **STOP**: Before typing `from cohezion.foo import bar`
2. **CHECK**: `view_file_outline` or `grep_search` to verify `bar` exists in `foo`
3. **WRITE**: Only after confirming the API surface

### 6.2. Before Creating a New Class

1. Check existing classes in the same domain (avoid duplication)
2. Check constructor signatures of classes you'll instantiate
3. Verify import paths are correct (`cohezion.core.persistence.X` not `cohezion.persistence.X`)

### 6.3. Session Boundary Protocol

At the start of any coding session:

```bash
# 10-second health check
uv run pytest tests/smoke/ -x -q
uv run ruff check src/cohezion/ --statistics
```

If either fails, fix before doing anything else — compound debt grows exponentially.

---

## 7. Metrics

Track these to measure improvement:

| Metric                             | Target               | Measurement                               |
| ---------------------------------- | -------------------- | ----------------------------------------- |
| Ghost function rate                | 0 per month          | Count of `import X` where X doesn't exist |
| Type error escape rate             | < 5 per month        | basedpyright error-severity only          |
| Smoke test pass rate               | 100% on every commit | CI gate                                   |
| Token cost of error fix sessions   | Trending → 0         | Compare monthly                           |
| Time from code-write to first-test | < 60 seconds         | Sprint logs                               |

---

## 8. Summary

> **The cheapest bug to fix is one that never escapes the editor.**

Three automated checks — import, instantiate, type-check — would have prevented every error found in the 2026-02-24 sprint. This spec makes those checks mandatory, automated, and integrated into the compound engineering lifecycle.
