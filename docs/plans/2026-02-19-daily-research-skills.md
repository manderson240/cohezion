# Daily Research Skills Integration Plan

Created: 2026-02-19
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Build a large-scale daily research pipeline that scans dozens of public sources for new techniques, tools, and patterns relevant to Cohezion — covering compound engineering, token efficiency, context awareness, and app creation. Produces both individual inbox notes (deep dives) and a comprehensive daily digest. Invocable as `/research` command and schedulable via cron.

**Architecture:** A Python-based research pipeline with three stages:
1. **Harvest** — Parallel searches across 6 source types: web search (~24 queries), GitHub trending/releases, HackerNews, Reddit, arXiv papers, and tracked blogs. Targets 200+ raw findings per run.
2. **Score & Filter** — Hybrid evaluation: keyword/category match first (zero-cost), then Ollama local LLM scoring for relevance to Cohezion's four focus areas. Keeps top 50-80 scored findings.
3. **Synthesize & Publish** — Produces 30-50 individual `inbox/` notes with proper frontmatter + a comprehensive `daily/` digest note with per-focus-area sections linking everything. The Claude Code `/research` skill orchestrates this pipeline.

**Tech Stack:** Python 3.10+, `duckduckgo-search` Python package (primary web search), GitHub API (via `gh` CLI search endpoint), HackerNews Algolia API, Reddit JSON API, arXiv API, Ollama for local scoring, Obsidian vault output with frontmatter.

## Scope

### In Scope

- Python research pipeline package (`research/`) with harvest/score/publish stages
- Source configuration file (`research/sources.yaml`) defining search queries, source URLs, categories
- Standalone CLI interface (`research/cli.py`) usable from any AI coding tool via bash
- MCP server endpoint (`research/mcp_server.py`) for MCP-compatible tools (Claude Code, OpenCode, etc.)
- Claude Code skill (`.claude/skills/daily-research/SKILL.md`) + command (`.claude/commands/research.md`) as one access method
- Cron wrapper script (`research/run_research.sh`) for automated daily execution
- Vault output: inbox notes + daily digest note following existing conventions
- Scoring rubric aligned to Cohezion's 4 focus areas with configurable weights
- Skill candidate detection: findings describing reusable tools, patterns, or techniques are flagged for integration via `/learn` → `/vault` workflow

### Out of Scope

- Paid API integrations (all sources are free/public)
- Real-time streaming or webhooks (batch daily processing only)
- Automatic integration of findings into Cohezion code (human triage step preserved)
- MCP server for the research pipeline (future enhancement)
- Dashboard or UI for viewing results (vault + Obsidian graph is the UI)

## Prerequisites

- Python 3.10+ with a dedicated venv for the research pipeline (`research/.venv/`)
- Install dependencies: `pip install duckduckgo-search pyyaml requests` (into research venv)
- Ollama running on port 11434 with a scoring model (recommend `mistral:latest` 7B for speed/quality balance)
- `gh` CLI authenticated for GitHub search/release scanning
- Vault directories (`inbox/`, `daily/`) exist (they do)

## Context for Implementer

> This section is critical for cross-session continuity. Write it for an implementer who has never seen the codebase.

- **Patterns to follow:** The vault uses YAML frontmatter with `title`, `date`, `status`, `tags` (arrays). See `patterns/_template.md` for the pattern template structure. Daily notes follow the format in `daily/2026-02-09-lessons-integration-complete.md`.
- **Conventions:** Tags are YAML arrays (`tags: [research, compound-engineering]`), never comma-separated strings. Notes use Obsidian wiki-links (`[[note-name]]`). Inbox notes don't require full frontmatter but benefit from it.
- **Key files:**
  - `concepts/compound-engineering.md` — Defines the 4 pillars of compound engineering
  - `concepts/token-efficiency.md` — Token optimization principles and anti-patterns
  - `concepts/context-management.md` — Context awareness concepts
  - `patterns/compound-async-executor-pattern.md` — The 7-step execution pipeline
  - `experiments/2026-02-07-ai-research-agent-for-vault-notes.md` — Prior art: AI research agent producing vault-quality notes
  - `.claude/commands/learn.md` — Skill creation patterns and SKILL.md template
