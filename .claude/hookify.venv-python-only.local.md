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

# CORRECT
uv run scripts/dreaming-engine.py

# Also correct (explicit venv path)
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 scripts/dreaming-engine.py
```

`uv run` picks up the project venv, ensuring `requests`, `surrealdb`, and all vault dependencies are available.
