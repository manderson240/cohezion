# Research: Akash on Strix Halo (Ryzen AI Max+ 395)

**Date**: 2026-02-01
**Status**: Verified / Backlogged
**Hardware**: Framework Desktop (Ryzen AI Max+ 395)

## The "Unified Memory" Discovery
Unlike discrete GPUs (capped at 24GB/80GB), this APU features **128GB LPDDR5x-8000 Unified Memory**.
- **Capability**: Can load 70B-100B parameter models (e.g., Llama-3-70B, DeepSeek-R1 Distill) entirely in memory.
- **Market Niche**: "High-Memory Inference Node" (rare on Akash).

## Verification Status
- **Kernel**: **6.14.0-37-generic** ✅ (Confirmed compatible with Strix Halo).
- **Driver**: ROCm userspace libraries (v6.4+) required. (`/sys/class/kfd` is present).
- **Network**: Requires port forwarding (8443, 3000-3100).

## Financial Viability (The Blocker)
- **Minimum**: 5 AKT deposit (Provider) + 30 AKT (Bid Balance).
- **Professional**: To win *multiple* concurrent leases and maximize utilization, a higher bid balance is required (likely 100+ AKT) to satisfy network escrow requirements for parallel workloads.
- **Current State**: Funding insufficient. Project paused until healthy capital reserves (100+ AKT) are established.

## Implementation Blueprint (For Resumption)
1.  **Install ROCm**: Target userspace libraries (User is in `render` group).
2.  **Attribute Advertising**: `memory_type=unified_128gb`.
3.  **Pricing Strategy**:
    - **Self**: Free (Authorized Wallet in `bid_strategy.yaml`).
    - **Public**: Aggressive pricing ($1.00/hr) to capture high-VRAM market.
