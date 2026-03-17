# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Luma AMD Speedrun: Phase 12 — Status & Next Steps

## Context

Phase 12 explored hiprtc (HIP Runtime Compilation) as a way to bypass Python dispatch
overhead (~130us). **hiprtc is BLOCKED on Popcorn CLI** via static source scanning
(rejects `hipModuleLaunchKernel`, `hipModuleLoadData`, `libamdhip64.so` strings).

Pivoted to combining best discoveries from Phase 11 + Phase 12 into a single
optimized MLA submission.

## Completed Work

### Infrastructure (Tasks ...

### Prompt 2

Base directory for this skill: /home/mike-anderson/.claude/skills/popcorn-cli-amd-kernel-submission

# Popcorn CLI AMD Kernel Submission Workflow

## Submission Commands

```bash
CLI=~/.local/bin/popcorn-cli
KERNELS=/path/to/kernels/dir

# 1. Test (correctness check — do this first)
$CLI submit --no-tui --mode test --gpu MI355X --leaderboard <name> $KERNELS/<kernel>/submission.py

# 2. Benchmark (timing, no leaderboard impact)
$CLI submit --no-tui --mode benchmark --gpu MI355X --leaderboard <...

### Prompt 3

Base directory for this skill: /home/mike-anderson/.claude/skills/competitive-kernel-optimization-ceiling

# Competitive Kernel Optimization: Beyond Parameter Tuning

## Problem

After exhausting all tunable parameters in a library (e.g., aiter's `fused_moe`), ranking
stays in the lower half of the leaderboard. The reference implementation is already
well-optimized; parameter sweeps either have no effect, cause correctness failures, or
degrade performance.

## Context: When to Use This

- All...

### Prompt 4

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

### Prompt 5

We need to focus on custom kernels or we will never win.

### Prompt 6

[Request interrupted by user for tool use]

### Prompt 7

The runner itself holds the keys to success

### Prompt 8

adapt our strategy based on the tools available

### Prompt 9

you can overcome any blocker

### Prompt 10

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user initially asked to implement a Phase 12 plan for the Luma AMD Speedrun competition, which involved verifying completed work and submitting the MLA kernel to the MI355X runner. After successful submission (74.3 µs ranked geomean, new best), the user pivoted to a strategic direction change: **...

### Prompt 11

[Request interrupted by user for tool use]

### Prompt 12

If we understand and the architecture and the runner tools can't we create the optimized kernels locally until we're fairly confident we have a winning solution before we submit it?

### Prompt 13

[Request interrupted by user for tool use]

### Prompt 14

Leverage our unique silicon as well

### Prompt 15

[Request interrupted by user for tool use]

