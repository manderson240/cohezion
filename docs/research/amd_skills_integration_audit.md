# AMD Official AI Agent Skills Integration & Gap Audit

This report audits Cohezion's integration with the official AMD AI Agent Skills repository ([`https://github.com/amd/skills`](https://github.com/amd/skills)), housed under [`src/cohezion/skills/amd/skills-repo/`](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/amd/skills-repo/).

---

## 1. Inventory & Integration Status

| AMD Official Skill | File Location | Purpose & Core Capabilities | Cohezion Integration Level | Status |
|---|---|---|---|:---:|
| **`local-ai-use`** | `src/cohezion/skills/amd/skills-repo/skills/local-ai-use/` | Routes multimodal calls (SD-Turbo, Kokoro TTS, Whisper STT) to Lemonade Server (`:13305`) to eliminate cloud API costs. | **HIGH (Active)**: Documented in `AGENTS.md` and routed via `UnifiedHybridRouter`. | 🟢 **Integrated** |
| **`local-ai-app-integration`** | `src/cohezion/skills/amd/skills-repo/skills/local-ai-app-integration/` | Bundles embeddable Lemonade daemon (`lemond`) for private, offline app inference without cloud dependencies. | **HIGH (Active)**: Used for sovereign local background daemons. | 🟢 **Integrated** |
| **`serving-llms-on-epyc`** | `src/cohezion/skills/amd/skills-repo/skills/serving-llms-on-epyc/` | CPU-optimized LLM serving using vLLM + Zentorch extensions on AMD Zen CPUs. | **MEDIUM**: Configured in inference recipes for Ryzen 9 7945HX CPU fallback. | 🟡 **Configured** |
| **`serving-llms-on-instinct`** | `src/cohezion/skills/amd/skills-repo/skills/serving-llms-on-instinct/` | ROCm + vLLM / SGLang serving on AMD Instinct accelerators. | **LOW**: Stored for cloud-scale GPU migration (local box uses Radeon 8060S iGPU). | ⚪ **Cataloged** |
| **`magpie-kernel-evaluator`** | `src/cohezion/skills/amd/skills-repo/skills/magpie-kernel-evaluator/` | Benchmarks and validates custom GPU kernel correctness on RDNA/CDNA architectures. | **MEDIUM**: Available for GPU kernel testing. | 🟡 **Configured** |
| **`tracelens-analysis-orchestrator`** | `src/cohezion/skills/amd/skills-repo/skills/tracelens-analysis-orchestrator/` | Orchestrates modular PyTorch profiler trace analysis with subagent parallelism. | **HIGH (Active)**: Used for auditing PyTorch UMA memory copies and GPU kernel bottlenecks. | 🟢 **Integrated** |

---

## 2. Synergies with Cohezion Architecture
1. **Multimodal Zero-Cost Gating**: `local-ai-use` pairs directly with Cohezion's `EVI > 0.75` gating policy, ensuring multimodal operations never trigger cloud token spend.
2. **TraceLens Profiling for UMA Zero-Copy**: `tracelens-analysis-orchestrator` is the exact tool recommended in Claude's consultation to audit and eliminate unnecessary `hipMemcpy` buffer shuttling across the Strix Halo unified memory bus.
3. **Embeddable Daemon Architecture**: `local-ai-app-integration` ensures our autonomous background daemons (`hardened_daemon_v2.py`, `overnight_agi_daemon.py`) execute completely offline.
