Audit the codebase for asyncio anti-patterns that cause event-loop isolation failures in tests.

## What to Find

### 1. asyncio primitives at class level (Critical)
```bash
grep -rn "asyncio\.Lock()\|asyncio\.Semaphore()\|asyncio\.Event()\|asyncio\.Condition()" src/cohezion/ \
  | grep -v "def \|self\.\|#" | grep "^\s*[A-Za-z_].*[:=].*asyncio\."
```
Any asyncio primitive that's a class-level attribute (not in `__init__`) is a time bomb.

**Fix**: Move to `__init__`.

### 2. subprocess.communicate without timeout (High)
```bash
grep -rn "await process\.communicate()" src/cohezion/ | grep -v "wait_for"
```
Any `await process.communicate()` without `asyncio.wait_for(timeout=N)` can hang indefinitely.

**Fix**:
```python
stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)
```

### 3. curl without --max-time (High)
```bash
grep -rn "create_subprocess_exec.*curl" src/cohezion/ | grep -v "max-time"
```
curl calls to external services (Ollama, SurrealDB) hang without a timeout flag.

**Fix**: Add `"--max-time", "5", "--connect-timeout", "3"` to curl args.

### 4. vitals["key"] without .get() (Medium)
```bash
grep -rn 'vitals\["' src/cohezion/ | grep -v "vitals\.get"
```
Direct key access on vitals dicts raises KeyError if caller omits optional keys.

**Fix**: `vitals.get("memory_percent", 0)` with sensible defaults.

### 5. Async test files missing pytestmark (Medium)
```bash
for f in $(find tests/ -name "*.py" -exec grep -l "async def test_" {} \;); do
  grep -q "pytestmark\|@pytest.mark.asyncio" "$f" || echo "MISSING asyncio mark: $f"
done
```
Files with async tests but no mark fail silently under asyncio_mode=strict.

**Fix**: Add `pytestmark = pytest.mark.asyncio` at module level.

## Report Format

After running all checks:
1. List each file with issues by category
2. Estimate risk: Critical (will fail in CI) / High (fails when service is down) / Medium (latent)
3. Apply fixes to Critical issues immediately
4. Document High/Medium in KEY_LEARNINGS.md

## Context

This audit was formalized after Session 70 where 83 test failures decomposed into 6 asyncio-related root causes. The patterns are all captured in:
- `~/vaults/cohezion-vault/patterns/async-singleton-lock-isolation.md`
- `~/vaults/cohezion-vault/patterns/async-mock-subprocess-in-tests.md`
- KEY_LEARNINGS.md L130-L134
