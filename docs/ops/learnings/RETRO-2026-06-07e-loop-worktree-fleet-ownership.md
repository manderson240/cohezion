---
date: 2026-06-07
kind: retro
thread: [loops, worktree, local-inference, ownership, sandbox]
prompted_by: retro-watch ([retro:due], 2 tasks — items 97/110) + user directives ("safe worktree", "local silicon", "owned by agent specialist", "retros + cherry-pick to main are part of the loop")
status: captured
---

# Retro — resuming the build loop into a safe worktree, on local silicon, owned by specialists

A session that started as a `claude doctor` fix and turned into resuming + re-architecting the
IMPROVEMENT_BACKLOG build loop. Captures operational findings that cost time and should not be
re-discovered.

## What worked

- **Two clean deterministic ticks** (items 97 boolean-flag-args, 110 mutable-default-args): TDD
  with discriminating tests that kill the real traps (`1`-is-not-`True` via `isinstance(v, bool)`;
  `()`-vs-`[]` tuple-not-list), each wired into a REAL non-test consumer
  (`problem_discovery.default_templates`), surgical 4-file commits. 38 sibling tests green.
- **Delegating inference-bearing work to a specialist subagent** is context-efficient: the work
  (and its token cost) lives in the subagent; only the result returns to the main loop.

## Findings to NOT re-discover

1. **`EnterWorktree` defaults to `.claude/worktrees/`, which is READ-ONLY in this session's bwrap
   sandbox** → it fails with `bwrap: Can't create file at <wt>/.gitconfig: Read-only file system`,
   even with `dangerouslyDisableSandbox` (the whole `.claude/` subtree is masked). FIX: put loop
   worktrees under `.worktrees/` at the repo root (the project's existing convention — nemotron/
   kaggle worktrees live there too). The broken `.claude/worktrees/` dir also cannot be `rm`'d from
   inside the sandbox; needs an out-of-sandbox cleanup.
2. **`.mcp.json` "invalid JSON" was a `/dev/null` bind-mount mask, not bad content.** The bash
   sandbox masks `.mcp.json` with `/dev/null` every launch; `claude doctor` reads the REAL fs. When
   a real 0-byte file existed underneath, doctor parsed it as invalid JSON. Deleting the real file
   (config lives in `.claude/mcp.json`, 14 servers) fixed doctor; the mask is harmless. The mount
   only exists in Claude's namespace — `sudo umount` in the user's login shell reports "not mounted".
3. **lemonade `:13305` is the one router for the whole fleet.** `llamacpp_backend` ∈
   {vulkan,rocm,metal,cpu} on `POST /api/v1/load` selects the DEVICE; NPU uses the `flm` recipe;
   chat/embeddings auto-load on demand. 28-model catalog across NPU(XDNA2)+iGPU(gfx1151)+CPU. The
   dedicated `:13307`/`:13309` per-port servers are redundant — do NOT start them (OOM, rule K1).

## Honesty calibration (load-bearing)

- The **deterministic AST-audit arm uses ZERO inference by design** — "a number is a smell, not an
  LLM verdict." The per-tick code-authoring is the cloud agent, not local silicon. Do NOT claim the
  local fleet authored the audits. Local silicon is the substrate for the INFERENCE-bearing arms
  (research/distillation, quality gates, embeddings, multi-model review) only.

## Doctrine changes made this session

- Loop ownership = the specialist team (platform-coordinator coordinates; compound-engineering /
  autoresearch / swarm-orchestration own arms by type); per-tick inference-bearing work delegated.
- Local-silicon-first inference for all inference-bearing arms, routed via `:13305`.
- **NEW (this steer): retrospectives + a cherry-pick→branch-off-origin/main→PR→main landing flow
  are standing parts of each loop cycle** (see IMPROVEMENT_BACKLOG Notes).

## Next

- Land the clean loop commits (97, 110, doctrine) on main via a fresh branch off `origin/main`.
- Consider refining the `multi-agent-isolated-worktree-pattern` skill with finding #1.
