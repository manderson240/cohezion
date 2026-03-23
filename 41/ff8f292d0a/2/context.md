# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Luma AMD Speedrun — Breakthrough Attempts

## Context

Previous turn completed infrastructure (popcorn.py, driver.py wired) and submitted all 3
kernels to leaderboard. Current ranked geomeans:

| Kernel | Our Score | Leader | Gap |
|--------|----------|--------|-----|
| MLA | 79.9 µs | ~33 µs | 2.4x |
| MoE | 180.1 µs | ~110 µs | 1.6x |
| GEMM | 24.3 µs | ~13.4 µs | 1.8x |

**Root cause of gap**: Leaders use single fused GPU kernels (one dispatch, zero P...

### Prompt 2

Base directory for this skill: /home/mike-anderson/.claude/skills/tritonblas-matmul-fp4-api

# tritonblas.matmul_fp4 API (AMD MI355X)

## Problem

`tritonblas.matmul_fp4` is an undiscovered package on the AMD MI355X Popcorn runner
with non-obvious API constraints. It uses Origami chiplet-aware scheduling and a
persistent Triton kernel (`fp4_matmul`) built on `tl.dot_scaled`. Passing native
fp4 dtype causes a silent `KeyError`; layout differs from `aiter.gemm_a4w4`.

## Context / Discovery

Di...

### Prompt 3

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

