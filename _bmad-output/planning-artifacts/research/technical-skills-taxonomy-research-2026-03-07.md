---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
workflowType: 'research'
lastStep: 4
research_type: 'technical'
research_topic: 'Installed Skills Taxonomy & Natural Language Routing'
research_goals: 'Map all 150+ skills/commands/tools across 7 source layers; define routing heuristics; identify pruning candidates'
user_name: 'Mike-anderson'
date: '2026-03-07'
web_research_enabled: false
source_verification: true
---

# Research Report: Installed Skills Taxonomy & Natural Language Routing

**Date:** 2026-03-07
**Author:** Mike-anderson
**Research Type:** technical

---

## Research Overview

Cohezion has accumulated **150+ skills, commands, agents, and MCP tools** from 7 distinct sources. This research produces a complete taxonomy mapping how they relate, which to invoke for a given natural language request, and where redundancy can be pruned.

---

## 1. Skill Sources (7 Layers)

| # | Source | Location | Count | Load Mechanism |
|---|--------|----------|-------|----------------|
| 1 | **BMAD Commands** (project) | `.claude/commands/bmad-*.md` | 90 | Slash commands that load workflow `.md` from `_bmad/` |
| 2 | **Project Commands** (custom) | `.claude/commands/{audit,async-audit,bash-report,deploy,heal,wake,...}.md` | 10 | Slash commands with direct execution |
| 3 | **Project Skills** | `.claude/skills/update-tools/` | 1 | Skill invocation |
| 4 | **Global Commands** (Pilot) | `~/.claude/commands/{spec,spec-plan,spec-implement,spec-verify,sync,learn,vault}.md` | 7 | Slash commands with structured workflows |
| 5 | **Global Rules** (Pilot) | `~/.claude/rules/*.md` | ~15 | Auto-loaded at session start (enforcement, not invocable) |
| 6 | **Plugin Skills** (marketplace) | Loaded via marketplace/custom install | ~55 | `Skill()` tool call |
| 7 | **MCP Tools** | `.mcp.json` + `~/.claude/mcp.json` | ~80 | `ToolSearch` then direct tool call |

**Total installed surface area:** ~258 entries (with ~60 redundant/duplicate).
**Effective unique capabilities:** ~198.

---

## 2. BMAD Module Taxonomy (~90 commands)

BMAD is organized into **5 modules**, each with a lifecycle phase focus. All commands live in `.claude/commands/bmad-*.md` and delegate to workflow files in `_bmad/`.

### 2.1 BMM — Business Model Module (Product Lifecycle)

**Prefix:** `bmad-bmm-*` | **Agent personas:** architect, dev, qa, sm, pm, analyst, tech-writer, ux-designer, quick-flow-solo-dev

| Phase | Commands | Natural Language Triggers |
|-------|----------|--------------------------|
| **Analysis** | `technical-research`, `domain-research`, `market-research` | "research X", "investigate Y", "what are the options for Z" |
| **Planning** | `create-prd`, `edit-prd`, `validate-prd`, `create-product-brief`, `create-architecture`, `create-ux-design` | "create a PRD", "design the architecture", "plan the UX" |
| **Solutioning** | `create-epics-and-stories`, `create-story`, `sprint-planning`, `sprint-status` | "break this into stories", "plan the sprint", "check sprint status" |
| **Implementation** | `dev-story`, `quick-dev`, `quick-spec`, `qa-generate-e2e-tests`, `code-review` | "implement story X", "quick fix", "review this code" |
| **Cross-cutting** | `check-implementation-readiness`, `correct-course`, `retrospective`, `document-project`, `generate-project-context` | "are we ready to build?", "course correct", "run retro" |

**Lifecycle flow:**
```
research → product-brief → PRD → architecture → UX-design
  → epics-and-stories → sprint-planning → dev-story → code-review
  → sprint-status → retrospective
```

### 2.2 GDS — Game Development Studio

**Prefix:** `bmad-gds-*` | **Agent personas:** game-architect, game-designer, game-dev, game-qa, game-scrum-master, game-solo-dev, tech-writer