- **Gotchas:**
  - The research pipeline has its own venv at `research/.venv/` — create it during setup and install deps there to avoid polluting other project venvs
  - Ollama may not always be running; the pipeline should gracefully fall back to keyword-only scoring
  - DuckDuckGo rate-limits aggressive scraping; use delays between queries
- **Domain context:** Cohezion's four research focus areas are:
  1. **Compound engineering** — Knowledge accumulation, decision records, pattern extraction, session-over-session improvement
  2. **Token efficiency** — LLM cost optimization, model selection, batching, template reuse, local-first processing
  3. **Context awareness** — Context window management, memory persistence, cross-session continuity, context injection
  4. **App creation** — Agentic AI frameworks, MCP servers, tool development, code generation patterns

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Research pipeline core engine
- [x] Task 2: Source configuration and harvest module
- [x] Task 3: Hybrid scoring engine
- [x] Task 4: Vault publisher module
- [x] Task 5: Claude Code skill and command
- [x] Task 6: Cron wrapper and automation

**Total Tasks:** 6 | **Completed:** 6 | **Remaining:** 0

## Implementation Tasks

### Task 1: Research Pipeline Core Engine

**Objective:** Build the main pipeline orchestrator that coordinates harvest → score → publish stages. This is the backbone that all other tasks plug into.

**Dependencies:** None

**Files:**

- Create: `research/pipeline.py` — Main pipeline class with `run()` method
- Create: `research/__init__.py` — Package init
- Test: `research/tests/test_pipeline.py` — Pipeline orchestration tests

**Key Decisions / Notes:**

- Use `asyncio` for parallel harvest operations (multiple search queries at once)
- Pipeline class takes a config dict and returns a `ResearchReport` dataclass with all findings
- Each stage is a separate method: `harvest()`, `score()`, `publish()`
- Logging to stdout for both CLI and cron visibility
- Error handling: individual source failures don't halt the pipeline; log and continue

**Definition of Done:**

- [ ] `ResearchReport` dataclass defined with fields: `findings`, `scores`, `metadata`, `timestamp`
- [ ] `Finding` dataclass: `title`, `url`, `source`, `snippet`, `category`, `raw_score`
- [ ] Pipeline `run()` orchestrates all three stages in sequence
- [ ] Pipeline handles partial failures (one source down → others still work)
- [ ] Unit tests verify pipeline orchestration with mock stages

**Verify:**

- `research/.venv/bin/python3 -m pytest research/tests/test_pipeline.py -q`

### Task 2: Source Configuration and Harvest Module

**Objective:** Build the harvest stage that searches 20+ query categories across multiple source types (web search, GitHub, community forums). Configuration-driven via YAML.

**Dependencies:** Task 1

**Files:**

- Create: `research/sources.yaml` — Source definitions with query templates
- Create: `research/harvester.py` — Harvest module with source-specific adapters
- Test: `research/tests/test_harvester.py` — Harvester tests with mock responses

**Key Decisions / Notes:**

- Source types (6 adapters):
  - `web_search` — DuckDuckGo via `duckduckgo-search` Python package (primary)
  - `github_recent` — `gh` CLI trending repos by language
  - `github_releases` — `gh` CLI release monitoring for tracked repos
  - `hackernews` — HN Algolia API (`hn.algolia.com/api/v1/search`) for recent AI/engineering posts
  - `reddit` — Reddit JSON API (`reddit.com/r/{sub}.json`) for r/MachineLearning, r/LocalLLaMA, r/artificial, r/ClaudeAI
  - `arxiv` — arXiv API (`export.arxiv.org/api/query`) for cs.AI, cs.CL, cs.SE categories
  - `blog_feeds` — Tracked blog URLs checked for new posts (Simon Willison, Lilian Weng, Chip Huyen, The Gradient, etc.)
