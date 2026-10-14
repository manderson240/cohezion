You are Claude Fable 5.1, serving as Cohezion's Master Systems Architect and Evaluator.
Conduct an adversarial, unhurried architectural and strategic evaluation of our active Kaggle competition portfolio and 24/7 autonomous infrastructure:

### Context & Active Competitions ($2,237,000 Total Portfolio)
1. **Biohub 3D Cell Tracking ($60,000, Ends Sept 29 — <48 Hours Left)**:
   - Metric: Tracking Accuracy (TRA) via Acyclic Oriented Graph Matching (AOGM).
   - Cost penalties: w_FN = 10.0 (false negative vertex), w_NS = 5.0 (false split), w_ED = 1.5 (edge deletion), w_EA = 1.5 (edge addition), w_FP = 1.0 (false positive vertex).
   - Core tension: False negative vertices (w_FN = 10.0) penalize 10x worse than false positives (w_FP = 1.0). Pruning uncertain detections aggressively destroys TRA.
   - Our implementation: Kernel v21 currently running on Kaggle NvidiaL4 GPU. Incorporates:
     * Restored unpruned detection chassis (tau in [0.930, 0.945]) to prevent FN cascade.
     * Mitotic Center-of-Mass conservation: ||(i1*d1 + i2*d2)/(i1+i2) - parent|| <= 3.5 um.
     * Mitotic daughter divergence repulsion: ||d1 - d2|| >= 3.5 um (eliminating false splits where daughters occupy same centroid).
     * Temporal track persistence filter: Pruning only isolated singleton vertices with track length < 2 frames.
   - Critical decision: Final 2 submission selections for Private Leaderboard evaluation.

2. **Kaggriculture Market Simulation ($50,000, Ends Sept 30 — <72 Hours Left)**:
   - Metric: Final coin wealth at Turn 720 (Day 30).
   - Our standing: SOTA v6 (#56612362) at 1351.0 rating, SOTA v7 (#56614155) at 1310.5 on live tournament ladder. Top 10 ladder cutoff is ~2920.
   - SOTA v7 Innovation: Rayon 32-thread simulation revealed that predatory competitor bots dump massive wheat/milk supplies on Turns 27-28, crashing spot prices to near zero. SOTA v7 implements pre-emptive Dutch auction liquidity on Days 24-25 when spot prices exceed 5.0 (milk) and 10.0 (melon), securing cash before the liquidity trap.
   - Critical question: If rival bots also anticipate early liquidation, what prevents an earlier price crash (Day 23), and how should order-book priority (_vq_compact) be tuned?

3. **ARC Prize 2026 ($1,550,000 Total Across Tracks, Ends Nov 2 — 35 Days Left)**:
   - ARC-AGI-2 ($700k Track): Current score 31.81% (Top 9.5%, Silver Medal, Rank 212/2192). Model: Qwen3-4B LoRA SFT139 + AutoHarness zero-cost bytecode verifier. Ref #56609704 currently pending hidden evaluation.
   - ARC-AGI-3 ($850k Track): Interactive MDP puzzle environment with 35-100 step budgets. Pure CPU solver developed (Zobrist SplitMix64 hashing + Cayley action budgeting + affordance BFS) executing in Kaggle's unlimited CPU pool (0 GPU quota). Kernel v1 completed, armed for automated dispatch at 00:00 UTC quota reset.

4. **24/7 Autonomous Infrastructure**:
   - Host: AMD Strix Halo (128GB Unified Memory, Ryzen AI MAX+ 395 16C/32T, Radeon 8060S iGPU, XDNA2 NPU).
   - Autonomous Rust Sentinel daemon (cohezion-sentinel) running continuously at <2 MB RSS, monitoring Kaggle kernels and auto-submitting outputs upon completion.
   - Cron heartbeat running every 15 minutes.
   - Strict adherence to offline inference (enable_internet: false) and max 2 concurrent Kaggle GPU sessions.

### Questions for Claude Fable 5.1:
1. **Biohub Final Selection Strategy**: Between the conservative pure Hungarian baseline (0.946) and the hardened Mitotic COM + Repulsion model (v21), how should we allocate our 2 final private leaderboard evaluation slots to protect against private shakeup?
2. **Kaggriculture Counter-Predatory Hardening**: How can SOTA v7 safeguard against higher-order predatory auction dynamics without surrendering yield on days 20-24?
3. **ARC-AGI-3 CPU Scaling**: Since Kaggle offers unlimited CPU compute sessions, how can we leverage parallel CPU search architectures to maximize exploration depth on interactive puzzles without hitting memory or timeout limits?
4. **Sentinel & Fleet Resilience**: Identify any single point of failure in our 24/7 background execution and quota recovery pipeline.

Deliver your unhurried, rigorous analysis. Report measured numbers and honest boundaries.