| Phase | Commands | Natural Language Triggers |
|-------|----------|--------------------------|
| **Preproduction** | `create-game-brief`, `game-brief`, `brainstorm-game` | "brainstorm a game", "create game brief" |
| **Design** | `gdd`, `create-gdd`, `narrative` | "create game design doc", "write narrative" |
| **Technical** | `game-architecture`, `quick-spec`, `quick-dev` | "design game architecture", "quick game spec" |
| **Production** | `dev-story`, `create-story`, `sprint-planning`, `sprint-status`, `code-review`, `correct-course`, `retrospective` | "implement game story", "game sprint status" |
| **Testing** | `gametest-framework`, `gametest-test-design`, `gametest-automate`, `gametest-test-review`, `gametest-playtest-plan`, `gametest-performance` | "create test framework", "playtest plan" |

**Lifecycle flow:**
```
brainstorm-game → game-brief → GDD → narrative → game-architecture
  → sprint-planning → create-story → dev-story → code-review
  → gametest-* → sprint-status → retrospective
```

### 2.3 CIS — Creative Innovation Studio

**Prefix:** `bmad-cis-*` | **Agent personas:** brainstorming-coach, creative-problem-solver, design-thinking-coach, innovation-strategist, presentation-master, storyteller

| Commands | Natural Language Triggers |
|----------|--------------------------|
| `brainstorming` (+ top-level `bmad-brainstorming`) | "let's brainstorm", "ideation session" |
| `design-thinking` | "design thinking workshop", "empathy mapping" |
| `innovation-strategy` | "disruption analysis", "innovation opportunities" |
| `problem-solving` | "systematic problem solving", "root cause analysis" |
| `storytelling` | "craft a narrative", "tell a story about X" |

### 2.4 TEA — Test Engineering Academy

**Prefix:** `bmad-tea-*` | **Agent persona:** tea

| Commands | Natural Language Triggers |
|----------|--------------------------|
| `testarch-test-design` | "design test plan", "test strategy" |
| `testarch-automate` | "expand test automation", "automate tests" |
| `testarch-atdd` | "acceptance test driven", "write acceptance tests" |
| `testarch-test-review` | "review test quality" |
| `testarch-framework` | "setup test framework", "init Playwright/Cypress" |
| `testarch-ci` | "setup CI pipeline", "quality gates" |
| `testarch-nfr` | "assess NFRs", "performance/security assessment" |
| `testarch-trace` | "traceability matrix", "quality gate decision" |
| `teach-me-testing` | "teach me testing", "learn testing" |

### 2.5 BMB — BMAD Module Builder (Meta)

**Prefix:** `bmad-bmb-*` | **Agent personas:** agent-builder, module-builder, workflow-builder

| Commands | Natural Language Triggers |
|----------|--------------------------|
| `create-agent`, `edit-agent`, `validate-agent` | "create a BMAD agent", "validate agent" |
| `create-workflow`, `edit-workflow`, `validate-workflow`, `rework-workflow` | "create workflow", "validate workflow" |
| `create-module`, `edit-module`, `validate-module`, `create-module-brief` | "create BMAD module", "validate module" |
| `validate-max-parallel-workflow` | "validate workflow in parallel mode" |

**Meta flow:**
```
create-module-brief → create-module
create-agent / create-workflow (independently)
validate-agent / validate-workflow / validate-module (quality gates)
edit-agent / edit-workflow / edit-module (modifications)
rework-workflow (V6 compliance upgrade)
```

### 2.6 BMAD Cross-Cutting Utilities

| Command | Natural Language Triggers |
|---------|--------------------------|
| `bmad-help` | "what should I do next", "help me", "what now" |
| `bmad-party-mode` | "party mode", "group discussion with all agents" |
| `bmad-index-docs` | "index the docs", "generate doc index" |
| `bmad-shard-doc` | "split this document", "shard large markdown" |
| `bmad-editorial-review-prose` | "review for prose quality", "copy edit" |
| `bmad-editorial-review-structure` | "review document structure", "structural edit" |
| `bmad-review-adversarial-general` | "cynical review", "adversarial review" |
| `bmad-review-edge-case-hunter` | "find edge cases", "boundary condition review" |

