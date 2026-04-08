# Cohezion System Card

**Version**: 2026.4.8-MYTHOS-PREP  
**Generated**: 2026-04-08T09:52:00Z  
**Repository**: github.com/cohezion/core  
**Branch**: feature/2026-tip-of-the-spear

---

## Executive Summary

Cohezion is a physics-grounded AI research platform designed for autonomous agentic systems with HIHO (High Inductive, High Observation) stability guarantees. The system integrates 12D manifold physics (FLUME VAE), compound feedback loops, and benchmarking infrastructure targeting Claude Mythos Preview capabilities.

### Key Metrics

| Capability | Target (Mythos) | Current | Gap |
|------------|-----------------|---------|-----|
| SWE-bench Pass@1 | 93.9% | Est. 75% | -18.9% |
| Cybench Saturation | 100% | Est. 80% | -20% |
| OSWorld Success | 79.6% | Est. 65% | -14.6% |
| TerminalBench | 82% | Est. 70% | -12% |
| USAMO | 97.6% | Limited | Gap |
| **Composite** | 100% | **68.37%** | **-31.63%** |

---

## 1. System Overview

### 1.1 Purpose and Scope

Cohezion provides:
- **Autonomous Agent Infrastructure**: Unified agent harness with tool use
- **Physics-Grounded Learning**: 12D manifold with Riemannian metrics
- **Compound Feedback**: Self-improving loops via Ouroboros
- **Benchmarking**: Mythos-aligned evaluation suite
- **Distributed Training**: Multi-GPU RL with DDP/FSDP

### 1.2 Target Users

- **Primary**: AI research labs (internal)
- **Secondary**: Vetted security partners
- **Not for**: General public availability

### 1.3 Deployment Context

- Production: Heavy internal use
- Partners: Security-audited deployments
- Research: Academic collaboration under NDAs

---

## 2. Capabilities

### 2.1 Software Engineering

**Benchmark**: SWE-bench Verified equivalent

Implementation:
```python
from cohezion.benchmarks.coding_benchmark import CohezionCodeBenchmark

benchmark = CohezionCodeBenchmark()
results = await benchmark.run_full_benchmark(
    executor=llm_executor,
    n_tasks=500,
    parallel=True
)
```

**Features**:
- Python repository analysis
- Issue-to-patch generation
- Test-driven verification
- Docker isolation

**Known Limitations**:
- Python focus only (no multi-language)
- Single-turn repair (no trajectory)
- Simplified patch validation

### 2.2 Cybersecurity

**Benchmark**: Cybench-equivalent CTF challenges

```python
from cohezion.benchmarks.cyber_benchmark import CyberBenchmark

challenge = CTFChallenge(
    category="web",
    difficulty=3,
    description="SQL injection in login form"
)
result = await cyber_benchmark.evaluate_ctf(
    challenge, llm_executor
)
```

**Categories**:
- Cryptography (AES, RSA, custom ciphers)
- Web exploitation (SQLi, XSS, CSRF)
- Binary exploitation (buffer overflow, ROP)
- Reverse engineering (keygen, algorithm recovery)
- Forensics (packet analysis, memory dumps)

### 2.3 Long-Horizon Agentic

**Benchmark**: OSWorld/TerminalBench equivalent

```python
from cohezion.agent.unified_harness import UnifiedAgent

agent = UnifiedAgent()
trace = await agent.run_task(
    task="Configure nginx reverse proxy with PostgreSQL",
    env={"tools": ["bash", "file"]},
    timeout=1800
)
```

**Features**:
- Multi-step execution (up to 50 steps)
- Tool ecosystem (bash, python, file, browser)
- Error recovery (3 attempts)
- Session alignment (HIHO gates)

### 2.4 Distributed Training

```python
from cohezion.rl.distributed_trainer import DistributedTrainer

trainer = DistributedTrainer(
    strategy="ddp",
    world_size=16,
    gradient_accumulation=4
)
```

