# Cohezion Vault

Knowledge base for the Cohezion agentic AI framework, managed as an Obsidian vault.

## Agent Orientation

**New to this vault?** Read `VAULT_MANIFEST.md` first — it maps every directory, explains where to put your output, and lists entry points. Each directory also has a `_index.md` file with purpose, conventions, and key notes.

**Graph awareness?** Read `metabolism/graph-briefing.md` for vault shape, hot neurons, bridges, and attention items (~1000 tokens, updated by cron).

The `/vault-keeper` skill runs proactively — it monitors vault health and acts on issues without being asked. See `.claude/skills/vault-keeper/SKILL.md` for details.

## Structure — The Triune Self

### The Knower (awareness, ground truth)
| Directory | Purpose |
|-----------|---------|
| `cortex/` | Core concepts and definitions (was `concepts/`) |
| `sensory/` | Research papers, external observations (was `papers/`) |
| `memory/` | Lessons learned — embodied knowledge (was `lessons/`) |
| `genome/` | System blueprints — specs, skills, agents (was `specs/`) |

### The Thinker (reasoning, judgment)
| Directory | Purpose |
|-----------|---------|
| `prefrontal/` | Architecture Decision Records (was `decisions/`) |
| `laboratory/` | Hypothesis testing and results (was `experiments/`) |
| `cerebellum/` | Reusable patterns and procedures (was `patterns/`) |

### The Doer (action, lived experience)
| Directory | Purpose |
|-----------|---------|
| `motor/` | Project tracking and action plans (was `projects/`) |
| `hippocampus/` | Daily notes, session logs (was `daily/` + `sessions/`) |
| `thalamus/` | Unsorted intake — triage point (was `inbox/`) |
| `missions/` | Multi-agent coordinated tasks |
| `retrospectives/` | Post-session analysis |

### The Connective (where all three meet)
| Directory | Purpose |
|-----------|---------|
| `dreaming/` | Cross-domain resonances (SurrealDB-generated) |
| `songlines/` | Narrative knowledge paths across domains |
| `subconscious/` | Latent associations — notes that should be linked |
| `metabolism/` | System health dashboards |
| `visual-cortex/` | Canvases and spatial diagrams (was `canvas/`) |

## Repository Branch Model

This repo has **two parallel, disconnected git histories** — `track-c` and `main` share no common ancestor and cannot be merged without a major restructuring effort.

| Branch | Purpose | Notes |
|--------|---------|-------|
| `track-c` | Vault content + cohezion tooling | Obsidian notes, decisions, patterns, cohezion-engine, research pipeline |
| `main` | Platform code | Separate project, different origin |

**Working rules:**
- All vault and tooling work happens on `track-c`
- Do not attempt `git merge`, `git rebase`, or `git diff origin/main` across branches — there is no merge base
- PRs from `track-c` feature branches target `track-c` (not `main`)
- The `/security-review` command has a local override that handles the no-merge-base case

**Known debt:** This split is intentional for now but is technical debt. See `motor/repo-and-process-debt.md` for the plan to address it.

## Conventions

- Notes use YAML frontmatter with `title`, `date`, `status`, and `tags` fields
- Tags are arrays in frontmatter (e.g., `tags: [decision, architecture]`)
- Templates in each directory use `_template.md` naming
- Obsidian wiki-links (`[[note]]`) are used for cross-referencing

## MCP Integration

- **Cloud Vault MCP Server** on port 8360 — programmatic vault access
- **Claude Code MCP Plugin** on port 22360 — IDE integration

## Working with This Vault

- When fleshing out thalamus notes, research the topic thoroughly and write structured content in-place
- Respect existing frontmatter schemas when creating notes in templated directories
- Keep notes atomic and cross-linked where relevant
- When moving notes from `thalamus/` to a permanent directory, add appropriate frontmatter and `aspect:` field

## Claude Code Best Practices

### Tool Selection Matrix (Read Instead of Bash)

**File Operations** — Use dedicated tools instead of `cat`, `grep`, `find`, `sed`:

| Task | Tool | Example | Why NOT Bash? |
|------|------|---------|---------------|
| Read a file | **Read** | `Read("/path/file.py")` | More transparent, supports images/PDFs |
| Search file content | **Grep** | `Grep("pattern", "*.ts")` | Ripgrep optimized, regex support |
| Find files by pattern | **Glob** | `Glob("**/*.md")` | Fast pattern matching, no shell escaping |
| Edit text in file | **Edit** | `Edit(file, old, new)` | Precise replacement, preserves formatting |
| Create new file | **Write** | `Write(file, content)` | Atomic, clear intent |
| Execute commands | **Bash** | `Bash("git status")` | Only for terminal operations |

**Decision Tree**:
```
Need to read/modify files?
├─ Read file content → Read
├─ Search files → Grep (content) or Glob (filenames)
├─ Modify text → Edit
├─ Create file → Write
└─ Run command (git/npm/docker) → Bash
```

**Anti-patterns to avoid**:
- ❌ `bash: cat file.txt` → use `Read("file.txt")`
- ❌ `bash: grep pattern file` → use `Grep("pattern", path)`
- ❌ `bash: find . -name "*.ts"` → use `Glob("**/*.ts")`
- ❌ `bash: sed 's/old/new/' file` → use `Edit(file, old, new)`

### Parallelization Guidelines

**Parallel Execution**: Call independent tools together to maximize efficiency.

**When to parallelize**:
- Multiple independent reads (e.g., read 3 config files)
- Multiple independent searches (e.g., grep multiple patterns)
- Mixed independent operations (read A, glob B, read C)

