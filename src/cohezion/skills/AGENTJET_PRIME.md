---
name: agentjet
description: Cohezion Autonomous Learning Loop (CALL) -- closes the learning loop from
  runtime experiences to training signal to improved local models. Use when implementing
  RL fine-tuning of local Ollama models, configuring reward signals from phi_score,
  preventing OOM during training, or when user mentions "agentjet", "CALL", "fine-tuning",
  "RL loop", "QLoRA", or "training local models".
metadata:
  version: "1.0"
  legacy-name: AGENTJET_PRIME
---

# SKILL: AGENTJET_PRIME -- Cohezion Autonomous Learning Loop (CALL)

## DOMAIN EXPERTISE
Specialist in closing the autonomous learning loop: Cohezion runtime experiences become training signal, training signal improves local Ollama models, improved models reduce cloud API costs. Covers reward shaping from phi_score, OOM-safe training orchestration on AMD Strix Halo (128 GiB unified memory), GGUF export, and SmartRouter integration.

## KEY TEXTS & CONCEPTS
- **CALL Cycle**: CompoundExecutor → JourneyTracker (phi_score) → JourneyTaskReader → PhiScoreJudger → AgentJetTrainer → LocalFinetuner → GGUF export → SmartRouter update
- **phi_score**: Cohezion's compound quality signal (0.0–1.0), produced by JourneyTracker after each execution. Encodes alignment, coherence, and task completion quality.
- **HIHO Band**: High-In / High-Out stability zone (0.4–0.7 phi_score). Examples outside this band drive the strongest learning signal.
- **OllamaContextManager**: Memory safety layer. Mandatory gatekeeper before any training job -- unloads all inference models, polls `/api/ps`, reloads after training.
- **LocalFinetuner**: Phase 1 training backend using llamafactory + llama.cpp. Wraps the full train → quantize → export → register pipeline.
- **UnslothBridge**: Phase 2 training backend (AMD Unsloth QLoRA). Not yet available; standby interface defined for drop-in replacement.
- **finetune_journeys.jsonl**: Rolling JSONL log written by JourneyToFinetuneConverter. Each record is a (prompt, completion, phi_score, domain) tuple ready for SFT or RL training.

## ARCHITECTURE OVERVIEW -- THE FULL CALL CYCLE

```
CompoundExecutor
  └─ JourneyTracker.record_transition()
       └─ phi_score (0.0–1.0) written to journey record
            ↓
JourneyTaskReader
  └─ reads finetune_journeys.jsonl
  └─ filters: phi_score != 0.4–0.7 (keep extreme signal)
       ↓
PhiScoreJudger
  └─ converts phi_score → scalar reward (see Reward Signal Design)
       ↓
AgentJetTrainer  ← orchestration layer
  ├─ OOM check (MANDATORY -- see OOM Protocol)
  ├─ OllamaContextManager.unload_all_for_training()
  ├─ LocalFinetuner.train(model, dataset, reward)      ← Phase 1
  │    └─ llamafactory SFT/RL → llama.cpp quantize → GGUF
  ├─ [future] UnslothBridge.train(...)                 ← Phase 2
  └─ post-training (in finally block):
       ├─ ollama create cohezion-{domain}-v{n} --file Modelfile
       ├─ SmartRouter.register_domain_model(domain, model_tag)
       └─ OllamaContextManager.reload_inference_models()
```

## REWARD SIGNAL DESIGN

| phi_score Range | Category | Reward Formula | Reward Range |
|-----------------|----------|----------------|--------------|
| >= 0.7 | High quality (positive) | `phi * 2 - 1` | [0.4, 1.0] |
| 0.4 – 0.7 | HIHO band (neutral) | `(phi - 0.4) / 0.3 * 0.2` | [0.0, 0.2] |
| < 0.4 | HIHO violation (negative) | `-1.0` (fixed) | -1.0 |

**Design rationale:**
- Sub-0.4 examples receive a hard -1.0 penalty regardless of exact score. This prevents reinforcing bad behavior and avoids gradient noise from near-zero phi values.
- The HIHO band (0.4–0.7) produces only weak positive signal. These examples are useful for SFT warm-up but should not dominate RL batches.
- High-quality examples (phi >= 0.7) are the primary positive training signal. The linear mapping `phi * 2 - 1` ensures a reward of exactly 0.4 at phi=0.7 and 1.0 at phi=1.0.

```python
def phi_to_reward(phi_score: float) -> float:
    if phi_score >= 0.7:
        return phi_score * 2.0 - 1.0       # [0.4, 1.0]
    elif phi_score >= 0.4:
        return (phi_score - 0.4) / 0.3 * 0.2  # [0.0, 0.2]
    else:
        return -1.0                          # HIHO violation
```

