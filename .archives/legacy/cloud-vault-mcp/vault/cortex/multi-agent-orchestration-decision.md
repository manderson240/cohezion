# Cohezion Multi-Agent Orchestration: Decision & Implementation

**Date**: 2026-04-10  
**Decision**: Cohezion-Native + GAIA Patterns  
**Status**: ✅ Ready to Implement

---

## Decision Summary

### Question
Should Cohezion use AMD GAIA, third-party frameworks, or native orchestration for multi-agent systems?

### Answer
**Cohezion-Native + GAIA Patterns** - Enhance existing infrastructure with AMD-optimized patterns.

---

## Evaluation Results

### GAIA Framework
- ✅ **AMD Native** - NPU/iGPU optimized, 100% local
- ✅ **C++ Support** - Low latency, hardware-accelerated
- ❌ **Overlap** - Redundant with existing TeamOrchestrator
- ❌ **New Abstractions** - Requires learning new architecture

**Verdict**: Use for NPU-specific optimizations, not primary orchestration.

### Third-Party Frameworks (LangGraph/CrewAI/AutoGen)
- ✅ **Ecosystem** - Large communities, documentation
- ❌ **Overlap** - Redundant with existing `team_orchestrator`, `democratic_debate`
- ❌ **Dependencies** - Heavy frameworks, vendor lock-in
- ❌ **Customization** - Limits flexibility

**Verdict**: Borrow patterns, don't adopt frameworks wholesale.

### Cohezion-Native (Selected)
- ✅ **Leverages existing** - TeamOrchestrator, ComputeBackendRouter, vault integration
- ✅ **No dependencies** - Clean integration, FLUME-first
- ✅ **Customizable** - Full control over abstractions
- ✅ **Validated models** - Gemma-4-E2B-it (97 TPS), Jan-v1-4B, qwen3:4b

**Verdict**: **PRIMARY APPROACH**

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              COHEZION MULTI-AGENT ORCHESTRATION             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Enhanced TeamOrchestrator                          │  │
│  │  - Specialist routing (validated models)          │  │
│  │  - GAIA-style tool registry                        │  │
│  │  - Hardware-aware execution (NPU/GPU/Cloud)        │  │
│  └──────────────────┬────────────────────────────────────┘  │
│                     │                                        │
│     ┌───────────────┼────────────────┐                     │
│     ▼               ▼                ▼                     │
│  ┌────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Code   │    │ Reasoning│    │ Long Ctx │               │
│  │Specialist      │    │Specialist      │    │Specialist      │
│  │        │    │          │    │          │               │
│  │Model:  │    │Model:    │    │Model:    │               │
│  │qwen3:4b│    │Gemma-4-  │    │Gemma-4-  │               │
│  │Backend:│    │E2B-it    │    │E2B-it    │               │
│  │NPU     │    │Backend:  │    │Backend:  │               │
│  │TPS: 75│    │Vulkan    │    │Vulkan    │               │
│  └────────┘    └──────────┘    └──────────┘               │
│         │            │              │                     │
│         └────────────┴──────────────┘                     │
│                     ▼                                        │
│            ┌──────────────┐                                │
│            │ Vault MCP    │                                │
│            │ HIHO Checks  │                                │
│            │ Metric Tracking│                              │
│            └──────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Specialist Agents (Validated)

| Specialist | Model | Backend | TPS | Use Case |
|------------|-------|---------|-----|----------|
| **CodeSpecialist** | qwen3:4b | NPU | 75 | Code gen, review, debugging |
| **ReasoningSpecialist** | Gemma-4-E2B-it-GGUF | GPU Vulkan | 97 | Complex reasoning, 256K ctx |
| **NovelSpecialist** | Jan-v1-4B-GGUF | GPU Vulkan | 76 | Research, experiments |

---

## Implementation Phases

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Specialist Router | Week 1 | Routing by task type |
| Phase 2: Tool Registry | Week 1-2 | GAIA-style tool system |
| Phase 3: Multi-Agent Execution | Week 2 | End-to-end orchestration |
| Phase 4: Validation | Week 2-3 | Benchmarking, tests |

---

## Files Created

1. `MULTI_AGENT_ORCHESTRATION_ANALYSIS.md` - Full comparison analysis
2. `IMPLEMENTATION_PLAN.md` - Detailed implementation guide with code

## Files to Create (Next)

1. `src/cohezion/swarm/specialist_agents.py` - Specialist definitions
2. `src/cohezion/swarm/specialist_router.py` - Task routing
3. `src/cohezion/swarm/tool_registry.py` - GAIA-style tools
4. `src/cohezion/swarm/multi_agent_orchestrator.py` - Orchestration

---

## Key Benefits

1. **Validates existing infrastructure** - Cohezion already had team orchestration
2. **Leverages validated models** - Gemma-4-E2B-it (97 TPS) already tested
3. **No external dependencies** - Clean, maintainable code
4. **AMD optimized** - NPU/GPU hybrid via existing router
5. **Integrated** - Works with vault, HIHO, metrics

---

## Next Action

**Start Phase 1**: Create `src/cohezion/swarm/specialist_agents.py`

Define validated specialist agents for code, reasoning, and novel tasks.

---

*Decision by*: Cohezion Agent  
*Analysis Date*: 2026-04-10  
*Ready to implement*: ✅