### 2.7 BMAD Agent Personas (~20 agents)

These are **role-based personas**, not workflows. They set the agent's personality and expertise domain for interactive sessions.

| Domain | Agents |
|--------|--------|
| BMM | `architect`, `dev`, `qa`, `sm`, `pm`, `analyst`, `tech-writer`, `ux-designer`, `quick-flow-solo-dev` |
| GDS | `game-architect`, `game-designer`, `game-dev`, `game-qa`, `game-scrum-master`, `game-solo-dev`, `tech-writer` |
| CIS | `brainstorming-coach`, `creative-problem-solver`, `design-thinking-coach`, `innovation-strategist`, `presentation-master`, `storyteller` |
| TEA | `tea` |
| BMB | `agent-builder`, `module-builder`, `workflow-builder` |
| Core | `bmad-master` |

---

## 3. Plugin Skills (Marketplace & Custom)

### 3.1 Development Workflow

| Skill | Trigger | Source |
|-------|---------|--------|
| `spec` / `spec-plan` / `spec-implement` / `spec-verify` | "spec-driven dev", `/spec` | Pilot (global) |
| `sync` | "sync rules and skills" | Pilot |
| `learn` | "extract knowledge", triggered at 90% context | Pilot |
| `vault` | "share skills with team" | Pilot |
| `simplify` | "review changed code for reuse/quality" | Pilot |
| `test-fix` | "fix failing tests" | Plugin |
| `fix-packages` | "fix missing __init__.py" | Plugin |
| `async-audit` | "audit asyncio patterns" | Project command |
| `security-review` | "security vulnerability review" | Plugin |
| `retrospect` | "run dev retrospective" | Plugin |
| `new-agent` | "scaffold new agent file" | Plugin |

### 3.2 Superpowers (Meta-Skills)

These wrap around other skills as behavior enhancers:

| Skill | When Triggered |
|-------|---------------|
| `superpowers:brainstorming` | Before any creative task |
| `superpowers:systematic-debugging` | Any bug or test failure |
| `superpowers:test-driven-development` | Implementing any feature |
| `superpowers:writing-plans` | Have a spec, need a plan |
| `superpowers:executing-plans` | Have a plan, need execution |
| `superpowers:subagent-driven-development` | Executing implementation plans |
| `superpowers:dispatching-parallel-agents` | 2+ independent tasks |
| `superpowers:verification-before-completion` | About to claim done |
| `superpowers:requesting-code-review` / `receiving-code-review` | PR review |
| `superpowers:finishing-a-development-branch` | Branch done, merge time |
| `superpowers:using-git-worktrees` | Feature work isolation |
| `superpowers:writing-skills` | Creating/editing skills |
| `superpowers:using-superpowers` | Starting any conversation |

### 3.3 Git & PR Operations

| Skill | Trigger |
|-------|---------|
| `commit-commands:commit` | "commit" |
| `commit-commands:commit-push-pr` | "commit, push, and open PR" |
| `commit-commands:clean_gone` | "clean up merged branches" |
| `pr-review-toolkit:review-pr` | "comprehensive PR review" |

### 3.4 Cohezion-Specific

| Skill | Trigger |
|-------|---------|
| `heal` | "self-healing protocol" |
| `audit` | "deep audit of performance/HIHO" |
| `deploy` | "deploy to Cloud Run" |
| `wake` | "wake up the system" |
| `scout` | "daily model research" |

### 3.5 Hookify (Behavior Guards)

| Skill | Trigger |
|-------|---------|
| `hookify:hookify` | "create hooks to prevent X" |
| `hookify:configure` | "enable/disable hookify rules" |
| `hookify:list` | "list hookify rules" |

### 3.6 Content Creation

