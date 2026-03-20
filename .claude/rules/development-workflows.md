# Development Workflows

Working with the 3D Graph Plugin and MCP Server.

## 3D Graph Plugin Development

### Setup

```bash
cd obsidian-plugin/3d-graph-plugin
npm install
```

### Development Cycle

1. **Make changes** in `src/`
2. **Watch mode** (auto-rebuild on save):
   ```bash
   npm run dev
   ```
3. **Reload plugin** in Obsidian (Ctrl+R or restart)
4. **Test changes** in 3D graph view
5. **Run tests:**
   ```bash
   npm test
   ```

### Testing Strategy

**Unit Tests (Jest):**
- Located in `src/__tests__/`
- Test individual components/services
- Run: `npm test`

**Manual Testing:**
- Open Obsidian vault
- Enable plugin in Settings → Community plugins
- Open 3D graph view (ribbon icon or Cmd+P)
- Verify visualization, interactions, search, filters

### Build for Production

```bash
npm run build
```

Output: `main.js` (copy to `.obsidian/plugins/3d-graph-plugin/`)

### Common Issues

**Plugin not loading:**
- Check `manifest.json` version matches
- Check console for errors (Ctrl+Shift+I in Obsidian)
- Verify `main.js` exists in plugin directory

**Graph not rendering:**
- Check `.claude/3d-graph-data.json` exists
- Verify data format matches schema
- Check console for Three.js errors

## MCP Server Development

### Setup

```bash
cd mcp-server
pip install -e ".[dev]"
```

### Development Cycle

1. **Make changes** in `src/kyutai_mcp/`
2. **Run server** (auto-reload):
   ```bash
   uvicorn kyutai_mcp.main:app --reload
   ```
3. **Test endpoints** with curl or httpie
4. **Run tests:**
   ```bash
   pytest
   ```

### Testing Strategy

**Unit Tests (pytest):**
- Located in `tests/`
- Test tools, handlers, data processing
- Run: `pytest` or `pytest -v` (verbose)

**Integration Tests:**
- Test MCP protocol compliance
- Test with actual Obsidian vault data
- Verify tool responses

### Code Quality

**Format:**
```bash
black .
```

**Lint:**
```bash
ruff .
```

**Type Check:**
```bash
mypy .
```

**Run all checks:**
```bash
black . && ruff . && mypy . && pytest
```

### Docker Deployment

```bash
# Build image
docker-compose build

# Run server
docker-compose up

# With config
docker-compose up -e CONFIG_PATH=/path/to/config.yaml
```

## Python Environment

**CRITICAL:** Use `uv run` — never bare `python3`:

```bash
# ❌ WRONG
python3 script.py

# ✅ RIGHT (preferred)
uv run script.py

# ✅ ALSO RIGHT (explicit venv path)
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 script.py
```

**Why:** `uv run` automatically resolves the correct venv and all its dependencies. Bare `python3` uses the system Python which lacks vault dependencies.

## Common Workflows

### Adding a New Paper to 3D Graph

1. Add paper markdown to `sensory/`
2. Include frontmatter with tags
3. Regenerate graph data:
   ```bash
   uv run .claude/extract_3d_graph.py
   ```
4. Reload plugin in Obsidian

### Adding a New MCP Tool

1. Define tool in `src/kyutai_mcp/tools/`
2. Register in `src/kyutai_mcp/main.py`
3. Add tests in `tests/`
4. Update documentation
5. Restart server

### Debugging

**Plugin (TypeScript):**
- Use Obsidian Developer Console (Ctrl+Shift+I)
- Add `console.log()` statements
- Check for errors in console

**MCP Server (Python):**
- Use `print()` or logging
- Check server logs
- Use `pytest` with `-s` flag to see print output
