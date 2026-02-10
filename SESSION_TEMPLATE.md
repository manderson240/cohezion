# Session XX Startup & Workflow Template

**For every session**: Copy this template and personalize

## ⚡ Quick Start (5 min)

```bash
SESSION_ID="47"
PHASE="phase-name"
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b session-${SESSION_ID}-${PHASE}
cd ~/dev/cohezion-session-${SESSION_ID}
./scripts/validate-session-setup.sh
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q
```

## Daily Workflow

- **Start**: Validate setup + check git status
- **Work**: Make changes, test frequently, commit atomically
- **End**: Full test suite + create SESSION_XX_SUMMARY.md

## Reference

- CLAUDE.md: Project rules
- MEMORY.md: Architecture
- GIT_WORKTREE_ENFORCEMENT.md: Git help

*Compound Engineering: Each session follows this template → exponential team efficiency*
