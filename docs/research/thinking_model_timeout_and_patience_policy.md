# ⏳ Thinking Model Timeout & Patience Policy

**Principle**: *'Leave plenty of time for the fat to render.'*  
**Date**: 2026-08-24  

## local_npu_igpu_thinking
- **Models**: `DeepSeek-R1-8B, Qwen3-Coder-30B, gpt-oss-20b, qwen3.6-moe-35b`
- **Timeout**: **300.0s** (5.0 min)
- **Rationale**: Allows local models full time to generate 4,000+ tokens of deep chain-of-thought without premature SIGKILL or HTTP timeouts.

## frontier_cloud_thinking
- **Models**: `deepseek-v4-pro:cloud, qwen3.5:397b-cloud, glm-5.2:cloud`
- **Timeout**: **600.0s** (10.0 min)
- **Rationale**: Frontier 1.6T and 397B parameter models require up to 2-3 minutes for deep multi-step mathematical derivations.

## fast_ast_deterministic
- **Models**: `AutoHarness AST, Sheaf Gluer, Poincaré Metric`
- **Timeout**: **5.0s** (0.1 min)
- **Rationale**: Pure Python algebraic and geometric operations finish in microseconds (<0.01ms).

