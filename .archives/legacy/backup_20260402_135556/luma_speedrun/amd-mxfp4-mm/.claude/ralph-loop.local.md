---
active: true
iteration: 1
session_id: 
max_iterations: 12
completion_promise: "GEMM leaderboard submission completed with benchmark time under 20us"
started_at: "2026-04-02T14:29:40Z"
---

Optimize GEMM kernel for Luma AMD Speedrun. load_inline is BLOCKED on runner. Use aiter API with tuned configs and AITER_BYPASS_TUNE_CONFIG=1. Submit via popcorn-cli. Try torch.cuda._compile_kernel HIPRTC path. Target under 20us. Persist results to SurrealDB. Every kernel change must be tested on runner via popcorn --mode test before continuing.
