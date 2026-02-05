# Bug Hunt Swarm Report - 2026-02-05 08:11

Total Issues Processed: 1

## 🐞 Bug in `src/cohezion/maintenance/pruner.py:40`
- **Original Issue**: Blocking 'subprocess.run' in async function 'monitor_git_health'. Use 'asyncio.create_subprocess_exec' or run_in_executor.
- **Scout Confidence**: 0.95
- **Auditor Score**: 0.65
### Impact
The use of `subprocess.run()` in an async function (`monitor_git_health`) blocks the asyncio event loop, preventing concurrent coroutines from running during command execution. While `git ls-files | wc -l` is fast, blocking even briefly in high-frequency or concurrent async contexts (e.g., during automated maintenance cycles or when multiple agents run) degrades responsiveness and throughput. Additionally, the shell command is incorrectly constructed: `['git', 'ls-files', '|', 'wc', '-l']` treats `'|'` as a literal argument to `git ls-files`, not a pipe — this will cause `git ls-files` to fail with an error about unknown pathspec '|', leading to incorrect behavior or exception. The code then tries to parse an empty or error output as `int(result.stdout.strip())`, which will raise `ValueError` or `subprocess.CalledProcessError` (if `check=True` were used), crashing the health check. This is both a correctness bug (invalid shell command) and a performance anti-pattern (blocking I/O in async context).
### Extracted Pattern
The code follows a pattern of using an LLM to analyze code density and score files for potential pruning. It implements a recursive directory scanner with exclusion filters, and uses a scoring system to determine which files are candidates for pruning. It also includes a git health monitor to detect bloat.
### Suggested Fix
```python
Routing Error:  | Fallback Error: 
```

---