- YAML config structure (abbreviated — full config has 6+ queries per focus area, 24+ total):
  ```yaml
  focus_areas:
    compound_engineering:
      queries:
        - "compound AI system architecture 2026"
        - "knowledge graph agent memory"
        - "decision record automation ADR"
        - "session memory persistence LLM"
        - "pattern extraction from code"
        - "multi-session AI workflow"
      weight: 1.0
    token_efficiency:
      queries:
        - "LLM token optimization techniques"
        - "context window compression"
        - "prompt caching strategies"
        - "speculative decoding inference"
        - "KV cache optimization"
        - "model distillation efficiency"
      weight: 1.0
    context_awareness:
      queries:
        - "context window management LLM"
        - "long context retrieval augmented"
        - "memory augmented language model"
        - "cross-session context injection"
        - "RAG pipeline optimization"
        - "semantic memory agent"
      weight: 1.0
    app_creation:
      queries:
        - "agentic AI framework 2026"
        - "MCP server model context protocol"
        - "AI code generation tool"
        - "tool use function calling LLM"
        - "multi-agent orchestration"
        - "AI app builder framework"
      weight: 1.0
  sources:
    github_recent:
      languages: [python, typescript, rust]
      since: daily
    github_releases:
      repos:
        - anthropics/anthropic-sdk-python
        - anthropics/claude-code
        - modelcontextprotocol/servers
        - langchain-ai/langchain
        - run-llama/llama_index
        - openai/openai-python
        - huggingface/transformers
        - vllm-project/vllm
        # ... 20+ repos total
    hackernews:
      tags: [story]
      queries: ["AI agent", "LLM tool", "context window", "MCP server"]
      min_points: 10
    reddit:
      subreddits: [MachineLearning, LocalLLaMA, artificial, ClaudeAI]
      sort: hot
      limit: 25
    arxiv:
      categories: [cs.AI, cs.CL, cs.SE]
      max_results: 30
    blog_feeds:
      urls:
        - https://simonwillison.net
        - https://lilianweng.github.io
        - https://huyenchip.com/blog
        - https://thegradient.pub
        - https://www.latent.space
  ```
- Use `duckduckgo-search` Python package directly for web searches (primary, no subprocess dependency)
- Use `gh api search/repositories` with date filters (`sort:stars created:>YYYY-MM-DD`) for recently popular repos (GitHub has no trending API — the trending page is HTML-only)
- HackerNews Algolia API is free, no auth, returns JSON directly
- Reddit `.json` endpoint is free, no auth for public subreddits
- arXiv API is free, no auth, returns Atom XML (parse with `xml.etree`)
- Blog feeds: fetch index page via `requests`, parse for new post links
- Rate limiting: 2-second delay between web search queries, 1-second between other API calls
- Target: 200+ raw findings per run across all sources

**Definition of Done:**

- [ ] YAML config defines 24+ search queries across 4 focus areas (6+ per area)
- [ ] YAML config lists 20+ GitHub repos for release monitoring
- [ ] Web search adapter returns `Finding` objects from DuckDuckGo results
- [ ] GitHub adapter returns `Finding` objects from recently popular repos (via search API with date filters) and releases
- [ ] HackerNews adapter queries Algolia API and returns `Finding` objects
- [ ] Reddit adapter fetches subreddit JSON and returns `Finding` objects
- [ ] arXiv adapter queries API for recent papers and returns `Finding` objects
- [ ] Blog feed adapter checks tracked URLs for new posts
- [ ] Rate limiting prevents API throttling (2s web search, 1s other APIs)
- [ ] Harvest runs all source types in parallel with `asyncio.gather()`
- [ ] Config is validated on load (missing fields → clear error message)

**Verify:**

- `research/.venv/bin/python3 -m pytest research/tests/test_harvester.py -q`
- `research/.venv/bin/python3 -c "from research.harvester import load_config; c = load_config('research/sources.yaml'); print(f'Loaded {len(c[\"focus_areas\"])} focus areas')"`

### Task 3: Hybrid Scoring Engine

**Objective:** Build the two-tier scoring system: fast keyword matching (tier 1) filters down to candidates, then Ollama local LLM scoring (tier 2) ranks by Cohezion relevance.

**Dependencies:** Task 1

**Files:**

- Create: `research/scorer.py` — Scoring engine with keyword and LLM tiers
- Test: `research/tests/test_scorer.py` — Scorer tests

**Key Decisions / Notes:**

- **Tier 1 — Keyword scoring (free, fast):**
  - Each focus area has a keyword set (e.g., compound engineering: `["compound", "knowledge graph", "decision record", "session memory", "pattern extraction"]`)
  - Score = weighted count of keyword matches in title + snippet
  - Threshold: findings scoring 0 on keywords are discarded
  - Expected filter: 200+ raw → 80-120 candidates
