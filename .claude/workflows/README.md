# Workflow collaborators

Reusable multi-agent [Workflow](https://docs.claude.com/en/docs/claude-code) scripts that act as on-demand
"code collaborators." Each fans work out across subagents (review in parallel, write tests/docs per module)
and is driven from a Claude Code session — they are **not** GitHub Actions and do not run on their own.

## Available workflows

| Name | What it does | Default target | Optional `args` |
|------|--------------|----------------|-----------------|
| `review` | Reviews the current branch's diff across 5 dimensions (correctness, security, performance, simplification, tests), then **adversarially verifies** each finding so only real issues survive. Returns a Markdown report. | diff vs `origin/main` | a base ref string, e.g. `"HEAD~3"` |
| `cover` | Finds under-tested `src/cohezion` modules and writes focused, offline pytest files (one per module, in isolated worktrees). | highest-value gaps repo-wide | a subpackage, e.g. `"compound"` |
| `docs` | Audits public modules for missing/weak docstrings, adds Google-style docstrings **in place** (docstrings only — no behavior change), and returns a reference page. | user-facing surfaces | a subpackage, e.g. `"environments"` |
| `compound` | **Meta-workflow.** Runs `review`, finds the most-affected subpackage from the findings, then runs `cover` + `docs` on it, and finishes with a retrospection that proposes improvements to the collaborators themselves. The compound-engineering loop in one shot. | diff vs `origin/main` | a base ref string |

## How to run

Ask in a session, e.g. *"run the `review` workflow"* or *"run `cover` scoped to physics"*. Claude invokes the
Workflow tool by name:

```
Workflow({ name: "review" })                 // diff vs origin/main
Workflow({ name: "review", args: "HEAD~5" }) // diff vs a different base
Workflow({ name: "cover",  args: "compound" })
Workflow({ name: "docs",   args: "environments" })
```

Workflows run in the background; progress is visible via `/workflows`. The Workflow tool requires explicit
opt-in (these consume tokens — `cover`/`docs` can spawn several agents that edit files in isolated worktrees,
so review the resulting diffs before merging).

## Design notes

- **`review`** uses `pipeline()` so each dimension's findings are verified the moment that dimension finishes
  (no barrier). Verification defaults to *refute* — a finding survives only if a verifier confirms it against
  the real code. It uses the `code-reviewer` agent type for the review pass.
- **`cover`** and **`docs`** use `isolation: "worktree"` because their agents edit files in parallel; isolated
  worktrees prevent collisions. They cap work at 6 modules/run to stay bounded, and `cover` deliberately targets
  modules testable **offline** (no Ollama/lemonade/SurrealDB/network).
- All three accept an optional `args` string to scope them; with no args they pick the highest-value targets.
- Scripts are plain JS executed in the Workflow runtime's async context (top-level `await`/`return` are valid).
  To tweak one, edit the file and re-run by name.
