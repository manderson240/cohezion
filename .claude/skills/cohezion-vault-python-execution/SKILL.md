---
name: cohezion-vault-python-execution
description: |
  Correct Python execution patterns for cohezion-vault scripts.
  Use when: (1) running any script in vault's scripts/ directory,
  (2) seeing ModuleNotFoundError when running vault scripts,
  (3) creating hookify rules that match bash patterns involving python3.
  Key insight: vault has NO local pyproject.toml — must use uv run --project
  pointing at cloud-vault-mcp/. Plain uv run and bare python3 both fail.
  Hookify block action causes circular self-block — always use warn instead.
author: Claude Code
version: 1.0.0
---

# Cohezion Vault Python Execution

## Problem

Running vault scripts like `scripts/dreaming-engine.py` fails with:
```
ModuleNotFoundError: No module named 'requests'
```

Or `uv run scripts/dreaming-engine.py` fails because uv can't find the project.

## Root Cause

The vault directory has **no `pyproject.toml`**. All Python dependencies live in a
separate project: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/`.

- `python3 scripts/foo.py` — uses system Python, no vault deps
- `uv run scripts/foo.py` — fails: no local pyproject.toml to resolve
- `uv run --project /home/mike-anderson/dev/cohezion/cloud-vault-mcp scripts/foo.py` — **CORRECT**

## Solution

```bash
# Preferred — uv resolves the cloud-vault-mcp venv
uv run --project /home/mike-anderson/dev/cohezion/cloud-vault-mcp scripts/dreaming-engine.py

# Also correct — explicit venv path
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 scripts/dreaming-engine.py
```

The `--project` flag tells uv which project's venv to activate before running the script.

## Hookify Rule for Enforcement

A hookify rule exists at `.claude/hookify.venv-python-only.local.md` (and globally at
`~/.claude/hookify.venv-python-only.local.md`) that warns when bare `python3 scripts/`
is detected in a bash command.

**CRITICAL: Use `action: warn`, NOT `action: block`.**

### Why block causes a circular dependency

Hookify's own runner command is:
```
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse.py
```

Claude Code applies PreToolUse hooks to ALL Bash subprocesses, including the hook
runner itself. If the pattern `python3` is set to `block`, the hook runner tries to
run, the PreToolUse hook fires on it, and blocks it — preventing hookify from running
at all. The error looks like:

```
PreToolUse:Bash hook blocking error from command:
"python3 ${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse.py": Blocked by hook
```

This occurs even with a narrow pattern like `(?<![/\w])python3\s+scripts/` because
shell variable expansion hasn't happened yet when the hook pattern is evaluated.

**Solution:** Always use `action: warn` for patterns that could match system Python.
The warn action shows the message but allows execution to continue.

## Hookify Rule Content

```markdown
---
name: venv-python-only
enabled: true
event: bash
pattern: (?<![/\w])python3\s+scripts/
action: warn
---

**BLOCKED: bare `python3` detected.**

Use `uv run` instead — it automatically resolves the correct venv:

\`\`\`bash
# WRONG
python3 scripts/dreaming-engine.py

# CORRECT (preferred — uv resolves the cloud-vault-mcp venv)
uv run --project /home/mike-anderson/dev/cohezion/cloud-vault-mcp scripts/dreaming-engine.py

# Also correct (explicit venv path)
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 scripts/dreaming-engine.py
\`\`\`

The vault has no local `pyproject.toml`. Plain `uv run` also fails — must use `--project` to point at `cloud-vault-mcp/`.
```

## Files Updated

- `CLAUDE.md` — Python env convention updated to show `uv run --project` as preferred
- `.claude/rules/development-workflows.md` — same update
- `.claude/skills/vault-keeper/SKILL.md` — dreaming engine invocation updated
- `.claude/hookify.venv-python-only.local.md` — warn rule (project-local)
- `~/.claude/hookify.venv-python-only.local.md` — warn rule (global)

## Verification

```bash
uv run --project /home/mike-anderson/dev/cohezion/cloud-vault-mcp scripts/dreaming-engine.py
# Expected: runs successfully, updates metabolism/graph-alerts.md
```
