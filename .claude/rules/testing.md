---
paths:
  - "tests/**"
---

# Testing Rules

- Run tests with `uv run pytest` — never bare `pytest`
- Use `pytest-asyncio` for async test functions
- Avoid `walk_packages` import scans — they hang on modules with heavy init (quantization engine, IDE configs). Use targeted `importlib.import_module()` tests instead
- Mock external services (Ollama, SurrealDB) rather than requiring live connections
- Test HIHO coherence invariant (0.5 overlap) for any simulation or physics module
- Pydantic models at boundaries should have schema validation tests
- Never commit tests that depend on specific file counts or line counts — the codebase is actively being cleaned up
