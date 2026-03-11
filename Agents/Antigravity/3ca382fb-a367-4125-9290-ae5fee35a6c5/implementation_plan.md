---
type: antigravity-artifact
session_id: 3ca382fb-a367-4125-9290-ae5fee35a6c5
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.305
  stage: embryo
  cluster: Agents
---

# Plan: Explaining the VLIW Performance Record

## Goal
To remember and explain how the 349-cycle VLIW record was achieved and why it's difficult to reproduce on other platforms.

## Proposed Report Structure
1.  **The Record**: Confirming the 349 cycles / 423x speedup milestone.
2.  **The "Secret Sauce"**:
    - **Software Pipelining**: 28-way/32-way window parallelism.
    - **Engine Balancing**: The `Hash Hybrid` optimization and `SG Offload`.
    - **Crown Cache**: Pre-broadcasting tree levels 1-2.
    - **List Scheduling & Tail Compaction**: The 4-pass scheduler logic.
3.  **Platform Discrepancy Analysis**:
    - Differences in `SLOT_LIMITS` (12 ALU slots is extremely generous).
    - Simulator behavior (Overlap/Barriers).
    - SIMD support (`VLEN=8`).

## Verification
- Reference `KEY_LEARNINGS.md` (Learning 5).
- Reference `optimizer.py` (line 140+ for compaction, line 375+ for hash hybrid).
- Reference `problem.py` (SLOT_LIMITS).