- **Tier 2 — Ollama LLM scoring (free, slower):**
  - Prompt template sends finding title + snippet + source to local Ollama model
  - Model rates 1-10 on each of the 4 focus areas + overall relevance
  - Use `requests` to call Ollama API at `http://localhost:11434/api/generate` with model specified in YAML config (default: `mistral:latest` — good quality/speed for classification; avoid large models like 80B that would take hours)
  - Graceful fallback: if Ollama unavailable, use keyword scores only (warn in log)
  - Expected filter: 80-120 candidates → top 50-80 scored findings
- Scoring output: each `Finding` gets a `scores` dict with per-area and overall scores
- **Skill candidate detection:** Tier 2 Ollama prompt also classifies whether the finding describes a reusable tool, pattern, or technique that could become a Cohezion skill. Adds `skill_candidate: true/false` and `skill_type: [tool|pattern|technique|framework]` to scored findings. In keyword-only fallback mode, flag findings matching skill-related keywords ("framework", "tool", "plugin", "library", "pattern", "template", "workflow")

**Definition of Done:**

- [ ] Keyword scorer assigns non-zero scores to relevant findings and zero to irrelevant ones
- [ ] Ollama scorer calls local API with scoring prompt and parses numeric response
- [ ] Graceful fallback when Ollama is unavailable (keyword-only mode with warning)
- [ ] Combined score ranks findings by overall Cohezion relevance
- [ ] Top-N selection (configurable, default 60) after scoring
- [ ] Skill candidate flag set on findings that describe reusable tools/patterns/techniques

**Verify:**

- `research/.venv/bin/python3 -m pytest research/tests/test_scorer.py -q`

### Task 4: Vault Publisher Module

**Objective:** Transform scored findings into vault-compatible output: individual `inbox/` notes for top findings and a comprehensive `daily/` digest note.

**Dependencies:** Task 1

**Files:**

- Create: `research/publisher.py` — Vault note generation module
- Test: `research/tests/test_publisher.py` — Publisher tests

**Key Decisions / Notes:**

- **Individual inbox notes** (top 30-50 highest-scored, configurable via `max_inbox_notes` in YAML):
  ```markdown
  ---
  title: "Finding: {title}"
  date: {today}
  status: new
  triage_status: new
  tags: [research, {focus_area}, {source_type}]
  source_url: {url}
  relevance_score: {overall_score}
  skill_candidate: {true|false}
  skill_type: {tool|pattern|technique|framework|null}
  vault_target: {patterns|concepts|decisions|papers|null}
  ---

  ## Summary
  {snippet}

  ## Source
  [{title}]({url}) — via {source_type}

  ## Relevance to Cohezion
  - **{focus_area}**: Score {score}/10
  - {brief_reason}

  ## Skill Integration Path
  <!-- For skill_candidate: true findings -->
  <!-- 1. Review finding → 2. /learn to extract skill → 3. /vault to share with team -->
  <!-- skill_type helps prioritize: tools > patterns > techniques > frameworks -->

  ## Potential Integration
  <!-- Triage: How might this be integrated into Cohezion? -->
  ```
- **Daily digest note** (`daily/YYYY-MM-DD-research-digest.md`):
  ```markdown
  ---
  title: "Research Digest: {date}"
  date: {today}
  tags: [research, digest, daily]
  ---

  ## Research Digest — {date}

  **Sources scanned:** {source_count}
  **Raw findings:** {raw_count}
  **After scoring:** {scored_count}
  **Inbox notes created:** {note_count}

  ### Skill Candidates (Ready for /learn → /vault)
  | Finding | Type | Focus Area | Score | Action |
  |---------|------|------------|-------|--------|
  | [[finding-1]] | tool | app-creation | 9/10 | /learn to extract |
  ...

  ### Top Findings by Focus Area

  #### Compound Engineering
  1. [[finding-title-1]] — Score 9/10 — {one-line summary}
  ...

  #### Token Efficiency
  ...

  ### All Findings (Scored)
  | # | Title | Source | Score | Focus Area |
  |---|-------|--------|-------|------------|
  | 1 | ... | ... | 9.2 | compound-engineering |
  ...
  ```