| Skill | Trigger |
|-------|---------|
| `pdf`, `docx`, `pptx`, `xlsx` | "create a PDF/Word/PowerPoint/spreadsheet" |
| `frontend-design` | "create frontend UI" |
| `canvas-design` | "create visual art" |
| `algorithmic-art` | "algorithmic art with p5.js" |
| `mcp-builder` | "create an MCP server" |
| `web-artifacts-builder` | "create web artifacts" |
| `playground:playground` | "create interactive HTML playground" |

**REDUNDANCY NOTE:** These skills exist in THREE plugin namespaces (`claude-api:*`, `document-skills:*`, `example-skills:*`) with identical functionality. See Section 6 for consolidation recommendation.

### 3.7 Other Plugin Namespaces

| Namespace | Skills | Status |
|-----------|--------|--------|
| `ralph-loop:*` (3 skills) | Ralph Loop plugin | Evaluate usage; remove if unused |
| `sentry:*` (3 skills) | Sentry integration | Keep dormant unless Sentry configured |
| `huggingface-skills:*` (12 skills) | HuggingFace ecosystem | Keep only if doing ML model work |
| `feature-dev:feature-dev` | Guided feature dev | Assess overlap with `/spec` |
| `claude-md-management:*` (2 skills) | CLAUDE.md maintenance | Useful for meta-improvement |
| `plugin-dev:*` (7 skills) | Plugin creation toolkit | Keep for authoring new plugins |
| `agent-sdk-dev:new-sdk-app` | Agent SDK scaffolding | Keep for SDK work |

---

## 4. MCP Tool Servers (~80 tools)

| Server | Purpose | Key Tools |
|--------|---------|-----------|
| `cohezion-bmad` | BMAD operations | `bmad_help`, `bmad_status`, `bmad_list_agents`, `bmad_list_workflows`, `bmad_party_mode`, `bmad_index_docs`, create/review tools |
| `cohezion-knowledge` | Skill knowledge base | `list_skills`, `get_skill`, `search_knowledge` |
| `cohezion-research` | Research sources | `search_arxiv`, `get_hf_trending`, `list_research_channels` |
| `cohezion-surreal` | SurrealDB graph | `store_node`, `query_nodes`, `store_learning`, `query_learnings`, `search_similar`, `sync_key_learnings` |
| `cohezion-swarm` | Multi-agent debate | `run_debate`, `get_perspectives`, `get_swarm_metrics` |
| `cohezion-skills` | Skill registry | `list_all_skills`, `search_skills`, `invoke_skill`, `register_skill` |
| `context7` | Library docs | `resolve-library-id`, `query-docs` |
| `github` | GitHub API | 40+ tools for PRs, issues, repos, branches |
| `overture-mcp` | Plan orchestration | `create_new_plan`, `submit_plan`, `update_node_status`, etc. |
| `playwright` | Browser automation | `browser_navigate`, `browser_click`, `browser_snapshot`, etc. |

---

## 5. Routing Strategy: Natural Language to Skill

### 5.1 Decision Tree (Priority Order)

```
User says something →
  1. EXACT MATCH: Does it match a slash command? → Execute directly
  2. LIFECYCLE PHASE: What phase of work is this?
     ├─ Research/Analysis → BMM research or CIS brainstorming
     ├─ Planning/Design → BMM PRD/Architecture or GDS Brief/GDD
     ├─ Implementation → BMM dev-story/quick-dev or /spec workflow
     ├─ Testing → TEA testarch-* or test-fix
     ├─ Review → bmad-review-* or code-review
     └─ Maintenance → retrospect, correct-course, deploy, heal
  3. DOMAIN: Is this game dev? → GDS variant. General product? → BMM variant.
  4. META: Is this about BMAD itself? → BMB module
  5. CREATIVE: Is this ideation/innovation? → CIS module
  6. TOOL NEED: Does it need external data?
     ├─ Library docs → context7
     ├─ Research papers → cohezion-research
     ├─ GitHub code → github MCP
     ├─ Knowledge graph → cohezion-surreal
     └─ Multi-perspective → cohezion-swarm
```

