Investigate and fix all failing tests using the compound test-fix protocol.

## Protocol (in strict order)

### Phase 1: Heal First
1. Run `uv run ruff check src/cohezion/ --fix` — auto-fix lint issues that may block test collection
2. Run `uv run ruff format src/cohezion/` — formatting can affect test discovery
3. Find missing `__init__.py`: `find src/cohezion -type d | grep -v __pycache__ | while read d; do [ ! -f "$d/__init__.py" ] && echo "MISSING: $d"; done`
4. Create any missing ones: `touch "$d/__init__.py"`

### Phase 2: Identify Failure Categories
5. Run full suite to get counts: `uv run pytest tests/ -q --no-header -p no:cacheprovider -o "addopts=" 2>&1 | tail -5`
6. Get failure file breakdown: `... | grep '^FAILED' | sed 's/::.*//' | sort | uniq -c | sort -rn`
7. Run each failing FILE individually: `uv run pytest tests/path/to/file.py -q --no-header -p no:cacheprovider -o "addopts="`
   - If passes individually → **isolation issue** (singleton/event loop pollution)
   - If fails individually → **logic bug** (specific root cause in that file)

### Phase 3: Apply Root Cause Patterns

**Pattern A — AttributeError `_method` "Did you mean: `method`?"**
→ Private-to-public rename drift. Search: `grep -rn "_old_name" src/ tests/`. Fix with sed.

**Pattern B — ERRORs in full suite, pass individually, async tests**
→ asyncio.Lock or asyncio.Semaphore at class level. Fix: move to `__init__`.
```python
# BAD: class-level asyncio primitive
class Foo:
    _lock: asyncio.Lock = asyncio.Lock()
# GOOD: instance-level in __init__
class Foo:
    def __init__(self):
        self._lock = asyncio.Lock()
```

**Pattern C — "async def functions are not natively supported"**
→ Missing `@pytest.mark.asyncio` with `asyncio_mode=strict`.
Fix: add `pytestmark = pytest.mark.asyncio` at module level.

**Pattern D — Test hangs indefinitely**
→ Subprocess (curl/network) or `asyncio.Future as side_effect` mock.
Fix subprocess: `patch("asyncio.create_subprocess_exec", return_value=mock_proc)` where `mock_proc.communicate = AsyncMock(return_value=(b'{}', b""))`.
Fix mock hang: replace `MagicMock(side_effect=asyncio.Future)` with `AsyncMock(return_value=None)`.

**Pattern E — Type/value assertion mismatch**
→ Field type changed but test assertion not updated. Read source + test side by side.

**Pattern F — Singleton pollution (non-async)**
→ Class-level mutable state not reset between tests. Check conftest.py for singleton resets.

### Phase 4: Verify
8. Run `uv run pytest tests/ -q --no-header -p no:cacheprovider -o "addopts=" 2>&1 | tail -3`
9. Report: before/after counts, root causes fixed, patterns matched.

## Key Rules
- NEVER fix 83 tests one-by-one — categorize root causes first
- Always run individually before concluding "logic bug"
- Heal before investigating — formatting affects test collection
- asyncio.Future as side_effect is ALWAYS a hang, not a fix
