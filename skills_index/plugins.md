---
title: "Plugin Skills Index"
date: 2026-03-07
tags: [skills-index, plugins, marketplace, superpowers]
---

# Plugin Skills Index

Skills installed via marketplace, custom plugins, and the Pilot global commands.

## Development Workflow

| Skill | Trigger | Source |
|-------|---------|--------|
| `spec` / `spec-plan` / `spec-implement` / `spec-verify` | `/spec` | Pilot (global) |
| `sync` | "sync rules and skills" | Pilot |
| `learn` | "extract knowledge" | Pilot |
| `vault` | "share skills with team" | Pilot |
| `simplify` | "review changed code" | Pilot |
| `test-fix` | "fix failing tests" | Plugin |
| `fix-packages` | "fix missing __init__.py" | Plugin |
| `security-review` | "security review" | Plugin |
| `retrospect` | "dev retrospective" | Plugin |
| `new-agent` | "scaffold new agent" | Plugin |

## Superpowers (Meta-Skills)

| Skill | Auto-Trigger |
|-------|-------------|
| `brainstorming` | Before creative tasks |
| `systematic-debugging` | Bug/test failure |
| `test-driven-development` | Feature implementation |
| `verification-before-completion` | Before claiming done |
| `writing-plans` / `executing-plans` | Spec workflows |
| `subagent-driven-development` | Implementation plans |
| `dispatching-parallel-agents` | 2+ independent tasks |
| `using-git-worktrees` | Feature isolation |
| `writing-skills` | Skill authoring |

## Git & PR
| Skill | Trigger |
|-------|---------|
| `commit-commands:commit` | "commit" |
| `commit-commands:commit-push-pr` | "commit, push, PR" |
| `commit-commands:clean_gone` | "clean merged branches" |
| `pr-review-toolkit:review-pr` | "review this PR" |

## Content Creation (Canonical: `document-skills:*`)
| Skill | Trigger |
|-------|---------|
| `pdf` | "create a PDF" |
| `docx` | "create a Word doc" |
| `pptx` | "create a PowerPoint" |
| `xlsx` | "create a spreadsheet" |
| `frontend-design` | "create frontend UI" |
| `canvas-design` | "create visual art" |
| `mcp-builder` | "create MCP server" |
| `web-artifacts-builder` | "create web artifacts" |
| `playground:playground` | "interactive playground" |

**Note:** `claude-api:*` and `example-skills:*` are duplicates — see [[2026-03-07-skill-pruning-consolidation-plan]].

## Other Namespaces
| Namespace | Skills | Status |
|-----------|--------|--------|
| `hookify:*` | hookify, configure, list | Active |
| `ralph-loop:*` | ralph-loop, cancel-ralph, help | Evaluate usage |
| `sentry:*` | seer, sentry-sdk-setup, sentry-workflow | Dormant |
| `huggingface-skills:*` | 12 skills | Active for ML work |
| `plugin-dev:*` | 7 skills | Plugin authoring toolkit |
| `claude-md-management:*` | revise-claude-md, claude-md-improver | Meta-improvement |
| `feature-dev:feature-dev` | Guided feature dev | Assess overlap with `/spec` |

## Related
- [[skill-taxonomy-7-layer-architecture]]
- [[skill-routing-decision-tree]]
