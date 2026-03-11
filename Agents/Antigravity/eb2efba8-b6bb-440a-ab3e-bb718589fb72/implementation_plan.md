---
type: antigravity-artifact
session_id: eb2efba8-b6bb-440a-ab3e-bb718589fb72
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.310
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Sovereign Akash Node [ON HOLD]

**Status**: **BLOCKED** (Insufficient Capital for Professional Tier)
**Resumption Criteria**: Wallet balance > **100 AKT** (to support multiple concurrent escrow deposits).
**Verified Hardware**: Framework Desktop (Ryzen AI Max+ 395, 128GB Unified, Kernel 6.14).

## Strategy: High-Memory Inference Node
Leveraging 128GB Unified Memory to run 70B+ parameter models.

## User Review Required
> [!WARNING]
> **Project Backlogged**: Do not proceed until funding is secured.
> **Preserved Context**: See `src/cohezion/knowledge_graph/RESEARCH_AKASH_STRIX_HALO.md` for specific hardware verification details.

## Proposed Changes (Pending Resumption)

### 1. Infrastructure (Sovereign Setup)
#### [PENDING] [setup_high_memory_provider.sh](file:///home/mike-anderson/dev/cohezion/ops/akash/setup_high_memory_provider.sh)
- **Step 1**: Install ROCm 6.4+ Userspace Libraries.
- **Step 2**: Install MicroK8s with GPU/DNS.
- **Step 3**: Import `KEPLER_WALLET_KEY`.

#### [PENDING] [provider.yaml](file:///home/mike-anderson/dev/cohezion/ops/akash/provider.yaml)
- **Attributes**: `memory_type=unified_128gb`.
- **Bid Strategy**: Prioritize internal wallet, priced for public capacity.

## Verification Plan
1.  **ROCm Check**: `rocminfo` -> `gfx1151`.
2.  **Escrow Check**: Verify sufficient AKT for 3+ concurrent leases.