### 5.2 Keyword Routing Map

| Keywords in Request | Primary Skill | Fallback |
|---------------------|---------------|----------|
| "research", "investigate", "explore options" | `bmad-bmm-technical-research` | `bmad-bmm-domain-research` |
| "PRD", "requirements", "product spec" | `bmad-bmm-create-prd` | `bmad-bmm-edit-prd` |
| "architecture", "system design" | `bmad-bmm-create-architecture` | `bmad-gds-game-architecture` |
| "story", "epic", "user story" | `bmad-bmm-create-story` | `bmad-bmm-create-epics-and-stories` |
| "sprint", "planning" | `bmad-bmm-sprint-planning` | `bmad-bmm-sprint-status` |
| "implement", "build", "code this" | `bmad-bmm-dev-story` | `bmad-bmm-quick-dev` |
| "test", "testing", "QA" | `bmad-tea-testarch-test-design` | `test-fix` |
| "review", "code review" | `bmad-bmm-code-review` | `pr-review-toolkit:review-pr` |
| "brainstorm", "ideate" | `bmad-brainstorming` | `bmad-cis-brainstorming` |
| "game", "gameplay" | Route to `bmad-gds-*` variant | — |
| "deploy", "ship" | `deploy` | — |
| "fix tests", "failing tests" | `test-fix` | — |
| "commit", "push", "PR" | `commit-commands:commit` | `commit-commands:commit-push-pr` |
| "spec", "structured dev" | `/spec` | — |
| "what now", "help", "next step" | `bmad-help` | — |
| "create PDF/doc/pptx" | `document-skills:pdf` (etc.) | — |
| "security review" | `security-review` | — |
| "self-healing" | `heal` | — |

### 5.3 Overlap Resolution Matrix

| Ambiguity | Resolution Rule |
|-----------|-----------------|
| `bmad-bmm-code-review` vs `bmad-gds-code-review` vs `pr-review-toolkit:review-pr` | BMM for product code, GDS for game code, `pr-review-toolkit` for PR-specific review with GitHub integration |
| `bmad-bmm-quick-dev` vs `bmad-gds-quick-dev` | Domain context: game project → GDS, otherwise → BMM |
| `bmad-bmm-sprint-*` vs `bmad-gds-sprint-*` | Domain context: game → GDS, otherwise → BMM |
| `bmad-brainstorming` vs `bmad-cis-brainstorming` vs `superpowers:brainstorming` | `superpowers` is meta-prompt enhancer; `bmad-brainstorming` is interactive workflow; `bmad-cis-brainstorming` is lighter MCP variant |
| `bmad-bmm-retrospective` vs `bmad-gds-retrospective` vs `retrospect` | `retrospect` is dev-focused (flows into core files); BMAD variants are product/game lifecycle |
| `/spec` vs `bmad-bmm-quick-spec` vs `bmad-gds-quick-spec` | `/spec` is full structured TDD workflow; `quick-spec` is lightweight for small changes |
| `bmad-bmm-create-story` vs `bmad-gds-create-story` | Domain context |
| `bmad-gds-create-game-brief` vs `bmad-gds-game-brief` | Two paths to same output — keep command version, MCP is duplicate |
| `bmad-gds-gdd` vs `bmad-gds-create-gdd` | GDD creation via two paths — keep `create-gdd` (collaborative) |
| `code-review:code-review` vs `pr-review-toolkit:review-pr` | `pr-review-toolkit` is more comprehensive — prefer it for PR reviews |
| `feature-dev:feature-dev` vs `/spec` | `/spec` is the established workflow; `feature-dev` may overlap |

### 5.4 Superpowers Integration Pattern

Superpowers are **meta-skills** that wrap around other skills automatically:
- `brainstorming` runs before creative BMAD/CIS skills
- `systematic-debugging` runs before `test-fix`
- `test-driven-development` runs during `dev-story` / `spec-implement`
- `verification-before-completion` runs after any implementation

They do NOT replace the domain skill — they enhance it.

---