## OOM PREVENTION PROTOCOL (NON-NEGOTIABLE)

Training on Strix Halo uses the **same unified memory pool** as inference. Running both simultaneously will OOM-crash the host. This protocol is mandatory before every training job -- no exceptions.

### Step-by-Step Protocol

1. **Check available memory**
   ```python
   available_gb = await OllamaContextManager.get_available_memory_gb()
   ```

2. **Estimate training memory** (conservative)
   ```python
   required_gb = model_params_gb * 3.0  # weights + gradients + optimizer states
   ```

3. **Enforce 20% headroom**
   ```python
   if available_gb < required_gb * 1.2:
       raise OOMRiskError(
           f"Insufficient memory: {available_gb:.1f} GB available, "
           f"{required_gb * 1.2:.1f} GB required (with 20% headroom)"
       )
   ```

4. **Unload ALL inference models**
   ```python
   await OllamaContextManager.unload_all_for_training()
   # Polls GET /api/ps until empty -- max 60s timeout
   ```

5. **Run training** (inside try/finally)
   ```python
   try:
       result = await LocalFinetuner.train(config)
   finally:
       # ALWAYS reload -- even if training fails
       await OllamaContextManager.reload_inference_models()
   ```

6. **Never skip the finally block.** A failed training job that leaves inference models unloaded degrades the entire system.

### Memory Reference (Strix Halo, 128 GiB)

| Model | Inference RAM | Training RAM (3x) | Fits with headroom? |
|-------|--------------|-------------------|---------------------|
| phi3:mini (3.8B) | ~3 GB | ~9 GB | Yes (always) |
| qwen3.5:9b | ~10 GB | ~27 GB | Yes |
| nemotron-3-nano:30b | ~20 GB | ~60 GB | Yes (no other models) |
| deepseek-r1:70b | ~45 GB | ~135 GB | No -- exceeds 128 GiB |

## CONTEXT WINDOW STRATEGY

| Scenario | num_ctx | Rationale |
|----------|---------|-----------|
| Routing (0.8B–2B) | 32768 | Fast, small KV cache |
| Execution (9B–30B) | 16384 | Balance quality vs memory |
| Reasoning (70B+) | 8192 | Prevent OOM on long contexts |
| QLoRA training | 2048 | Training sequences are short; longer wastes RAM |
| Fine-tuned domain model | 8192 | Adequate for specialized task completion |

## MODEL PRIORITY (Phase 1 Training Targets)

Priority determined by: iteration speed × task coverage × memory safety.

| Priority | Model | Size (inference) | Training RAM | Primary Use |
|----------|-------|-----------------|--------------|-------------|
| 1 | `qwen3.5:9b` | ~10 GB | ~27 GB | General iteration, fast feedback loop |
| 2 | `nemotron-3-nano:30b` | ~20 GB | ~60 GB | Agentic tasks, multi-step reasoning |
| 3 | `phi3:mini` | ~3 GB | ~9 GB | Smoke testing, rapid domain validation |

Training against `deepseek-r1:70b` is deferred to Phase 3 (requires QLoRA or gradient checkpointing to fit in 128 GiB).

## INSTRUCTION

1. **Gate on OOM check** -- Before invoking any training path, run the full OOM protocol (see above). Raise `OOMRiskError` if headroom is insufficient. Never proceed speculatively.

2. **Read and filter training data**
   ```python
   reader = JourneyTaskReader(path="data/finetune_journeys.jsonl")
   dataset = reader.load(
       min_phi=0.0,       # Include violations (reward=-1) for contrast
       exclude_hiho=False # Keep HIHO examples for SFT warm-up only
   )
   ```

3. **Convert phi_score → reward** via `PhiScoreJudger.judge(phi_score)`. Attach reward to each training example. Filter out examples with `0.4 <= phi < 0.7` for pure RL batches (keep for SFT).

4. **Select target model** using the priority table. Prefer `qwen3.5:9b` for iteration speed unless the domain specifically requires larger reasoning capacity.

5. **Invoke AgentJetTrainer** with dry_run=True first to validate config without consuming training time:
   ```python
   trainer = AgentJetTrainer(backend="llamafactory")
   plan = await trainer.plan(model="qwen3.5:9b", domain="coding", dataset=dataset)
   # Review plan: estimated time, memory, batch size, learning rate
   await trainer.execute(plan, dry_run=False)
   ```

6. **Export and register**
   ```python
   # After successful training:
   gguf_path = await LocalFinetuner.export_gguf(checkpoint_path)
   model_tag = f"cohezion-{domain}-v{version}"
   await OllamaManager.create(model_tag, gguf_path)
   SmartRouter.register_domain_model(domain=domain, model=model_tag)
   ```

