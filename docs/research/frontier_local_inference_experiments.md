We need answer as Principal AI Systems Researcher/Frontier AGI Architect. Need brainstorm 5 high-impact sovereign experimental campaigns with local inference across Strix Halo NPU, iGPU, CPU. Need detail each: title/hypothesis, hardware partitioning, execution protocol/metric, SurrealDB/Obsidian schema. Need structured rigorous Markdown. Need incorporate given hardware/architecture: AMD Strix Halo Framework Desktop 16, 128GB unified RAM, XDNA2 NPU 50 TOPS, Radeon 8060S iGPU RDNA3.5 12GB+ shared, 16-core Ryzen 9 7945HX. Local runtimes Lemonade OmniRouter :13305, Ollama :11434, ROCm/Vulkan. Models: Qwen3-Coder-30B GGUF/Vulkan, DeepSeek-Qwen3-8B-GGUF, llama3.2-1b-FLM NPU, qwen3.6-moe-35b NPU, embed-gemma-300m-FLM NPU. Cohezion architecture: 12D Poincaré hyperbolic state tracking, AutoHarness AST policy verifiers (arXiv:2603.03329v1), HIHO 0.5 reality sonification, SurrealDB + Obsidian dual-persistence.

Need produce 5 experiments. Should be high-impact, sovereign, test fundamental AGI/physics/cognitive capability. Need map compute across NPU/iGPU/CPU. Need metrics like Pass@k, tokens/sec, hyperbolic geodesic distance d_P, Lyapunov exponent, entropy delta. Need storage schema.

Need be creative but plausible. Could include:
1. Hyperbolic Self-Consistency and Causal Trajectory Collapse: test whether 12D Poincaré embeddings can detect hallucination/confabulation via geodesic divergence; NPU embedding, iGPU reasoning, CPU verifier.
2. Speculative Drafting with NPU draft model and iGPU large model verification; measure acceptance rate, tokens/sec, entropy delta.
3. AutoHarness AST Policy Verifier as a formal grammar over model outputs; CPU bytecode verifier, iGPU generation, NPU embedding; measure pass@k, false positive rate.
4. HIHO 0.5 reality sonification as an auxiliary loss / feedback signal for self-correction; maybe sonification of entropy/divergence to guide NPU/iGPU loop.
5. Sovereign multi-agent debate with local models partitioned across NPU/iGPU/CPU, using hyperbolic state tracking to measure consensus convergence; metric Lyapunov exponent of debate dynamics.
6. Maybe "Cognitive Time Crystal" experiment: periodic re-evaluation of same prompt under varying temperature, measure phase transitions in embedding space, Lyapunov exponents.
7. "Adversarial AutoHarness fuzzing" to find policy violations in generated code; CPU AST verifier, iGPU code generation, NPU embedding for semantic similarity.

Need ensure each experiment has hardware partitioning explicitly. Need include SurrealDB/Obsidian schema: maybe SurrealDB tables/records for trajectories, metrics, embeddings; Obsidian markdown notes with YAML frontmatter, links, Mermaid diagrams, sonification logs.

Need format structured. Could use headings for each experiment. Need maybe include a summary table at top? The prompt asks brainstorm 5 campaigns, for each detail. We can provide intro and then 5 sections.

Need be rigorous. Use math notation where appropriate. Need mention local inference across NPU, iGPU, CPU. Need mention models used. Need maybe include "sovereign" aspects: no cloud, local data, reproducible.

Let's design 5 experiments:

Experiment 1: "Hyperbolic Hallucination Horizon: Geodesic Divergence as a Confabulation Early-Warning System"
Hypothesis: In 12D Poincaré ball, truthful vs confabulated completions follow different geodesic trajectories; divergence rate (Lyapunov exponent) predicts hallucination before semantic incoherence.
Hardware: NPU runs embed-gemma-300m-FLM to embed prompt and partial completions into 12D Poincaré; iGPU runs Qwen3-Coder-30B (Vulkan) for autoregressive generation; CPU runs AutoHarness AST verifier on generated code/text to label truthfulness; also CPU computes geodesic distances and Lyapunov exponents from NPU embeddings.
Protocol: Generate N=1000 completions on coding tasks; at each token step, compute embedding of prefix, project to Poincaré ball, compute geodesic distance from initial prompt embedding; estimate local Lyapunov exponent λ via average logarithmic growth of infinitesimal perturbations; compare λ distribution for verified-correct vs hallucinated outputs. Metric: AUC of λ for hallucination detection, tokens/sec, Pass@k on code tasks.
Storage: SurrealDB tables: `trajectory` (id, prompt_hash, model, timestamp, token_sequence, embedding_vector, geodesic_distance, lyapunov_est, verifier_label), `experiment_run`; Obsidian note per run with YAML frontmatter, Mermaid diagram of divergence, links to SurrealDB records, sonification log (HIHO 0.5 mapping λ to audio pitch).

Experiment 2: "NPU Speculative Drafting with Hyperbolic Acceptance Gates"
Hypothesis: A small NPU model (llama3.2-1b-FLM or qwen3.6-moe-35b NPU) can serve as a speculative drafter for a large iGPU model (Qwen3-Coder-30B), and acceptance/rejection decisions can be improved by a hyperbolic distance gate between drafter and verifier embeddings, reducing wasted compute.
Hardware: NPU runs drafter model (llama3.2-1b-FLM) to propose K tokens; iGPU runs large model to verify in parallel; CPU computes embedding of proposed tokens via embed-gemma-300m-FLM (could also be NPU but CPU for orchestration) and hyperbolic distance between drafter's predicted next-token distribution and verifier's distribution; if distance > threshold, reject early.
Protocol: Measure acceptance rate, tokens/sec, speedup vs baseline, entropy delta of accepted tokens. Metric: tokens/sec, acceptance rate, hyperbolic geodesic distance d_P between distributions, KL divergence, speedup factor.
Storage: SurrealDB `speculative_draft` records with drafter_id, verifier_id, prompt, proposed_tokens, accepted_tokens, rejection_reason, d_P, speedup; Obsidian note with performance graphs and threshold tuning.

Experiment 3: "AutoHarness AST Policy Verifier as a Differentiable Oracle for Self-