**When NOT to parallelize**:
- One tool's output feeds into another (e.g., read file → edit based on content)
- Sequential dependencies exist
- Results must be analyzed between operations

**Example**:
```
❌ Sequential (slow):
1. Read file A
2. Based on A, decide to read file B
3. Read file B
→ 3 separate round-trips, waits between each

✅ Parallel (fast):
Call Read(A), Read(B), Glob(pattern) together
→ 1 round-trip, all results at once
```

**Expected gain**: 30-50% time savings per multi-tool session

### Agent Delegation Strategy

**When to spawn agents vs. work inline**:

| Scenario | Action | Why |
|----------|--------|-----|
| Simple file read + edit | Inline | Overhead not worth it |
| Multi-step research task | Spawn Explore agent | Parallel work, protect context |
| Codebase search + analysis | Spawn Explore agent | Deep pattern matching |
| Architectural design | Spawn Plan agent | Complex trade-offs |
| Implementation (10+ files) | Spawn general-purpose agent | Context budget protection |
| Run tests/builds | Spawn Bash agent | Non-blocking execution |

**Agent Types** (see PRIME_CLAUDE_CODE_PRACTICES for details):
- **Explore**: Fast pattern matching, codebase analysis, multi-round search
- **Plan**: Architecture + implementation strategy (requires approval)
- **general-purpose**: Multi-step implementation + tests
- **Bash**: Terminal operations (git, npm, pytest, docker)

### Memory System Strategy

**Location**: `/home/mike-anderson/.claude/projects/-home-mike-anderson-vaults-cohezion-vault/memory/`

**What to save** (persists across sessions):
- ✅ Project conventions + infrastructure details
- ✅ Lessons learned from past mistakes
- ✅ Token efficiency patterns (cost per task type, ROI calculations)
- ✅ Repeated procedures (e.g., Python venv path, MCP discovery)
- ✅ Service endpoints + configuration quirks

**What NOT to save**:
- ❌ Session-specific context (current task, in-progress work)
- ❌ Speculative information (not yet validated)
- ❌ Duplicates of CLAUDE.md or project documentation
- ❌ Personally identifiable information or secrets

**ROI**: Saves 5-10K tokens per session through knowledge reuse

### MCP Tool Awareness

**Available MCP Servers** (configured in `~/.claude/mcp.json`):

1. **Cloud Vault MCP** (port 8360)
   - VaultOps: Query papers, decisions, lessons, concepts
   - CompoundOps: Semantic linking, cross-validation
   - ObsidianOps: Create wiki-links, update frontmatter
   - Teleport: Cloud↔local file sync
   - SheetsBridge: Batch update Google Sheets
   - SurrealDB: Query agent context graph

2. **Ollama MCP** (port 22360)
   - embed: Generate embeddings for semantic search
   - query: Vector search across vault
   - batch: Bulk operations
   - select_model: Choose Ollama model
   - status: Check Ollama health

**When to use**:
- Searching vault programmatically? → Cloud Vault MCP
- Semantic search + embeddings? → Ollama MCP
- Creating vault notes automatically? → ObsidianOps
- Batch updating sheets? → SheetsBridge
- Querying agent decisions? → SurrealDB

### Git Safety Protocol (Commit Before Destructive Ops)

**Safe operations** (no confirmation needed):
- `git status`, `git diff`, `git log`
- `git add [specific files]`
- `git commit -m "message"`

**Risky operations** (ALWAYS confirm first):
- Force-push: `git push --force` or `git push -f`
- Hard reset: `git reset --hard`, `git restore .`, `git clean -f`
- Branch deletion: `git branch -D`
- Rebasing published commits: `git rebase`
- Amending published commits: `git commit --amend`

**Confirmation template before risky ops**:
```
"I'm about to [operation]. This will [specific consequence].
[Who might be affected?]. OK to proceed?"
```

**Never bypass** safety checks with flags like `--no-verify`, `--force-with-lease`, etc.
unless explicitly authorized for that specific operation.

### Python Environment Conventions

**CRITICAL**: Use `uv run` — never bare `python3`:

```bash
# ❌ WRONG
python3 script.py

# ✅ RIGHT (preferred)
uv run script.py

# ✅ ALSO RIGHT (explicit venv path)
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 script.py
```

**Why**: `uv run` automatically resolves the correct venv, ensuring all dependencies (`requests`, `surrealdb`, etc.) are available. Bare `python3` uses the system Python which lacks vault dependencies.

### Token Budget Strategy

**Current baseline** (as of 2026-02-12): ~17% usage (34k/200k tokens)

**Strategy by task complexity**:

| Complexity | Tokens | Approach |
|-----------|--------|----------|
| Simple (read/edit 1-2 files) | <10k | Execute inline |
| Medium (3-5 files, analysis) | 10-30k | Execute inline or light agent use |
| Complex (10+ files, testing) | 30-100k | Spawn agent(s) |
| Research-heavy (multi-round) | 100k+ | Spawn agent + parallelize |

**Avoid**: Keeping large search results in context. Instead:
1. Use agent to search + collect results
2. Agent returns structured data (JSON)
3. You process and update files from lead context

**Save cost**: Agents cost ~1/3 of inline work (Haiku model + focus)

---

## Production Governance

See [[PRIME_CLAUDE_CODE_PRACTICES]] for executable procedures that operationalize these guidelines.

Guidelines encode platform best practices; the PRIME skill makes them discoverable + automatic.