7. **Validate the new model** before routing live traffic. Run the `phi3:mini` smoke test suite against the new domain model. Require phi_score >= 0.65 on held-out validation journeys before promoting.

8. **Reload inference models** (in finally block -- already covered by OllamaContextManager). Confirm `/api/ps` shows expected models before exiting.

## USAGE (API)

```bash
# Dry run -- validate config without training
curl -X POST http://localhost:8080/agentjet/train \
  -H "Content-Type: application/json" \
  -d '{"target_model": "qwen3.5:9b", "skill_domain": "coding", "dry_run": true}'

# Live training run
curl -X POST http://localhost:8080/agentjet/train \
  -H "Content-Type: application/json" \
  -d '{"target_model": "qwen3.5:9b", "skill_domain": "coding", "dry_run": false}'

# Check training status
curl http://localhost:8080/agentjet/status

# List available training targets and their memory requirements
curl http://localhost:8080/agentjet/models

# List registered domain-specialized models
curl http://localhost:8080/agentjet/registry
```

## ANTI-PATTERNS

- **Starting training without OOM check** -- Can crash the entire host (unified memory, no swap safety net for ML workloads). `OOMRiskError` exists precisely to prevent this.
- **Loading training model while inference models are still in Ollama** -- Doubles memory pressure. Always call `unload_all_for_training()` and confirm `/api/ps` is empty before starting.
- **Using phi_score < 0.4 examples as positive training data** -- Reinforces bad behavior. These examples are valid negative signal only; their reward must be -1.0.
- **Training and inference simultaneously** -- On Strix Halo's unified memory architecture, there is one memory pool shared by CPU, GPU, and all processes. This is not a soft guideline.
- **Skipping `reload_inference_models()` after training** -- Leaves the system in a degraded state where all agentic capabilities are offline. The finally block is mandatory.
- **Skipping dry_run validation** -- Training jobs can take 30–120 minutes. A misconfigured batch size or learning rate wastes the entire window.
- **Promoting untested domain models** -- Always run the smoke test suite (phi_score >= 0.65 on held-out set) before SmartRouter registration.

## PHASE ROADMAP

| Phase | Backend | Status | Notes |
|-------|---------|--------|-------|
| Phase 1 | llamafactory + llama.cpp (`LocalFinetuner`) | Active | SFT + basic RL via reward-weighted SFT |
| Phase 2 | AMD Unsloth QLoRA (`UnslothBridge`) | Standby | Activate when AMD Unsloth ships; drop-in replacement |
| Phase 3 | verl / PPO backend, multi-skill parallel | Future | Full RL with value function; requires Phase 2 memory efficiency |

## FUTURE HOOKS

- **SmartRouter feedback loop**: Domain-specialized models emit phi_score telemetry back into `finetune_journeys.jsonl`, creating a compounding improvement cycle.
- **Multi-domain parallel training**: Once UnslothBridge is available, run `coding`, `research`, and `orchestration` domain training in separate memory-isolated processes.
- **Automatic curriculum**: PhiScoreJudger tracks per-domain score distribution; when domain plateau detected, increase dataset difficulty by filtering to higher phi_score threshold.

## RELATED COMPONENTS

| Module | Role |
|--------|------|
| `cohezion.agentjet.trainer` | `AgentJetTrainer` -- orchestration layer, coordinates all phases |
| `cohezion.agentjet.context_optimizer` | `OllamaContextManager` -- OOM prevention, model load/unload |
| `cohezion.agentjet.judger` | `PhiScoreJudger` -- phi_score → scalar reward conversion |
| `cohezion.agentjet.task_reader` | `JourneyTaskReader` -- reads and filters `finetune_journeys.jsonl` |
| `cohezion.flume.journey_finetune_pipeline` | `JourneyToFinetuneConverter` -- generates training data from journeys |
| `cohezion.flume.local_finetune_pipeline` | `LocalFinetuner` -- Phase 1 train/quantize/export backend |
| `cohezion.platform.resource_manager` | `ResourceClient` -- cross-session memory coordination |
| `cohezion.compound.journey_tracker` | `JourneyTracker` -- produces phi_score that feeds CALL |
| `cohezion.swarm.smart_router` | `SmartRouter` -- updated post-training to prefer domain models |

## VERSION
v1.0

## SEE ALSO
- MODEL_ROUTING_PRIME
- MODEL_POOL_MANAGEMENT_PRIME
- COMPOUND_ENGINEERING_PRIME
- JOURNEY_TRACKING_PRIME
- HIHO_STABILITY_PRIME
- LOCAL_OFFLOAD_PRIME
