# Tutorial Audit — 2026-06-25

**Scope:** All 10 files in `docs/tutorials/`. Checks: Python 3.11 syntax in tagged code blocks, `cohezion.*` import path resolution, `src/cohezion/` file path existence, old pattern flags (bare `pip install`, `sys.path.insert`, port 11434, `OLLAMA_*`).

**Summary:** 1 PASS, 2 WARN, 7 FAIL. Root cause of most FAILs is **non-Python content in ```` ```python ```` blocks** (bash commands, pseudo-code with em-dashes, YAML payloads, IP:port strings). Import paths and `src/` file references are mostly accurate; the content staleness is primarily syntactic.

---

## Findings Table

| Tutorial | Status | Issues |
|----------|--------|--------|
| `01-day-1-setup-and-first-test.md` | FAIL | 11 syntax errors in Python-tagged blocks (em-dashes, unterminated strings, bash in python blocks) |
| `01-getting-started.md` | FAIL | 3 syntax errors + `pip install` reference (should be `uv sync`) |
| `02-day-2-the-compound-loop.md` | FAIL | 10 syntax errors (decimal literals like `3.11.0`, em-dashes `—`, `≈` symbol) |
| `02-physics-walkthrough.md` | **PASS** | 0 issues |
| `03-day-3-skills-and-vault.md` | FAIL | 12 syntax errors (em-dashes, `→` arrow, mismatched parens/braces) |
| `03-world-model.md` | FAIL | 5 syntax errors (version strings like `0.9.0` parsed as invalid decimal) |
| `04-day-7-running-a-campaign.md` | FAIL | 6 syntax errors (em-dash in python blocks, truncated multi-line examples) |
| `04-rl-environment.md` | WARN | 2 syntax errors (unexpected indent in pseudo-code block) |
| `05-day-30-contributing-an-architectural-change.md` | FAIL | 11 syntax errors (em-dashes, leading zeros, `expected 'else'`) |
| `INDEX.md` | WARN | `pip install` in backtick reference (pocket-tts — minor) |

---

## Key Patterns

1. **Em-dash contamination** (`—`, U+2014): Appears in 5 tutorials inside Python-tagged code blocks. The harness already bans em-dashes in YAML/code (per `harness.md`); the tutorials pre-date this rule.
2. **Version strings in Python blocks** (`3.11.0`, `0.9.0`): Interpreted as invalid decimal literals by `ast.parse`. These should be in plain text or shell blocks.
3. **`pip install` in `01-getting-started.md`**: Should use `uv sync` per CLAUDE.md security standards.
4. **Import paths**: All `cohezion.*` imports verified against `src/cohezion/` — no dead module paths found.
5. **File paths**: No `src/cohezion/` references to missing files found.

---

## Recommended Actions

| Priority | Action |
|----------|--------|
| P1 | Re-tag bash/shell commands in tutorials from ` ```python ` to ` ```bash ` |
| P1 | Replace em-dashes with `--` in all Python code blocks |
| P2 | Update `01-getting-started.md`: `pip install -e .` → `uv sync` |
| P2 | Replace version strings like `3.11.0` in Python blocks with bash or plain text |
| P3 | Add `INDEX.md` clarification: reference to `uv add pocket-tts` not bare `pip install` |
