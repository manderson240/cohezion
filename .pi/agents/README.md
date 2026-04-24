# Cohezion Pi Side Agents

This directory contains lifecycle scripts for [pi-side-agents](https://github.com/pasky/pi-side-agents) integration.

## Scripts

### `worktree-init`
Automatically runs when a new side agent worktree is created:
- Installs dependencies with `uv sync`
- Runs format + lint + type-check
- Prepares worktree for development

### `merge`
Runs before merging side agent work back to main:
- Executes `make test-fast`
- Runs `make lint-check`
- Runs `make type-check`
- Blocks merge if any checks fail

## Usage

```bash
# Spawn a side agent
/agent test hypothesis: memoization improves cache hit rate

# Agent gets:
# - Dedicated tmux window
# - Isolated git worktree
# - Auto-initialized environment (via worktree-init)

# When agent completes:
# - Switch to tmux window (Ctrl+B <num>)
# - Review work with git diff
# - Type "LGTM" to trigger merge validation (via merge script)
# - Auto-commits and merges to main
```

## Cost Optimization

For parallel autoresearch experiments:
```bash
# Main agent: expensive model for orchestration
# Side agents: cheaper models for parallel testing
/agent -model minimax-m2.7:cloud test caching strategy A
/agent -model glm-5:cloud test caching strategy B
/agent -model qwen3.5:cloud test caching strategy C
```

## Security

Side agents inherit pi extension configuration from main session:
- ✅ SECURITY mode: MAX by default
- ✅ Command blocklist: 66 commands blocked
- ✅ SSRF protection: 48 patterns blocked

## Notes

- Worktrees are reused across sessions (auto-pruned on reuse)
- Old branches persist until explicitly deleted
- Each side agent is single-use (dies with `/quit`)