- File naming: inbox notes use `inbox/research-YYYY-MM-DD-{slug}.md`, digest uses `daily/YYYY-MM-DD-research-digest.md`
- Deduplication: maintain a `research/seen_urls.json` index mapping source_url → note filename. Check this index (O(1)) instead of scanning vault frontmatter (O(n)). Append new entries on each run.

**Definition of Done:**

- [ ] Inbox notes follow vault frontmatter schema (tags as arrays, date format, `triage_status: new`)
- [ ] Digest note includes summary stats + per-focus-area sections + full findings table
- [ ] Digest handles 50+ findings with clear categorization and priority ordering
- [ ] File names are slugified and date-prefixed
- [ ] Dedup check prevents duplicate notes for same URL
- [ ] Wiki-links in digest point to actual inbox note filenames
- [ ] All volume thresholds configurable via YAML (`max_inbox_notes`, `max_scored`, etc.)

**Verify:**

- `research/.venv/bin/python3 -m pytest research/tests/test_publisher.py -q`

### Task 5: Multi-Tool Access Layer (CLI + MCP + Claude Code)

**Objective:** Make the pipeline accessible from any AI coding tool: standalone CLI for bash-based tools, MCP server for MCP-compatible tools, and Claude Code skill/command for Claude Code users.

**Dependencies:** Task 1, Task 2, Task 3, Task 4

**Files:**

- Create: `research/cli.py` — Standalone CLI with argparse (usable from any tool via `python research/cli.py`)
- Create: `research/mcp_server.py` — FastMCP server exposing pipeline as MCP tools (for Claude Code, OpenCode, Antigravity, etc.)
- Create: `.claude/skills/daily-research/SKILL.md` — Claude Code skill definition
- Create: `.claude/commands/research.md` — Claude Code command for `/research`
- Test: `research/tests/test_cli.py` — CLI argument parsing and output format tests

**Key Decisions / Notes:**

- **Standalone CLI** (`research/cli.py`) — Primary interface, usable from any AI tool:
  - `python research/cli.py run` — Full run (harvest + score + publish)
  - `python research/cli.py run --quick` — Quick mode: web search only, keyword scoring, no vault notes
  - `python research/cli.py run --focus compound-engineering` — Filter to one focus area
  - `python research/cli.py triage` — Review existing inbox research notes, suggest vault placement
  - `python research/cli.py status` — Show last run stats (when, how many findings, etc.)
  - Output: JSON to stdout (for programmatic use by any tool) + vault notes to disk
- **MCP server** (`research/mcp_server.py`) — FastMCP server exposing tools:
  - `research_run(mode, focus_area)` — Run pipeline, return findings as structured data
  - `research_triage()` — Return inbox research notes with suggested vault targets
  - `research_status()` — Last run metadata
  - Registers in `.mcp.json` or `mcp_servers.json` for auto-discovery by MCP-compatible tools
- **Claude Code command** (`.claude/commands/research.md`) — Calls CLI, presents summary
  - `/research` wraps `python research/cli.py run` and formats output for conversation
  - `/research --triage` wraps `python research/cli.py triage`
- **Vault integration:** Output highlights skill candidates and suggests vault directory per finding (patterns/ for reusable solutions, concepts/ for new ideas, decisions/ for architectural choices, papers/ for academic work). Triage mode helps sort inbox research notes into permanent locations with proper cross-linking.
- The command template calls the pipeline and reads the digest:
  ```bash
  research/.venv/bin/python3 research/pipeline.py [args]
  ```

**Definition of Done:**

- [ ] Standalone CLI (`research/cli.py`) works with `run`, `triage`, and `status` subcommands
- [ ] CLI outputs JSON to stdout for programmatic consumption by any AI tool
- [ ] MCP server (`research/mcp_server.py`) exposes `research_run`, `research_triage`, `research_status` tools
- [ ] MCP server config added to `mcp_servers.json` for auto-discovery
- [ ] Claude Code command file at `.claude/commands/research.md` wraps CLI with formatted output
- [ ] Claude Code skill file at `.claude/skills/daily-research/SKILL.md` with trigger conditions
- [ ] `--quick` and `--focus` flags work on CLI
- [ ] `triage` subcommand reads inbox research notes and suggests vault placement
- [ ] Output includes `vault_target` per finding (patterns/, concepts/, decisions/, papers/)

