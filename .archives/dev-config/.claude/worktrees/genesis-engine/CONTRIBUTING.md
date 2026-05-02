# Contributing to Cohezion

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only |
| `develop` | Active development |
| `feature/*` | New features |
| `fix/*` | Bug fixes |

### Workflow

1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-feature
   ```

2. Make changes with atomic commits

3. Push and create PR to `develop`

4. After review, merge to `develop`

5. Periodic releases merge `develop` → `main`

## Pre-commit Hooks

Hooks run automatically on commit:
- **ruff**: Lint and format Python
- **mypy**: Type checking
- **trailing-whitespace**: Remove trailing spaces
- **check-yaml/json**: Validate config files

On push:
- **pytest**: Run full test suite

### Manual Run

```bash
# Run all hooks
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
```

## Adding a Skill

1. Create `skills/MY_SKILL_PRIME.md`
2. Register:
   ```python
   from cohezion.registry.skill_registry import register_skill
   register_skill("MY_SKILL_PRIME", "Description", ["keywords"], "skills/MY_SKILL_PRIME.md")
   ```

## Adding an MCP Server

1. Create `mcp/my_server.py` with tools
2. Add to `mcp/mcp_registry.json`
3. Test with:
   ```python
   from cohezion.mcp.my_server import get_server
   server = get_server()
   ```

## Code Style

- Type hints required for public functions
- Docstrings for all classes and public methods
- Max line length: 88 (ruff default)
- PEP 8 compliance enforced

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/cohezion
```
