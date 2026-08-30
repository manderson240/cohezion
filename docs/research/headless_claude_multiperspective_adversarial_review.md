# Headless Claude Opus 4.5 Adversarial Review: Cohezion Heterogeneous Stack

**Date**: 2026-08-21  
**Reviewer**: Headless Claude Opus 4.5 (Principal Systems Architect & Adversarial Evaluator)  
**Target System**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (Strix Halo, 128GB Unified Memory)  
**Inference Engine**: Lemonade OmniRouter (Port `13305`)  

---

## 1. Cynical Hardware/Kernel Architect
**Focus:** Memory bus contention, thermal throttling, register pressure, NPU driver stability.

- **UMA Bus Saturation Risks:** Claiming 91.8% theoretical bandwidth saturation (210 GB/s) on a UMA bus shared between CPU, iGPU, and NPU is playing with fire. The moment the OS pages memory or an unexpected interrupt hits, latency jitter will spike, causing tail-latency degradation for the 128B Mistral-Medium.
- **Thermal Throttling & Power Capping:** Running Qwen3.6-MoE on NPU, Qwen3-Coder on iGPU, and a 128B model on CPU simultaneously will inevitably hit the SoC's thermal design power (TDP) limit. The kernel will underclock the iGPU/CPU to protect the silicon, rendering the 88.1 tok/s decode rate an ephemeral burst metric, not a sustained throughput.
- **NPU Driver Preemption:** Current AMD/Ryzen NPU drivers lack robust hardware preemption. A long-running inference kernel on the NPU (like the 35B MoE) can lock up the command queues, causing the driver to timeout and reset, which takes down the entire Lemonade 13305 router stack.

---

## 2. Frontier AGI Systems & Swarm Orchestrator
**Focus:** Agent latency, tool-calling determinism, multi-session race conditions, EventBus durability.

- **Tree-Attention Speculative Decoding Race Conditions:** Using the NPU as a draft model and iGPU as a verifier introduces complex synchronization logic. If the NPU draft drifts too far from the iGPU verifier due to stochastic sampling, the rollback latency negates all speculative gains.
- **EventBus Bottlenecks:** The 4-layer pinning defense and EventBus might serialize asynchronous tool-calling across agents. Under high concurrency, the EventBus becomes a single point of failure (SPOF) and a massive contention point, destroying multi-session scalability.
- **KV-Cache Prefix Eviction:** The 38.6ms prompt cache hit relies on strict KV-Cache reuse. In a swarm setting, interleaved requests from different agents will thrash the KV-cache, causing catastrophic capacity misses and triggering full recomputation.

---

## 3. Formal Verification & Quality Assurance Lead
**Focus:** AST bytecode verification, AutoHarness zero-cost claims, failure modes under OOM.

- **Zero-Cost Abstraction Fallacy:** AutoHarness cannot provide zero-cost AST bytecode verification in a highly concurrent heterogeneous environment. Dynamic memory allocations during bytecode parsing will introduce GC pauses or allocator contention.
- **OOM Cascades:** The UMA architecture means an OOM from the 128B CPU model directly steals pages from the iGPU's GTT (Graphics Translation Table). When this happens, the iGPU faults, causing a hard crash of the router rather than graceful degradation.
- **Silent Wavefront Corruption:** Persistent wavefront decoding relies on contiguous memory. If memory becomes fragmented, the paging logic might silently corrupt KV states, leading to deterministic but incorrect outputs that evade standard unit tests.

---

## 4. Sovereign Infrastructure & Security Auditor
**Focus:** Port exposure, loopback security, model provenance, cloud egress.

- **Lemonade Port 13305 Exposure:** Binding the router policy to a TCP port (even on loopback) is vulnerable to cross-site websocket hijacking (CSWSH) if a developer runs a browser on the same machine. Local privilege escalation could allow arbitrary model querying.
- **Cloud Egress & Data Exfiltration:** Evacuating 128B to iGPU MXFP4 or integrating Frontier Cloud Models (Qwen-397B, DeepSeek-V4 Pro) blurs the line between local sovereignty and cloud dependency. Without a hardened egress firewall, sensitive telemetry or prompt data could leak to third-party endpoints.
- **Model Provenance Vulnerabilities:** The reliance on various quantized formats (GGUF, MXFP4, FLM, IQ4_KT) means downloading binaries from untrusted sources (e.g., HuggingFace). A poisoned model could execute adversarial payloads via buffer overflows in the quantizer backend.

---

## Synthesis & Actionable Remediations

### Critical Vulnerabilities
1. Unified memory contention leading to system-wide lockups under concurrent multi-agent load.
2. NPU driver hangs causing cascading failures in the Lemonade router.
3. Lack of memory isolation between CPU, iGPU, and NPU leading to potential GTT faults and KV-cache corruption.

### Actionable Remediations
1. **Implement cgroups & TDP Capping:** Strictly partition memory and set static power limits per device to prevent thermal throttling and OOM cascades.
2. **Watchdog Timers for NPU/iGPU:** Introduce a microsecond-resolution watchdog that restarts the inference engine gracefully if hardware queues stall.
3. **Hardened Local Mux:** Enforce strict loopback authentication or Unix Domain Sockets (UDS) for port `13305` to mitigate local escalation vectors.
4. **Dynamic Batching with QoS:** Replace static KV-cache prefixing with a QoS-aware dynamic batcher that prioritizes active agent threads over background verification tasks.
