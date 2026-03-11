# AMD x GPU MODE Hackathon Rules & Constraints

## Overview
- **Phase 1: Qualifiers** (Mar 6, 2026 - Mar 30, 2026)
- **Objective:** Optimize three critical GPU kernels:
  1. MXFP4 MoE
  2. MLA Decode
  3. MXFP4 GEMM
- **Target Hardware:** AMD Instinct™ MI355X GPUs.

## Submission Rules (Phase 1)
- Submissions must be made using the **Popcorn CLI** (https://github.com/gpu-mode/popcorn-cli).
- Scoring is based on the **absolute runtime/speed** of the kernel averaged over a large set of test cases.
- **Top 10 fastest kernels** for each problem will be considered for aggregate score.
- Submissions must beat the baseline to receive points.
- Only the **top scoring kernel** for each problem from a team will be considered.

## Eligibility & Compliance
- **GitHub ID:** manderson240
- **Discord ID:** miked238725
- Team size: Up to 3 members.
- Must register on Luma and AMD Developer Program.
- Must have a valid Discord ID and GitHub ID.
- All submissions must be **original work**.
- If advancing to Phase 2, code must be mergeable into AMD repositories (ATOM/vLLM/SGLang).
