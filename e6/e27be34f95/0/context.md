# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Luma AMD Speedrun: Phase 2 — VLIW-Informed Custom Kernel Approaches

## Context

**Phase 1 (parameter tuning) is complete.** All aiter API parameters have been exhausted:
- `doweight_stage1=True`: correctness failure (SiLU nonlinearity)
- `block_size_M=64`: GPU memory fault on benchmark shapes
- `dispatch_policy=1`: 20-79% slower
- `OPUS sorting`: no effect on MXFP4 variant
- `fast_mode=True` (MLA): 17-21% slower
- `num_kv_splits` sweep (MLA): all tested value...

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

Base directory for this skill: /home/mike-anderson/.claude/skills/aiter-kernel-parameter-semantics

# aiter Kernel Parameter Semantics (AMD MI355X)

## Problem

aiter's `fused_moe` and `mla_decode_fwd` have parameters that sound like performance flags
but actually change computation or have counter-intuitive effects on MI355X.

## fused_moe: doweight_stage1

### What it does

`doweight_stage1=True` moves the `topk_weights` multiplication from **stage 2** (after SiLU
activation) to **stage 1**...

### Prompt 4

Base directory for this skill: /home/mike-anderson/.claude/skills/aiter-mxfp4-api-limitations

# aiter MXFP4 API Limitations (AMD MI355X)

## Overview

MXFP4 ("Microscaling FP4") packs **2 fp4 values per uint8 byte** (`torch.float4_e2m1fn_x2`),
with an E8M0 block-32 scale factor. This packing creates invisible API contract mismatches
across aiter's kernels. Discovered during Luma AMD Speedrun competition (March 2026, MI355X).

---

## Limitation 1: `gemm_afp4wfp4` rejects PyTorch native fp4 d...

### Prompt 5

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user requested implementation of a 6-task plan titled "Luma AMD Speedrun: Phase 2 — VLIW-Informed Custom Kernel Approaches." The plan targeted optimizing three GPU kernels (GEMM, MoE, MLA) for the Luma AMD Speedrun competition on MI355X hardware. Phase 1 (parameter tuning) was complete with all a...

### Prompt 6

Remember we should be using helios to create our custom triton kernels locally and the resources available in the runner, especially Origami.

### Prompt 7

Base directory for this skill: /home/mike-anderson/.claude/skills/helion-triton-code-generation

# Helion → Triton Code Generation Workflow

## Problem

Writing Triton MXFP4 kernels for AMD gfx950 requires understanding correct tile shapes,
scale layouts, and hardware constraints — none of which are documented. Helion (a PyTorch DSL
that compiles to Triton) can generate valid Triton code that can be read and adapted.

## Context

**Helion v0.3.1** is a PyTorch DSL by the PyTorch team that com...

### Prompt 8

Base directory for this skill: /home/mike-anderson/.claude/skills/tritonblas-matmul-fp4-api

# tritonblas.matmul_fp4 API (AMD MI355X)

## Problem

`tritonblas.matmul_fp4` is an undiscovered package on the AMD MI355X Popcorn runner
with non-obvious API constraints. It uses Origami chiplet-aware scheduling and a
persistent Triton kernel (`fp4_matmul`) built on `tl.dot_scaled`. Passing native
fp4 dtype causes a silent `KeyError`; layout differs from `aiter.gemm_a4w4`.

## Context / Discovery

Di...

### Prompt 9

Base directory for this skill: /home/mike-anderson/.claude/skills/competitive-kernel-optimization-ceiling

# Competitive Kernel Optimization: Beyond Parameter Tuning

## Problem

After exhausting all tunable parameters in a library (e.g., aiter's `fused_moe`), ranking
stays in the lower half of the leaderboard. The reference implementation is already
well-optimized; parameter sweeps either have no effect, cause correctness failures, or
degrade performance.

## Context: When to Use This

- All...

### Prompt 10

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user wants to continue optimizing GPU kernels for the Luma AMD Speedrun competition on MI355X hardware. The specific instruction (from /compact) is: **"Remember we should be using helios to create our custom triton kernels locally and the resources available in the runner, especially Origami."** ...

### Prompt 11

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

### Prompt 12

Can we try all 3 in parallel and learn from each?
Are we using all the resources available in the runner?
Might it help to do some research on the architecture of what we're trying to fine tune instead of pure brute force?

### Prompt 13

Base directory for this skill: /home/mike-anderson/.claude/plugins/cache/claude-plugins-official/superpowers/4.3.1/skills/brainstorming

# Brainstorming Ideas Into Designs

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke an...

### Prompt 14

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

### Prompt 15

Yes, but also keep in mind we have a gemini cli session also trying to submit.  So check other system operations before you submit to make sure we avoid any submission errors due to too many concurrent submission.

