---
name: stop-learn-check
enabled: true
event: stop
pattern: .*
action: warn
---

## Session End — Learning Check

Before stopping, evaluate if this session produced extractable knowledge:

### Quick Decision Tree:
1. **Did you discover a non-obvious solution?** (spent 10+ min investigating, solution not in docs)
2. **Did you hit a new dead end?** (tried something, confirmed it doesn't work)
3. **Did you build a repeatable workflow?** (multi-step task that will recur)
4. **Did you get submission results?** (any popcorn test/benchmark/leaderboard data)
5. **Did you probe an API?** (discovered calling conventions, error modes, timing data)

**If YES to any → invoke `/learn` before stopping.**

### Kernel skill update check:
- Were any results from `amd-gemm-mxfp4-optimization` submissions recorded?
- Were any results from `amd-moe-mxfp4-optimization` submissions recorded?
- Were any results from `amd-mla-decode-optimization` submissions recorded?
- Was `competitive-kernel-optimization-ceiling` dead-end list updated?

### Plan update check:
- Is the plan status still accurate? (PENDING/COMPLETE/VERIFIED)
- Were any submissions in the plan completed? Mark them done.

**If nothing was learned → stop silently, no action needed.**
