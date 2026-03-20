---
name: venv-python-only
enabled: true
event: bash
pattern: (?<![/\w])python3\s+scripts/
action: warn
---

**BLOCKED: bare `python3` detected.**

Use `uv run` instead — it automatically resolves the correct venv:

```bash
# WRONG
python3 scripts/dreaming-engine.py

# CORRECT (preferred — uv resolves the cloud-vault-mcp venv)
uv run --project /home/mike-anderson/dev/cohezion/cloud-vault-mcp scripts/dreaming-engine.py

# Also correct (explicit venv path)
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 scripts/dreaming-engine.py
```

The vault has no local `pyproject.toml`. Plain `uv run` also fails — must use `--project` to point at `cloud-vault-mcp/`.