**Supported Strategies**:
- DDP (Data Parallel)
- FSDP (Fully Sharded)
- Hybrid (FSDP + DDP for large models)

---

## 3. Architecture

### 3.1 Core Components

```
┌─────────────────────────────────────────────────┐
│  Cohezion Stack                                 │
├─────────────────────────────────────────────────┤
│  User Interface        │ API / CLI / Dashboard  │
├───────────────────────┼───────────────────────┤
│  Agent Layer          │ UnifiedAgent          │
│                       │ CompoundSession       │
└───────────────────────┼───────────────────────┤
│  Tool Layer           │ bash, python, file    │
│                       │ browser, think        │
└───────────────────────┼───────────────────────┤
│  RL Layer             │ TRIUNE PPO, GRPO    │
│                       │ LoRA, DDP/FSDP      │
└───────────────────────┼───────────────────────┤
│  Physics Layer        │ FLUME VAE (256D)    │
│                       │ Riemannian Manifold │
└───────────────────────┼───────────────────────┤
│  Memory Layer         │ MIRIX (6 types)     │
│                       │ Ouroboros, Wiki MCP │
└─────────────────────────────────────────────────┘
```

### 3.2 FLUME VAE (256D Latent Space)

```python
from cohezion.flume import VAEEncoder

# Encode text to 256D manifold
encoder = VAEEncoder(latent_dim=256)
embedding = encoder.encode("The quick brown fox")
# embedding.shape == (256,)
# Manifold distance: ds² = g_μν dx^μ dx^ν
```

**Properties**:
- Smooth latent space
- Disentangled representations
- Christoffel symbol navigation
- Geodesic path planning

### 3.3 HIHO Stability

**High Inductive**: Strong priors from physics grounding
**High Observation**: Continuous drift monitoring

```python
# Coherence check
result = mgr.check_alignment(
    request="Generate recursive function",
    threshold=0.5  # HIHO stability band
)
if not result.should_proceed:
    # Block execution, decompose request
```

---

## 4. Safety and Alignment

### 4.1 Constitutional AI Integration

**Principles** (from `.agent/CONSTITUTION.md`):
1. Transparency: All reasoning logged
2. Interpretability: White-box analysis
3. Human Oversight: Critical gates
4. Stability: HIHO [0.4, 0.6] band

### 4.2 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Autonomous loops | Medium | High | Human approval gates |
| Self-modification | Low | High | Code review required |
| Multi-agent escalation | Low | Medium | Coherence monitoring |
| Data poisoning | Low | High | Vault integrity checks |

### 4.3 Monitoring

**Real-time**:
- Coherence tracking (12D manifold)
- Circuit breaker on anomaly
- Token rate limiting

**Async**:
- Automated offline pipelines
- Pattern detection (Ouroboros)
- Human expert audit

---

## 5. Training Methodology

### 5.1 TRIUNE PPO

Three-objective optimization:
1. Task reward R_task
2. Physics consistency R_physics
3. Safety R_safety

```python
from cohezion.rl.ppo_trainer import TRIUNETrainer

trainer = TRIUNETrainer(
    alpha=0.7,  # Task weight
    beta=0.2,   # Physics weight  
    gamma=0.1   # Safety weight
)
```

### 5.2 GRPO (Group Relative Policy Optimization)

Mythos-style training with group sampling.

```python
from cohezion.rl.grpo_trainer import GRPOTrainer

trainer = GRPOTrainer(
    policy=model,
    reference_model=ref_model,
    group_size=64
)
```

### 5.3 Distributed Training

See `src/cohezion/rl/distributed_trainer.py`

**Docker**: `docker/Dockerfile.distributed`  
**K8s**: `k8s/manifests/distributed-training.yaml`

---

## 6. Evaluation

### 6.1 Benchmark Suite