## 6. Pruning Recommendations

### 6.1 Redundant / Consolidation Candidates

| Skill(s) | Issue | Recommendation |
|-----------|-------|----------------|
| `claude-api:*` + `document-skills:*` + `example-skills:*` | ~17 skills x3 = 51 entries for ~17 actual capabilities | **Keep `document-skills:*` only.** Remove `claude-api:*` and `example-skills:*` |
| `bmad-gds-create-game-brief` + `bmad-gds-game-brief` | Two skills for same thing | Keep command version, remove MCP duplicate |
| `bmad-gds-gdd` + `bmad-gds-create-gdd` | GDD creation via two paths | Keep `create-gdd`, deprecate `gdd` |
| `bmad-gds-code-review` | Dormant unless building games | Disable unless game project active |
| `bmad-gds-retrospective` | Covered by `retrospect` + `bmad-bmm-retrospective` | Remove GDS variant |
| `code-review:code-review` | Subset of `pr-review-toolkit:review-pr` | Remove (pr-review-toolkit is more comprehensive) |

### 6.2 Low-Value / Dormant Candidates

| Skill | Reason | Recommendation |
|-------|--------|----------------|
| `bmad-bmb-validate-max-parallel-workflow` | Extremely niche | Keep only if actively building BMAD modules |
| `bmad-gds-gametest-*` (6 skills) | Full game testing suite | Disable unless game project active |
| `bmad-agent-gds-*` (7 agents) | Game-specific agent personas | Disable unless game project |
| `hookify:writing-rules` | Meta-skill about writing hookify rules | Rarely needed; `hookify:hookify` covers creation |
| `ralph-loop:*` (3 skills) | Unclear if used | Evaluate usage; remove if unused |
| `sentry:*` (3 skills) | Only relevant if using Sentry | Keep dormant unless configured |
| `huggingface-skills:*` (12 skills) | Heavy, niche | Keep only if doing ML model work |

### 6.3 Token Cost Analysis

Biggest token sinks from skill/command loading:
1. **Triple-duplicate plugins** (~17 skills x3 = 51 entries for ~17 capabilities): **~34 redundant entries**
2. **BMAD commands** (~90): Each is tiny (3-6 lines), but they all appear in skill listings
3. **GDS module** (~20 commands + 7 agents): Full game dev pipeline that's dormant

**Estimated savings from pruning:** Remove ~60 redundant/dormant entries, reducing skill listing noise by ~40%.

---

## 7. Key Relationships Summary

### Source Layer Interactions

```
Global Rules (Layer 5) ─── enforce behavior across ALL other layers
                           │
Plugin Superpowers (Layer 6) ─── meta-enhance skills from Layers 1-4
                           │
BMAD Commands (Layer 1) ───┤─── primary workflow skills
Project Commands (Layer 2) ─┤─── project-specific shortcuts
Project Skills (Layer 3) ───┤─── custom skill modules
Global Commands (Layer 4) ──┤─── structured dev workflows (/spec)
                           │
MCP Tools (Layer 7) ─── external data access for all above
```

### Compound Engineering Loop Integration

```
Natural Language Request
  → Routing Decision Tree (this document)
    → Selected Skill executes
      → CompoundExecutor records metrics
        → RetrospectionEngine extracts learnings
          → SkillRefiner updates skill definition
            → Loop continues with improved routing
```

---

## 8. Verification Checklist

- [x] All 7 source layers documented with counts
- [x] BMAD 5-module taxonomy complete (BMM, GDS, CIS, TEA, BMB)
- [x] Natural language triggers mapped per skill
- [x] Lifecycle flows documented (BMM, GDS, BMB)
- [x] Routing decision tree defined (6-step priority)
- [x] Keyword-to-skill mapping (17 entries)
- [x] Overlap resolution matrix (11 ambiguities)
- [x] Pruning recommendations with rationale
- [x] Token cost analysis
- [x] CLAUDE.md quick reference section added (53 lines)

---

*Generated by BMAD Technical Research Workflow — 2026-03-07*
