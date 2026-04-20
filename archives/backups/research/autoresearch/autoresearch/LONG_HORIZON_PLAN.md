# Long-Horizon Autoresearch: Cohezion Mythos-Readiness

**Session Duration**: 4-6 hours continuous  
**Objective**: Achieve 85%+ alignment with Claude Mythos Preview capabilities across benchmarks, RL infrastructure, and system architecture  
**Primary Metric**: `composite_readiness_score` (weighted average of benchmark coverage, RL capability, and architecture coherence)

---

## Phase Overview

### Phase 1: Benchmark Infrastructure (Hours 0-1.5)
**Goal**: Complete SWE-bench compatible evaluation pipeline

**Tasks**:
1. ✅ Coding benchmark scaffold exists - needs Docker integration
2. Create cybersecurity benchmark (Cybench equivalent)
3. Create long-horizon agentic benchmark (OSWorld/TerminalBench equivalent)
4. Create math/reasoning benchmark (USAMO equivalent)
5. Create safety/alignment evaluation (SHADE-Arena equivalent)

**Deliverables**:
- `benchmarks/cyber_benchmark.py` - CTF-style security challenges
- `benchmarks/agentic_benchmark.py` - Multi-step tasks with sandboxes
- `benchmarks/math_benchmark.py` - Competition math problems
- `benchmarks/safety_benchmark.py` - Covert capabilities evaluation
- `benchmarks/orchestrator.py` - Unified benchmark runner

**Success Criteria**:
- All benchmarks can run in Docker containers
- Report generation with Mythos-comparable metrics
- 90%+ test coverage

---

### Phase 2: RL Training Infrastructure (Hours 1.5-3)
**Goal**: Production-grade RL training comparable to Anthropic's RLHF pipeline

**Tasks**:
1. ✅ TRIUNE PPO exists - needs GRPO/PPO upgrade
2. Create RL environment for code generation
3. Create RL environment for agentic tasks
4. Implement reward model training (LoRA-based RM)
5. Implement KL-regularized RLHF
6. Create distributed training coordination

**Deliverables**:
- `rl/environments/code_env.py` - Gymnasium env for coding
- `rl/environments/agentic_env.py` - Multi-step task env
- `rl/reward_model.py` - Trainable reward model
- `rl/grpo_trainer.py` - GRPO implementation (Mythos uses this)
- `rl/rlhf_pipeline.py` - End-to-end RLHF orchestration
- `rl/safety_constraints.py` - Constitutional AI constraints

**Success Criteria**:
- RL training converges on coding tasks
- Reward model achieves >0.8 correlation with human judgments
- Distributed training works across 4+ GPUs

---

### Phase 3: Coherent Architecture Integration (Hours 3-4.5)
**Goal**: Unify existing components into agentic system comparable to Claude Code

**Tasks**:
1. ✅ Compound loop exists - needs tool integration
2. ✅ Wiki integration exists - needs better retrieval
3. ✅ FLUME VAE exists - needs agent integration
4. Create unified agent harness (like Claude Code)
5. Integrate all tools: wiki, MCP, compound, swarm
6. Create memory system for long-horizon tasks
7. Improve HIHO stability monitoring

**Deliverables**:
- `agent/unified_harness.py` - Main agent loop
- `agent/tool_integration.py` - Tool use framework
- `agent/memory.py` - Long-horizon memory (MIRIX integration)
- `agent/safety_monitor.py` - Runtime safety checks
- `agent/autonomous_loop.py` - Self-improving agent

**Success Criteria**:
- Agent can complete 10+ step tasks autonomously
- Tool use is reliable (>90% success)
- Safety monitor catches concerning behaviors

---

### Phase 4: System Card Generation & Documentation (Hours 4.5-6)
**Goal**: Generate comprehensive system card matching Mythos Preview documentation

**Tasks**:
1. Run all benchmarks, collect results
2. Generate safety evaluation report
3. Document RL training process
4. Create capabilities assessment
5. Write alignment evaluation summary
6. Document monitoring and mitigations

**Deliverables**:
- `docs/system_card/SYSTEM_CARD.md` - Main system card (200+ pages)
- `docs/system_card/capabilities.md` - Benchmark results
- `docs/system_card/alignment.md` - Alignment evaluation
- `docs/system_card/safety.md` - Safety mitigations
- `docs/system_card/training.md` - Training methodology
- `docs/system_card/risk_assessment.md` - Risk pathways analysis

**Success Criteria**:
- System card matches Mythos structure
- All sections have quantitative evidence
- Risk pathways documented with mitigations

---

## Continuous Improvement Loop

Every 30 minutes:
1. Run fast benchmark subset (<5 min)
2. Check git status - commit if stable
3. Log progress to `autoresearch.jsonl`
4. Adjust priorities based on blockers

Every hour:
1. Run full test suite
2. Update `progress_report.md`
3. Checkpoint working state

---

## Starting State Assessment

### Existing Assets (from context):
- ✅ TRIUNE PPO trainer
- ✅ LoRA trainer
- ✅ Distributed trainer (DDP/FSDP)
- ✅ Benchmark suite (HIHO-specific)
- ✅ Autoresearch framework
- ✅ Compound loop
- ✅ Wiki integration (Karpathy pattern)
- ✅ FLUME VAE (256D)
- ✅ MIRIX memory
- ✅ Ouroboros self-improvement
- ✅ Stitch design system
- ✅ Sandbox tooling (Docker/Firecracker)

### Critical Gaps:
- ❌ SWE-bench coding benchmark (Docker-based)
- ❌ Cybersecurity evaluation
- ❌ Long-horizon agentic benchmark
- ❌ Safety/covert capabilities eval
- ❌ GRPO training (Mythos uses this)
- ❌ Reward model training
- ❌ Unified agent harness
- ❌ System card documentation

---

## Blocker Mitigation

If docker unavailable:
- Fall back to subprocess-based isolation
- Document limitation

If GPU unavailable:
- Use CPU with smaller models
- Document in results

If benchmark data unavailable:
- Create synthetic datasets
- Document as limitation

---

## Expected Outcomes

By session end:
- [ ] 4 new benchmark suites operational
- [ ] RL training pipeline for code/tasks
- [ ] Unified agent harness
- [ ] 200+ page system card draft
- [ ] Composite readiness score > 75%

---

*Generated: 2026-04-08*  
*Version: Long-Horizon v1.0*