**Verify:**

- `research/.venv/bin/python3 research/cli.py --help` — CLI prints usage with subcommands
- `research/.venv/bin/python3 research/cli.py status` — Returns JSON with last run info (or "no runs yet")
- `research/.venv/bin/python3 -m pytest research/tests/test_cli.py -q` — CLI tests pass
- `cat .claude/commands/research.md` — File exists with `description:` frontmatter
- `cat .claude/skills/daily-research/SKILL.md` — File exists with `name:` and `description:` frontmatter
- `cat mcp_servers.json | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'research' in d.get('mcpServers',{})"` — MCP config registered

### Task 6: Cron Wrapper and Automation

**Objective:** Create a shell wrapper that runs the pipeline unattended, with logging and error handling suitable for cron.

**Dependencies:** Task 1, Task 2, Task 3, Task 4

**Files:**

- Create: `research/run_research.sh` — Cron-compatible wrapper script
- Create: `research/cron_example.txt` — Example crontab entry
- Test: `research/tests/test_cron_wrapper.sh` — Smoke test for wrapper

**Key Decisions / Notes:**

- Wrapper activates the venv, sets `PYTHONPATH`, runs the pipeline
- Logs to `~/.pilot/logs/research-YYYY-MM-DD.log` (or configurable via env var)
- Exit codes: 0 = success, 1 = partial failure (some sources failed), 2 = total failure
- Example crontab: `0 6 * * * /home/mike-anderson/vaults/cohezion-vault/research/run_research.sh`
- Wrapper checks Ollama availability before running; logs warning if offline
- On failure: write a failure note to `inbox/research-failure-YYYY-MM-DD.md` so the user sees it in Obsidian

**Definition of Done:**

- [ ] Shell script is executable and runs the pipeline end-to-end
- [ ] Logs output to datestamped file
- [ ] Returns meaningful exit codes (0/1/2)
- [ ] Example crontab entry documented
- [ ] Script handles missing Ollama gracefully (falls back to keyword scoring)

**Verify:**

- `bash research/run_research.sh --dry-run` — Exits 0 with dry-run output
- `cat research/cron_example.txt` — Contains valid crontab line

## Testing Strategy

- **Unit tests:** Each module (pipeline, harvester, scorer, publisher) has isolated tests with mock data. No real API calls in unit tests.
- **Integration test:** A single `test_full_pipeline.py` that runs the pipeline with a minimal config (2 queries, keyword-only scoring) against real DuckDuckGo and verifies vault notes are produced.
- **Manual verification:** Run `/research --quick` in Claude Code and verify conversation output. Run full pipeline and check `inbox/` and `daily/` for new notes.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DuckDuckGo rate-limiting | Medium | Medium | 2-5s random jitter between queries; catch `RatelimitException` from duckduckgo-search lib; cap at 30 queries per run; detect empty results as rate-limit signal; fallback to cached results |
| Ollama not running | Medium | Low | Graceful fallback to keyword-only scoring with log warning; pipeline still produces results |
| Low-quality findings (noise) | Medium | Medium | Tier-1 keyword filter removes irrelevant results; configurable score threshold (default 3/10) drops low-relevance items |
| GitHub API rate limits | Low | Low | Use `gh` CLI with authenticated token; batch API calls; cache trending results for 24h |
| Duplicate findings across runs | Medium | Low | Dedup check in publisher compares `source_url` against existing vault notes before creating |
| Pipeline too slow for cron window | Low | Medium | Configurable parallelism; `--quick` mode for faster runs; timeout per source (30s default) |

## Open Questions

- Future: Could the pipeline feed into a weekly "research brief" that summarizes trends across multiple daily runs?

### Deferred Ideas

- Advanced MCP server features (streaming results, progress callbacks, subscription to new findings)
- Semantic dedup using Ollama embeddings (compare new findings against existing vault)
- Auto-linking findings to relevant existing vault concepts/patterns
- Full RSS/Atom feed parser for blogs (current approach checks index pages; full RSS would be more reliable)
- Research impact tracking (which findings led to actual Cohezion improvements)
