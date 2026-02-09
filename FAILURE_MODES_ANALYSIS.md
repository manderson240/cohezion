# MCP Integration Failure Modes Analysis

**Status**: In Progress (Task #14)
**Date**: 2026-02-09
**Analyst**: Reliability Engineering / Adversarial Team

## Executive Summary

This document systematically analyzes failure modes and weaknesses in the Cloud Vault MCP integration design across 9 critical dimensions:

1. **MCP Server Resilience** - Crash detection, recovery, and state consistency
2. **Vault Access & Availability** - Directory inaccessibility, permissions, data corruption
3. **Dependency Stability** - Starlette breaking changes, version management, fallback strategies
4. **Concurrency & Race Conditions** - Multi-agent vault access, locking, atomic operations
5. **Authentication & Secrets Management** - API key expiration, rotation, exposure
6. **Error Handling & Propagation** - Silent failures, cascading errors, observability
7. **Scalability & Resource Constraints** - Team concurrency, request queuing, memory leaks
8. **Network Resilience** - Partition detection, timeout handling, graceful degradation
9. **Data Integrity & Loss Prevention** - Corruption recovery, transaction safety, backups

---

## 1. MCP Server Failure & Recovery

### 1.1 Server Crash Detection

**Severity**: CRITICAL (Session loss)

**Current State**:
- UV/Uvicorn crash propagates uncaught to OS
- Claude Code receives immediate connection error (socket reset)
- No heartbeat/health check mechanism for server liveness
- No automatic recovery or restart loop

**Failure Scenarios**:
1. **Unhandled exception in MCP tool** → Process crash → Client times out after 30s
2. **Memory exhaustion** (SSE queue unbounded) → OOM killer → Process termination
3. **Async deadlock** in inbox processor → Event loop hangs → No heartbeat
4. **File descriptor leak** in vault_watcher → Eventually can't open files → Crash
5. **Starlette/Uvicorn bug** → Silent exit with no error logs

**Weaknesses**:
- No watchdog/systemd auto-restart mechanism
- No memory limits or overflow protection
- No timeout on blocking operations
- SSE subscriber queue unbounded (can grow to 1000s MB if client disconnects slowly)
- Exception handling in main.py doesn't catch all async errors

**Mitigation Strategies**:

1. **Process Supervision** (Recommended):
   - Deploy with systemd service or supervisor (auto-restart on crash)
   - Monitor PID via `/proc/{pid}/status` to detect stale processes
   - Health check endpoint: `/health` returns `{"status": "ok", "timestamp": ...}`
   - Implement heartbeat: Client pings `/health` every 10s, logs if missing

2. **Memory Protection**:
   - Bounded SSE queue: `maxsize=1000` with `Full` exception handling
   - Timeout on all blocking I/O: 5s for vault ops, 10s for Claude API calls
   - Periodic memory dump: Log heap size every 5 minutes, warn at >500MB

3. **Async Error Handling**:
   ```python
   try:
       uvicorn.run(...)
   except Exception as e:
       logger.critical("MCP server crashed: %s", e, exc_info=True)
       sys.exit(1)
   ```

4. **Graceful Degradation**:
   - Catch exception in each @mcp.tool() and return error JSON
   - Never crash the entire server for a single tool failure
   - Queue unprocessed events and retry on recovery

---

### 1.2 Partial Service Degradation

**Severity**: HIGH (Lost functionality while server runs)

**Failure Scenarios**:
1. Vault operations fail but SSE stream still works → Client thinks server is healthy
2. Anthropic API timeout in inbox processor → Blocks all future inbox processing
3. Google Sheets API down → `sheets_*` tools fail but others work
4. VaultFileWatcher crashes but server keeps running → No change notifications

**Weaknesses**:
- Health endpoint doesn't check dependencies (vault, Anthropic, Sheets)
- Exceptions in background tasks (inbox processor) don't propagate to main
- No circuit breaker for external APIs
- Sheets failures crash entire response, not just sheets tools

**Mitigation Strategies**:

1. **Comprehensive Health Check**:
   ```python
   @mcp.tool()
   def health() -> dict:
       checks = {
           "vault": check_vault_readable(),
           "anthropic": check_anthropic_api(),
           "sheets": check_sheets_api(),  # optional=True if disabled
           "watcher": check_watcher_running(),
       }
       status = "ok" if all(checks.values()) else "degraded"
       return {"status": status, "checks": checks}
   ```

2. **Per-tool Circuit Breaker**:
   - Track failures per tool over 5-minute window
   - After 5 consecutive failures, return "Service temporarily unavailable"
   - Reset after 30 seconds of success

3. **Dependency Isolation**:
   - Initialize Sheets conditionally with try/except
   - If init fails, register tools that return "Sheets service unavailable"
   - Log warnings, don't crash

---

## 2. Vault Access & Inaccessibility

### 2.1 Vault Directory Becomes Inaccessible

**Severity**: CRITICAL (Blocks all operations)

**Failure Scenarios**:
1. **Permission denied**: `chmod 000 vault/` or user permission revoked
2. **Directory deleted**: `rm -rf vault/` or parent unmounted
3. **Filesystem error**: Corrupted inode, EXT4 journal error, NFS disconnect
4. **Disk full**: No space to write new notes
5. **Symlink broken**: `vault/ → /mnt/remote` and mount fails
6. **File in use**: Another process has exclusive lock on vault files

**Weaknesses**:
- Constructor `VaultOps.__init__()` fails → MCP server crashes on startup
- No fallback storage if vault becomes unavailable mid-session
- Permission errors only caught at operation time (lazy evaluation)
- No read-only mode if directory exists but isn't writable
- SSE watcher crashes if vault path disappears

**Current Code**:
```python
def __init__(self, vault_path: str):
    self.vault_path = Path(vault_path).resolve()
    if not self.vault_path.is_dir():
        raise ValueError(f"Vault path does not exist: {self.vault_path}")
    # No permission check!
```

**Mitigation Strategies**:

1. **Startup Validation**:
   ```python
   def __init__(self, vault_path: str):
       self.vault_path = Path(vault_path).resolve()
       if not self.vault_path.is_dir():
           raise ValueError(f"Vault path does not exist")

       # Check permissions
       test_file = self.vault_path / ".vault_write_test"
       try:
           test_file.write_text("test")
           test_file.unlink()
       except (OSError, PermissionError) as e:
           raise ValueError(f"Vault not writable: {e}")
   ```

2. **Fallback Storage**:
   - Primary: `vault_path` (from config)
   - Secondary: `${HOME}/.cohezion/vault_fallback/` (local, always accessible)
   - Tertiary: Memory cache of last 100 writes (ephemeral)
   - On write failure: Log warning, try secondary, then return error

3. **Graceful Degradation**:
   - Read-only mode if vault directory exists but not writable
   - Queue writes to fallback with retry on vault recovery
   - Return 503 Service Unavailable instead of 500 Internal Server Error

4. **Recovery Detection**:
   - Periodically re-check vault accessibility (every 30s during degraded mode)
   - Automatically switch back to primary once accessible
   - Replay queued writes in order

5. **Monitoring**:
   - Alert if vault inaccessible for >5 minutes
   - Track fallback storage usage
   - Log all vault access errors with permission/disk space diagnostics

---

### 2.2 Data Corruption & Inconsistency

**Severity**: HIGH (Silent data loss)

**Failure Scenarios**:
1. **Partial write**: Power failure mid-`write_text()` → Incomplete file
2. **Concurrent edits**: Agent A reads, Agent B writes, Agent A overwrites with stale data
3. **Symlink attack**: Attacker creates `vault/decisions/evil.md → /etc/passwd`
4. **VaultOps._resolve() bypass**: Path traversal via symlinks: `decisions/../../../etc/passwd`
5. **Text encoding issues**: File written UTF-8 with BOM, read as UTF-8, BOM included in content
6. **Hard link race**: Multiple hard links to same vault file, edits on one affect others

**Weaknesses**:
- `Path.write_text()` not atomic (can be interrupted)
- VaultFileWatcher doesn't detect symlink-based attacks (follows symlinks)
- `_resolve()` checks only string prefix, not inode equivalence
- No transaction log or write-ahead log
- Concurrent `.edit()` calls can race (read-modify-write not atomic)

**Current Code**:
```python
def _resolve(self, path: str) -> Path:
    resolved = (self.vault_path / path).resolve()
    if not str(resolved).startswith(str(self.vault_path)):  # Broken for symlinks!
        raise ValueError(f"Path escapes vault: {path}")
    return resolved

def edit(self, path: str, edits: list[dict]) -> str:
    # TOCTOU race: read, modify, write
    content = target.read_text()  # A reads
    # B reads and modifies
    for edit in edits:
        # A modifies
        # ...
    target.write_text(content)  # A writes (overwrites B's changes)
```

**Mitigation Strategies**:

1. **Atomic Writes**:
   ```python
   def write(self, path: str, content: str) -> str:
       target = self._resolve(path)
       target.parent.mkdir(parents=True, exist_ok=True)

       # Write to temp file first
       temp = target.parent / f"{target.name}.tmp.{os.getpid()}"
       try:
           temp.write_text(content, encoding="utf-8")
           temp.replace(target)  # Atomic on POSIX
       except:
           temp.unlink(missing_ok=True)
           raise
   ```

2. **Symlink Security**:
   ```python
   def _resolve(self, path: str) -> Path:
       vault_inode = self.vault_path.stat().st_ino
       resolved = (self.vault_path / path).resolve()

       # Walk path components and check each is within vault inode
       current = self.vault_path
       for part in resolved.relative_to(self.vault_path).parts:
           current = current / part
           if current.is_symlink():
               raise ValueError(f"Symlink not allowed: {current}")

       return resolved
   ```

3. **Distributed Locking**:
   - Use `fcntl.flock()` for exclusive write access
   - Hold lock across read-modify-write cycle
   - Timeout: 5s (release if holder crashes)

4. **Write-Ahead Logging**:
   - Before write: Log operation to `.vault_log/{timestamp}.txt`
   - On crash recovery: Replay unfinished writes
   - Periodic compaction: Delete logs >7 days old

5. **Concurrent Edit Detection**:
   - Store hash of original file before edit
   - Re-read hash before writing back
   - If mismatch: Return error "File was modified; try again"

---

## 3. Dependency Stability & Import Failures

### 3.1 Starlette/Uvicorn Breaking Changes

**Severity**: CRITICAL (Complete server failure)

**Recent History**:
- Session 39: `starlette>=0.38.0` changed `TrustedHostMiddleware` constructor
- Import error: `TypeError: TrustedHostMiddleware.__init__() missing required positional argument 'app'`
- Server wouldn't start; had to update to `starlette>=0.39.0`

**Failure Scenarios**:
1. **Starlette 0.40 release**: Removes `TrustedHostMiddleware` entirely
2. **Uvicorn 0.31 release**: Changes lifespan context manager signature
3. **MCP library 2.0**: Changes FastMCP API completely
4. **Python 3.14 release**: Removes deprecated asyncio API used in VaultFileWatcher
5. **Watchdog 5.0**: Changes FileSystemEventHandler interface

**Weaknesses**:
- Pinned minimum versions only (`>=0.38.0`), no maximum versions
- No tests running against latest versions (would catch immediately)
- Single import path: if `starlette` import fails, entire server fails
- No version constraints in production (pip could upgrade to breaking version)
- No deprecation warnings or migration guide for version updates

**Current pyproject.toml**:
```toml
dependencies = [
    "mcp[cli]>=1.2.0",
    "pyyaml>=6.0",
    "uvicorn>=0.30.0",
    "starlette>=0.38.0",  # No upper bound!
    "watchdog>=4.0",      # No upper bound!
]
```

**Mitigation Strategies**:

1. **Version Pinning** (Short-term):
   ```toml
   dependencies = [
       "mcp[cli]>=1.2.0,<2.0",
       "uvicorn>=0.30.0,<1.0",
       "starlette>=0.38.0,<0.40",  # Upper bound
       "watchdog>=4.0,<5.0",
   ]
   ```

2. **Compatibility Abstraction** (Medium-term):
   Create adapter layer:
   ```python
   # src/mcp_server/compat.py
   try:
       from starlette.middleware.trustedhost import TrustedHostMiddleware
   except ImportError:
       # Fallback for starlette 0.40+
       class TrustedHostMiddleware:
           def __init__(self, app, allowed_hosts):
               # Custom implementation
               self.app = app
   ```

3. **Automated Dependency Testing**:
   - CI: Test against latest minor versions of all dependencies
   - If test fails: Block merge, create issue for migration
   - Quarterly: Try `pip install --upgrade-all` and run tests

4. **Graceful Degradation for Middleware**:
   ```python
   if "*" not in config.allowed_hosts:
       try:
           mcp_app = TrustedHostMiddleware(mcp_app, allowed_hosts=config.allowed_hosts)
       except Exception as e:
           logger.warning("TrustedHostMiddleware failed (continuing without): %s", e)
   ```

---

## 4. Concurrency & Race Conditions

### 4.1 Multi-Agent Vault Access

**Severity**: HIGH (Data loss, corruption)

**Scenario**: 5-agent team accessing vault simultaneously
- Agent A reads `/decisions/architecture.md` (1000 lines)
- Agent B reads same file
- Agent C writes to same file (adds section)
- Agent A modifies content offline for 2 seconds
- Agent A writes back → Overwrites Agent C's changes (Lost Update)

**Failure Scenarios**:
1. **Lost Update Race**: Multiple agents edit same file concurrently
2. **Dirty Read**: Agent reads file while another agent is writing
3. **Directory Listing Race**: Agent lists directory while another deletes files
4. **Symlink TOCTOU**: Agent checks symlink, attacker replaces with different target
5. **SSE Missing Events**: Concurrent writes create events faster than SSE can deliver

**Current Code Weaknesses**:
- No locking mechanism in `VaultOps`
- Edit operations are read-modify-write without atomicity
- VaultFileWatcher uses watchdog observer (debounces, may miss events)
- Multiple agents can spawn multiple VaultFileWatcher instances (no coordination)

**Mitigation Strategies**:

1. **File-Level Locking**:
   ```python
   import fcntl

   def read_locked(self, path: str) -> str:
       target = self._resolve(path)
       with open(target, 'r') as f:
           fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock
           try:
               return f.read()
           finally:
               fcntl.flock(f.fileno(), fcntl.LOCK_UN)

   def write_locked(self, path: str, content: str) -> str:
       target = self._resolve(path)
       target.parent.mkdir(parents=True, exist_ok=True)

       # Exclusive lock
       with open(target, 'w') as f:
           fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
           if not f:
               raise IOError("File locked by another agent (timeout 5s)")
           try:
               f.write(content)
           finally:
               fcntl.flock(f.fileno(), fcntl.LOCK_UN)
   ```

2. **Optimistic Concurrency Control** (for edits):
   - Store hash/checksum of original file
   - On write-back: Check if file changed
   - If mismatch: Return error "File modified; conflict detected"
   - Client must merge or retry

3. **Single VaultFileWatcher Instance**:
   - Create singleton `get_watcher()` in main.py
   - All agents subscribe to same instance
   - Prevents duplicate event loops and race conditions

4. **Event Deduplication**:
   - Track `(path, event_type, timestamp)` in 100ms window
   - Only emit one event per unique (path, type)
   - Prevents SSE client overwhelm

---

### 4.2 Concurrent Inbox Processing

**Severity**: MEDIUM (File conflicts, duplicate processing)

**Failure Scenarios**:
1. **Duplicate Processing**: Two agents process same inbox note simultaneously
2. **File Rename Race**: Note moved while processor is reading
3. **Deleted While Processing**: Note deleted while Claude is responding
4. **Event Queue Overflow**: 100 inbox events arrive → Queue has 100 items

**Weaknesses**:
- No locking before processing a note
- SSE subscriber queue unbounded (can fill memory)
- No deduplication of processing events
- Inbox processor makes 2-3 API calls per note (blocking)

**Mitigation**:
1. **Lock Before Processing**:
   ```python
   async def process_note(self, path: str) -> ProcessingResult:
       try:
           lock = fcntl.flock(open(path), fcntl.LOCK_EX | fcntl.LOCK_NB)
       except BlockingIOError:
           return ProcessingResult(..., success=False, error="File locked")
   ```

2. **Bounded Inbox Queue**: `inbox_queue = asyncio.Queue(maxsize=50)`

3. **Idempotent Processing**: Store processed note hashes in `.vault_processed.json`

---

## 5. Authentication & Secrets Management

### 5.1 API Key Exposure & Compromise

**Severity**: CRITICAL (Full system compromise)

**Failure Scenarios**:
1. **API key in logs**: Exception logs include full auth header
2. **API key in error messages**: Client receives "Invalid key: abc123def456..."
3. **Key rotation impossible**: Single hardcoded key, no versioning
4. **Key logged by middleware**: Starlette access logs include Authorization header
5. **Key exposed in network**: Sent over HTTP (if not HTTPS)
6. **Key in environment history**: `echo $MCP_API_KEY` in bash history
7. **Key backup**: Git history contains old key values

**Weaknesses**:
- API key passed as environment variable (visible in `ps aux`)
- No key versioning (can't revoke without affecting all clients)
- No rate limiting per key
- Bearer token sent in plain Authorization header (requires TLS)
- Error messages may leak key fragments

**Current Code**:
```python
def main():
    if not config.api_key:
        logger.warning("MCP_API_KEY is not set...")  # Exposed!
    # ...
```

```python
class APIKeyAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:]
        if not hmac.compare_digest(token, self.api_key):
            return JSONResponse(
                {"error": "Invalid API key"},  # Logs auth attempt
                status_code=403,
            )
```

**Mitigation Strategies**:

1. **Secure Configuration**:
   - Load from file, not environment: `--api-key-file /etc/cohezion/api_key`
   - File permissions: `0600` (readable only by owner)
   - Never log the key itself
   - Support key from secret manager (AWS Secrets Manager, HashiCorp Vault)

2. **Key Versioning**:
   ```python
   @dataclass
   class APIKeyVersion:
       key_id: str
       key_hash: str  # SHA256(api_key)
       created_at: datetime
       revoked_at: datetime | None
       active: bool

   class APIKeyAuth(BaseHTTPMiddleware):
       def __init__(self, app, key_store: KeyStore):
           self.key_store = key_store  # Redis/DB with versions

       async def dispatch(self, request, call_next):
           token = request.headers.get("Authorization", "")[7:]
           key_hash = hashlib.sha256(token.encode()).hexdigest()
           if not self.key_store.is_valid(key_hash):
               # Never return specific error
               return JSONResponse({"error": "Unauthorized"}, 401)
   ```

3. **Rate Limiting per Key**:
   ```python
   # Redis: "rate:{key_hash}:{minute}" → count
   key_hash = hashlib.sha256(token.encode()).hexdigest()
   minute_bucket = f"rate:{key_hash}:{datetime.now().minute}"
   count = redis.incr(minute_bucket)
   redis.expire(minute_bucket, 60)
   if count > 1000:  # 1000 req/min per key
       return JSONResponse({"error": "Rate limited"}, 429)
   ```

4. **Transport Security**:
   - Require HTTPS (disable HTTP in production)
   - Add HSTS header: `Strict-Transport-Security: max-age=31536000`
   - Never send API key over HTTP

5. **Logging Security**:
   - Never log Authorization header
   - Strip auth from logs: `logger.info("Request: %s", redact_auth(request))`
   - Audit log: Track all key validations (success/failure) with timestamp

6. **Key Rotation Strategy**:
   - Support multiple active keys
   - Rotate quarterly: Deploy new key, keep old for 7 days grace period
   - Track which version used in each request (audit trail)

---

### 5.2 Anthropic API Key Management

**Severity**: HIGH (Can call Claude API, high cost risk)

**Weaknesses**:
- Anthropic key stored in environment (visible in `ps aux`)
- No separate key for inbox processor vs. other components
- No budget limit / request rate limiting
- Anthropic API timeout not configured (uses default 30s)

**Mitigation**:
1. Store in secure file/manager (same as MCP API key)
2. Create separate budget: `ANTHROPIC_BUDGET_MONTHLY=$100`
3. Track spend per day; alert at 50%, 80%, 95%
4. Set explicit timeout: `client = Anthropic(timeout=10)`

---

## 6. Error Handling & Observability

### 6.1 Silent Failures & Missing Errors

**Severity**: HIGH (Difficult to debug)

**Failure Scenarios**:
1. **Vault write fails but returns "success"**: Permission denied, returns same response
2. **SSE client disconnects, no error logged**: Agent waits forever for updates
3. **Anthropic API timeout with no retry**: Inbox note never processed
4. **File not found during list_dir**: Returns empty list instead of error
5. **Sheets API down**: Google API returns 500, caught as generic exception

**Current Code Weaknesses**:
```python
@mcp.tool()
def vault_write(path: str, content: str) -> str:
    try:
        return vault.write(path, content)
    except ValueError as e:
        return f"Error: {e}"  # Client doesn't know if write succeeded
```

```python
def list_dir(self, directory: str = "", recursive: bool = False) -> list[str]:
    try:
        # ...
    except FileNotFoundError as e:
        return f"Error: {e}"  # Returns string, not list → type confusion
```

**Mitigation Strategies**:

1. **Structured Error Responses**:
   ```python
   @dataclass
   class ToolResult:
       success: bool
       data: Any | None
       error: str | None
       error_code: str | None

   @mcp.tool()
   def vault_write(path: str, content: str) -> ToolResult:
       try:
           vault.write(path, content)
           return ToolResult(success=True, data=None, error=None)
       except PermissionError as e:
           return ToolResult(success=False, data=None, error=str(e),
                           error_code="PERMISSION_DENIED")
       except IOError as e:
           return ToolResult(success=False, data=None, error=str(e),
                           error_code="IO_ERROR")
   ```

2. **Comprehensive Logging**:
   ```python
   logger.info("vault_write: path=%s, size=%d, status=success", path, len(content))
   logger.error("vault_write: path=%s, error=%s", path, e, exc_info=True)
   ```

3. **Timeout Configuration**:
   ```python
   # All blocking I/O with timeout
   async def read_with_timeout(path: str, timeout_s: float = 5.0):
       try:
           return await asyncio.wait_for(async_read(path), timeout=timeout_s)
       except asyncio.TimeoutError:
           return ToolResult(success=False, error="Read timeout",
                           error_code="TIMEOUT")
   ```

4. **Structured Logging**:
   ```python
   import structlog
   log = structlog.get_logger()

   log.info("tool_executed", tool="vault_write", path=path,
           duration_ms=elapsed, success=True)
   log.error("tool_failed", tool="vault_write", path=path,
           error_code=error.code, duration_ms=elapsed)
   ```

---

## 7. Scalability & Resource Constraints

### 7.1 High Concurrency (Team Swarm)

**Severity**: MEDIUM (Performance degradation → timeout)

**Scenario**: 20-agent team, each making 10 requests/sec = 200 req/sec

**Failure Scenarios**:
1. **SSE Queue Overflow**: 20 agents subscribe, changes come 100/sec → Queue fills (unbounded)
2. **Memory bloat**: 200 active requests × ~1MB per request = 200MB
3. **File descriptor exhaustion**: Each client connection = 1 FD, 200 clients = 200+ FDs
4. **Async context explosion**: 200 concurrent tasks in event loop
5. **VaultFileWatcher events drop**: Watchdog queue can't keep up

**Weaknesses**:
- SSE subscriber queue unbounded: `self._subscribers: list[asyncio.Queue] = []`
- No max connection limit
- No request queuing or backpressure
- Event loop runs all tasks concurrently (no throttling)
- Vault operations not batched

**Current Code**:
```python
class VaultFileWatcher:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []  # No limit!
        # ...
```

**Mitigation Strategies**:

1. **Connection Limits**:
   ```python
   class RateLimitMiddleware(BaseHTTPMiddleware):
       def __init__(self, app, max_connections=100):
           self.max_connections = max_connections
           self.active = 0

       async def dispatch(self, request, call_next):
           if self.active >= self.max_connections:
               return JSONResponse({"error": "Server at capacity"}, 503)
           self.active += 1
           try:
               return await call_next(request)
           finally:
               self.active -= 1
   ```

2. **Bounded Queues**:
   ```python
   class VaultFileWatcher:
       def __init__(self, ..., max_subscribers=100, queue_size=1000):
           self._subscribers: list[asyncio.Queue] = []
           self.max_subscribers = max_subscribers
           self.queue_size = queue_size

       def subscribe(self):
           if len(self._subscribers) >= self.max_subscribers:
               raise RuntimeError("Too many subscribers")
           queue = asyncio.Queue(maxsize=self.queue_size)
           # ...
   ```

3. **Request Batching**:
   ```python
   # Batch multiple vault writes into single transaction
   async def batch_write(writes: list[tuple[str, str]]) -> list[bool]:
       results = []
       for path, content in writes:
           try:
               vault.write(path, content)
               results.append(True)
           except Exception:
               results.append(False)
       return results
   ```

4. **Memory Limit Alert**:
   ```python
   import psutil

   async def monitor_memory():
       process = psutil.Process()
       while True:
           await asyncio.sleep(10)
           mem = process.memory_info().rss / 1024 / 1024  # MB
           if mem > 500:
               logger.warning("High memory: %d MB", mem)
           if mem > 1000:
               logger.critical("Critical memory: %d MB, rejecting new requests", mem)
   ```

---

## 8. Network Resilience & Partition Tolerance

### 8.1 Client-Server Network Partition

**Severity**: HIGH (Clients think server is dead)

**Failure Scenarios**:
1. **Network glitch**: 100ms packet loss → Client timeout (30s) → Retry fail
2. **Server network down**: MCP server can't reach Anthropic API
3. **VPN/SSH tunnel breaks**: Claude Code loses connection to MCP server
4. **Firewall rule change**: Blocks MCP server port temporarily
5. **DNS resolution fails**: MCP server hostname unresolvable

**Weaknesses**:
- Client timeout is 30s (too long, user perceives as hang)
- No exponential backoff on retry (bursts requests)
- SSE connection hangs indefinitely if network partitions
- No probe/heartbeat to detect partition early

**Mitigation Strategies**:

1. **Client-Side Resilience**:
   ```python
   # In MCPClient
   config = MCPConfig(
       server_url="http://localhost:8360",
       api_key="...",
       timeout=5.0,  # Reduce timeout
       max_retries=3
   )

   async def call_tool_with_retry(self, tool_name, params):
       for attempt in range(self.config.max_retries):
           try:
               return await self._call_tool(tool_name, params,
                                          timeout=self.config.timeout)
           except MCPConnectionError:
               if attempt < self.config.max_retries - 1:
                   wait = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                   await asyncio.sleep(wait)
               else:
                   raise
   ```

2. **Server Heartbeat**:
   ```python
   # Client: Ping every 10s
   async def heartbeat():
       while True:
           try:
               await asyncio.wait_for(client.health(), timeout=2.0)
           except:
               logger.warning("Server unreachable (retry in 10s)")
           await asyncio.sleep(10)
   ```

3. **SSE Graceful Disconnect**:
   ```python
   # SSE client detects when stream ends
   async for event in client.subscribe_vault_events():
       if event.type == "heartbeat":
           last_heartbeat = now()

       # Check for stale heartbeat
       if now() - last_heartbeat > 30:
           logger.error("SSE stream stale, reconnecting")
           break  # Reconnect in outer loop
   ```

4. **Graceful Degradation**:
   - If MCP unreachable: Fall back to direct vault access (if local)
   - Cache last N successful responses, serve from cache if server down
   - Queue operations locally, sync when server recovers

---

## 9. Data Integrity & Loss Prevention

### 9.1 Backup & Recovery Strategy

**Severity**: CRITICAL (Permanent data loss if vault corrupted)

**Weaknesses**:
- No backups (vault is single point of truth)
- No git history (if using git vault, but not required)
- No WAL (write-ahead log)
- No daily snapshots
- No disaster recovery procedure documented

**Mitigation Strategies**:

1. **Automated Backups**:
   ```bash
   # cron: Daily at 2am
   tar -czf /backups/vault-$(date +%Y%m%d).tar.gz $VAULT_PATH
   # Keep last 30 days
   find /backups -name "vault-*.tar.gz" -mtime +30 -delete
   ```

2. **Git Tracking** (if applicable):
   ```bash
   cd $VAULT_PATH
   git init
   git config user.email "vault@cohezion"
   git add -A
   git commit -m "Initial vault import"

   # After MCP write:
   git add -A && git commit -m "Auto-commit from MCP"
   ```

3. **Write-Ahead Logging**:
   ```python
   class WALWriter:
       def write(self, path: str, content: str):
           # 1. Log to WAL
           wal_entry = {
               "timestamp": now(),
               "operation": "write",
               "path": path,
               "hash": sha256(content)
           }
           self.wal_log.append(wal_entry)

           # 2. Perform write
           vault.write(path, content)

           # 3. Mark complete in WAL
           wal_entry["complete"] = True
   ```

4. **Corruption Detection**:
   ```python
   # Periodic integrity check
   async def check_vault_integrity():
       for path in vault.list_dir(recursive=True):
           # Check file readable
           try:
               vault.read(path)
           except UnicodeDecodeError:
               logger.error("Vault file corrupted: %s", path)
               alert_ops()
   ```

---

## 10. Summary Table

| Failure Mode | Severity | Detection | Recovery | Prevention |
|---|---|---|---|---|
| Server crash | CRITICAL | Heartbeat timeout | Auto-restart | Exception handling, testing |
| Vault inaccessible | CRITICAL | Startup check | Fallback storage | Permission validation, monitoring |
| Data corruption | HIGH | Integrity check | Git history / WAL | Atomic writes, locking |
| Race conditions | HIGH | Load testing | Conflict detection | File locking, optimistic CC |
| API key exposure | CRITICAL | Audit logs | Rotate key, revoke | Secure storage, key versioning |
| Silent failures | HIGH | Structured logging | Alerts | Error response types |
| High concurrency | MEDIUM | Memory monitoring | Backpressure | Connection limits, queuing |
| Network partition | HIGH | Heartbeat | Retry with backoff | Timeouts, fallback |
| Data loss | CRITICAL | WAL replay | Restore from backup | Automated backups |

---

## 11. Recommended Immediate Actions (Priority Order)

### P0: Critical (Implement before production use)

1. **Server Crash Detection** (2h)
   - Add `/health` endpoint
   - Implement heartbeat in client
   - Add systemd auto-restart

2. **Vault Access Validation** (1h)
   - Check vault readable/writable on startup
   - Fallback storage path

3. **API Key Security** (1.5h)
   - Load from file, not environment
   - Never log key or auth header
   - Add rate limiting per key

4. **Data Corruption Prevention** (2h)
   - Atomic writes (write-to-temp-then-rename)
   - File locking for concurrent access
   - Symlink safety in `_resolve()`

### P1: High (Implement in Phase 5B.4)

5. **Error Handling Overhaul** (3h)
   - Structured error responses
   - Timeout configuration
   - Comprehensive logging

6. **Concurrency Control** (4h)
   - Bounded SSE queues
   - Connection limits
   - Request throttling

7. **Network Resilience** (2h)
   - Client-side exponential backoff
   - SSE heartbeat monitoring
   - Partition detection

### P2: Medium (Implement in Phase 6+)

8. **Automated Backups** (1h setup)
9. **Write-Ahead Logging** (3h)
10. **Distributed Secrets Management** (4h)

---

## 12. Testing Strategy

### Unit Tests
- Test `_resolve()` with path traversal attempts
- Test concurrent `.edit()` calls (expect conflict detection)
- Test error handling for all @mcp.tool() failures

### Integration Tests
- Vault inaccessibility → fallback to memory
- Network partition → exponential backoff retry
- High concurrency (20 agents, 10 req/sec each) → no corruption

### Chaos Engineering
- Kill MCP server process → Detect within 30s
- Fill disk → Graceful error on writes
- Change vault permissions → Fallback to read-only mode
- Remove API key → Return auth error, not crash
- Concurrent edits to same file → Conflict detected

---

## Appendix: Failure Mode Checklist

Use this to verify all failure scenarios are mitigated:

- [ ] Server crash detected within 30s
- [ ] Vault inaccessibility doesn't crash startup
- [ ] Starlette upgrade has migration path
- [ ] Race conditions detected (file locking or conflict detection)
- [ ] API keys not logged or exposed
- [ ] All errors caught and returned to client (no silent failures)
- [ ] Can scale to 20+ concurrent agents
- [ ] Network partition doesn't hang client indefinitely
- [ ] Vault data backed up daily
- [ ] Disaster recovery procedure documented and tested