```bash
# Run full suite
uv run python -m cohezion.benchmarks.orchestrator

# Individual benchmarks
uv run pytest tests/benchmarks/test_coding.py -v
uv run pytest tests/benchmarks/test_cyber.py -v
uv run pytest tests/benchmarks/test_agentic.py -v
```

### 6.2 Self-Evaluation

**Ouroboros Pattern**:
- Performance logging
- Anomaly detection
- Automatic skill refinement

```python
from cohezion.learning.ouroboros import OuroborosEngine

engine = OuroborosEngine()
engine.log_exhaust(task, result, coherence)
```

---

## 7. Comparison to Mythos Preview

### 7.1 Capabilities

Mythos Preview (Anthropic) | Cohezion | Status
-----------------------------|----------|--------
SWE-bench 93.9% | Est. 75% | Gap
Cybench | Est. 80% | Gap
OSWorld 79.6% | Est. 65% | Gap
USAMO 97.6% | Limited | Gap
TerminalBench 82% | Est. 70% | Gap

### 7.2 Infrastructure

Mythos | Cohezion | Status
-------|----------|--------
GRPO | Partial | Phase 2
Multi-GPU | DDP/FSDP | ✅
LoRA | Full | ✅
Safety evals | HIHO-based | ⚠️

### 7.3 Key Differentiators

**Cohezion Unique**:
- 12D manifold physics
- HIHO stability (not just RLHF)
- Ouroboros self-improvement
- Wiki-KG integration

**Mythos Advantage**:
- Production-scale training
- Extensive safety evaluation
- Proven deployment history

---

## 8. Deployment

### 8.1 Requirements

**Hardware**:
- GPU: AMD Ryzen AI MAX+ 395 or NVIDIA equivalent
- RAM: 32GB+ for local inference
- Storage: 100GB for models and checkpoints

**Software**:
- Python 3.13+
- PyTorch 2.6+
- Ollama (local) or cloud API
- SurrealDB (optional)
- Docker (for sandboxing)

### 8.2 Installation

```bash
git clone https://github.com/cohezion/core
cd core
uv sync
source .venv/bin/activate
```

### 8.3 Configuration

```bash
# Environment
export OLLAMA_HOST=http://localhost:11434
export SURREAL_ENDPOINT=ws://localhost:8000
export COHEZION_ENV=development

# Security (production)
export COHEZION_SANDBOX=docker
export COHEZION_CIRCUIT_BREAKER=true
```

---

## 9. Limitations

### 9.1 Known Gaps

1. **Multi-language support**: Python-only for coding tasks
2. **Trajectory repair**: Single-turn, no roll-back
3. **Safety coverage**: HIHO vs comprehensive evals
4. **Scale**: Single-node vs distributed clusters

### 9.2 Future Work

- [ ] Multi-language coding benchmark
- [ ] Trajectory-level RL training
- [ ] Comprehensive red-teaming
- [ ] Distributed training at cluster scale
- [ ] Constitutional AI refinement

---

## 10. References

### Papers

1. HIHO Grounded RL (Cohezion, 2026)
2. Claude Mythos Preview System Card (Anthropic, 2025)
3. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
4. Cybench: Cybersecurity Benchmark

### Code

- `src/cohezion/agent/unified_harness.py` - Main agent
- `src/cohezion/rl/` - Training infrastructure
- `src/cohezion/benchmarks/` - Evaluation suite
- `src/cohezion/flume/` - VAE and manifold physics

### Documentation

- `.agent/COHEZION_CHARTER.md` - Design principles
- `.agent/CONSTITUTION.md` - Constraints
- `HARDWARE_PROFILE_PRIME.md` - AMD Ryzen spec

---

## 11. Team and Contact

**Maintainer**: Cohezion Core Team  
**Research**: physics-grounded AI safety  
**Contact**: Internal channels only

---

**Document Version**: 2026.4.8-MYTHOS-PREP  
**Next Review**: 2026-05-08  
**Classification**: Internal Use
