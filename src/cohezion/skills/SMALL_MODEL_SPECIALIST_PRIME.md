---
name: small-model-specialist-prime
description: "`` SIMPLE Task → phi3:mini (2.2GB, <100ms) ↓ (if low confidence) MEDIUM Task → qwen2-math:7b OR qwen2.5-coder:7b (4.4-4.7GB, ~200ms) ↓ (if low confidence) COMPLEX Task → Cloud fallback (qwen3.5:cloud, minimax-m2.7:cloud) ``"
---

# SMALL_MODEL_SPECIALIST_PRIME

**Skill**: Local Model Specialization & Tip-of-Spear Routing
**Version**: 1.0
**Purpose**: Guide optimal task-to-model routing for 70-85% cloud token reduction
**Context**: AMD Ryzen AI MAX+ 395 (128GB RAM, 4 concurrent model limit)

## Core Strategy: 3-Tier Routing Cascade

```
SIMPLE Task → phi3:mini (2.2GB, <100ms)
  ↓ (if low confidence)
MEDIUM Task → qwen2-math:7b OR qwen2.5-coder:7b (4.4-4.7GB, ~200ms)
  ↓ (if low confidence)
COMPLEX Task → Cloud fallback (qwen3.5:cloud, minimax-m2.7:cloud)
```

**Memory Budget**:
- HOT tier (always loaded): 3.2GB (3 models)
- WARM tier (startup loaded): 17.9GB (5 models)
- COLD tier (on-demand): 10-30GB per model
- **Max concurrent**: 3 models (OOM safety with other sessions)
- **Worst-case footprint**: 21.1GB

## Model Capabilities Matrix

### HOT Tier (Always Available, <100ms response)

| Model | Size | Specialty | Use When | Avoid When |
|-------|------|-----------|----------|------------|
| **phi3:mini** | 2.2GB | General reasoning, function calling | Simple queries, basic logic, quick answers | Complex math, large code refactoring |
| **nomic-embed-text** | 274MB | Embeddings, semantic search | Document similarity, semantic cache | Text generation (not generative) |
| **lfm2.5-thinking** | 731MB | Fast reasoning chains | Simple logic, branching decisions | Multi-step proofs, complex algorithms |

### WARM Tier (Loaded at Startup, ~200ms response)

| Model | Size | Specialty | Use When | Avoid When |
|-------|------|-----------|----------|------------|
| **qwen2-math:7b** | 4.4GB | Mathematical reasoning, proofs | Calculus, algebra, theorem proving | General code, vision tasks |
| **mathstral:7b** | 4.1GB | Mistral math variant | Statistics, probability, optimization | NLP, code generation |
| **qwen2.5-coder:7b** | 4.7GB | Code generation, debugging | Python/JS/Rust code, syntax fixes | Math proofs, vision |
| **ministral-3:3b** | 3.0GB | Multilingual, small Mistral | Non-English text, fast multilingual | Long-context (limited 8K) |
| **moondream** | 1.7GB | Vision understanding | Charts, diagrams, screenshots, OCR | Text-only tasks |

### COLD Tier (On-Demand, 10-30GB, ~1-5s load time)

| Model | Size | Specialty | Use When | Avoid When |
|-------|------|-----------|----------|------------|
| **deepcoder:14b** | 9.0GB | Deep code understanding | Complex refactoring, architecture review | Simple syntax fixes (use 7B) |
| **phi4:latest** | 9.1GB | Advanced reasoning (14B-quality in 9GB) | Complex logic, multi-step reasoning | Simple queries (overkill) |
| **qwen2.5-coder:14b** | 9.0GB | Advanced code generation | Large codebases, complex algorithms | Quick fixes (use 7B) |
| **gpt-oss:20b** | 13GB | OpenAI-style reasoning | GPT-like tasks, general intelligence | Domain-specific (use specialist) |
| **devstral-small-2:24b** | 15GB | Mistral dev variant | Advanced dev workflows | Resource-constrained (use 7B) |
| **glm-4.7-flash** | 19GB | Fast Chinese + English | Bilingual tasks, Chinese NLP | English-only (use smaller) |
| **nemotron-3-nano:30b** | 24GB | NVIDIA research (highest quality local) | When cloud quality needed locally | Fast iteration (slow load) |

### Cloud Tier (Zero Memory, API Cost)

| Model | Cost | Specialty | Use When | Avoid When |
|-------|------|-----------|----------|------------|
| **qwen3.5:cloud** | $$$| Latest Qwen (Feb 2026) | Cutting-edge reasoning | Local models sufficient |
| **qwen3.5:397b-cloud** | $$$$| Max performance Qwen | Critical production tasks | Development/testing |
| **kimi-k2.5:cloud** | $$$| Kimi K2.5 (March 2026) | Long context (128K+) | Short tasks |
| **minimax-m2.7:cloud** | $$$| MiniMax cloud | Specialized MiniMax tasks | General queries |

## Routing Decision Tree

### Step 1: Detect Domain

**Math Domain** (≥2 math keywords: solve, calculate, prove, derivative, integral, equation, etc.)
- → Route to **qwen2-math:7b** (WARM) or **mathstral:7b** (WARM)

**Code Domain** (≥2 code keywords OR code pattern: ```, def, class, function, etc.)
- → Route to **qwen2.5-coder:7b** (WARM) for medium complexity
- → Route to **deepcoder:14b** (COLD) for complex refactoring

**Vision Domain** (≥2 vision keywords: image, chart, diagram, plot, etc.)
- → Route to **moondream** (WARM)

**General Domain**
- → Continue to Step 2

### Step 2: Analyze Complexity

**SIMPLE** (token_count < 30, no complex keywords, no code):
- → **phi3:mini** (HOT)
- Examples: "What is HIHO?", "Explain coherence", "List 3 approaches"

**MEDIUM** (token_count 30-200, moderate logic, may have code):
- Domain routing:
  - Math → **qwen2-math:7b** (WARM)
  - Code → **qwen2.5-coder:7b** (WARM)
  - General → **phi3:mini** (HOT) if simple reasoning, else **qwen2.5-coder:7b** (WARM)
- Examples: "Implement bubble sort", "Calculate standard deviation", "Refactor this function"

**COMPLEX** (≥2 complex keywords OR long query OR multi-step logic):
- Domain routing:
  - Math → **mathstral:7b** (WARM) → **Cloud** if insufficient
  - Code → **deepcoder:14b** (COLD) → **qwen2.5-coder:14b** (COLD) → **Cloud**
  - General → **phi4:latest** (COLD) → **gpt-oss:20b** (COLD) → **Cloud**
- Examples: "Design distributed cache architecture", "Prove Fermat's Last Theorem simplified case"

### Step 3: Confidence Check (Tip-of-Spear Pattern)

After routing to a model, check confidence score:

```python
if confidence < 0.7:
    escalate_to_next_tier()
```

**Escalation Path**:
1. HOT (phi3:mini, 2.2GB) → confidence < 0.7
2. WARM (qwen2-math:7b, 4.4GB) → confidence < 0.7
3. COLD (phi4:latest, 9.1GB) → confidence < 0.7
4. CLOUD (qwen3.5:cloud) → final answer

## Expected Savings

**Baseline** (all queries to cloud):
- 1000 queries/day × 200 tokens/query × $0.003/1K tokens = **$0.60/day = $18/month**

**With Tip-of-Spear Routing**:
- 60% routed to HOT (phi3:mini): $0.00
- 25% routed to WARM (qwen2-math:7b): $0.00
- 10% routed to COLD (local): $0.00
- 5% escalated to CLOUD: $0.03/day

**Total cost**: **$0.03/day = $0.90/month**
**Savings**: **95% reduction** (from $18/month to $0.90/month)

**Conservative Estimate** (accounting for escalations):
- 50% routed to HOT/WARM: $0.00
- 30% routed to COLD: $0.00
- 20% escalated to CLOUD: $0.12/day = $3.60/month

**Conservative savings**: **80% reduction** (from $18/month to $3.60/month)

## Usage Examples

### Example 1: Simple Query (HOT tier)

**Query**: "What is the HIHO principle?"

**Routing**:
1. Complexity: SIMPLE (15 tokens, simple keywords)
2. Domain: General
3. Decision: **phi3:mini** (HOT, 2.2GB, <100ms)

**Why**: Factual recall, no reasoning depth required

### Example 2: Math Query (WARM tier)

**Query**: "Calculate the derivative of f(x) = 3x² + 2x - 5"

**Routing**:
1. Complexity: MEDIUM (20 tokens, math keywords: calculate, derivative)
2. Domain: **MATH** (derivative, calculate)
3. Decision: **qwen2-math:7b** (WARM, 4.4GB, ~200ms)

**Why**: Domain specialist for calculus

### Example 3: Code Query with Escalation (WARM → CLOUD)

**Query**: "Refactor this 500-line Python class to use async/await patterns"

**Routing**:
1. Complexity: COMPLEX (code pattern, large scope)
2. Domain: **CODE**
3. Initial: **qwen2.5-coder:7b** (WARM, 4.7GB)
4. Confidence: **0.65** (below 0.7 threshold)
5. Escalate: **deepcoder:14b** (COLD, 9.0GB)
6. Confidence: **0.68** (still below 0.7)
7. Final: **qwen3.5:cloud** (CLOUD)

**Why**: Large refactoring requires high confidence, worth cloud cost

### Example 4: Vision Query (WARM tier)

**Query**: "Extract data from this bar chart screenshot"

**Routing**:
1. Complexity: MEDIUM
2. Domain: **VISION** (chart, screenshot)
3. Decision: **moondream** (WARM, 1.7GB, ~200ms)

**Why**: Vision specialist, no text-only model can handle this

## Integration with Compound Loop

When executing compound engineering tasks:

```python
from cohezion.swarm.cost_aware_router import CostAwareRouter

router = CostAwareRouter.get_default()

# Let router select optimal model
decision, can_proceed = router.select_model(
    query=user_request,
    max_cost_usd=0.01  # Budget constraint
)

if not can_proceed:
    logger.warning(f"Budget exceeded, using local-only fallback")
    # Force local routing (see BudgetEnforcer integration)

# Execute with selected model
result = await execute_with_model(decision.model, query)

# Record actual usage for cost tracking
router.record_execution(
    model=decision.model,
    actual_tokens=len(result.split()),  # Rough estimate
    duration_ms=elapsed_ms,
    success=True
)
```

## OOM Safety Guidelines

**With Other Sessions Running**:
1. **Never load >3 models concurrently** (max_concurrent_loaded = 3)
2. **Monitor memory pressure** (threshold: 80%)
3. **Evict COLD models after 10 min idle** (cold_evict_timeout_s = 600)
4. **Prefer WARM over COLD when uncertain** (WARM models stay loaded)

**Emergency Fallback** (if approaching OOM):
```python
# Force evict all COLD models
pool_manager.evict_all_cold()

# Fallback to HOT tier only
router.restrict_to_hot_tier_only()
```

## Monitoring & Metrics

Track routing effectiveness:

```python
stats = router.get_statistics()

print(f"Total queries: {stats.total_queries}")
print(f"HOT tier usage: {stats.phi3_routed / stats.total_queries * 100:.1f}%")
print(f"WARM tier usage: {stats.qwen_routed / stats.total_queries * 100:.1f}%")
print(f"CLOUD tier usage: {stats.deepseek_routed / stats.total_queries * 100:.1f}%")
print(f"Total cost: ${stats.total_cost_usd:.4f}")
print(f"Savings vs cloud-only: {stats.cost_vs_deepseek_only:.1f}%")
```

**Success Criteria**:
- HOT tier usage: >40%
- WARM tier usage: >30%
- CLOUD tier usage: <20%
- Cost savings: >70%

## Anti-Patterns (Common Mistakes)

❌ **Don't**: Route all queries to largest model "to be safe"
✅ **Do**: Trust the complexity analyzer, escalate only on low confidence

❌ **Don't**: Load all WARM models at startup (OOM risk)
✅ **Do**: Respect max_concurrent_loaded = 3 limit

❌ **Don't**: Ignore domain detection (e.g., routing math to general model)
✅ **Do**: Use domain specialists (qwen2-math for math, moondream for vision)

❌ **Don't**: Keep COLD models loaded indefinitely
✅ **Do**: Evict after 10 min idle (cold_evict_timeout_s = 600)

❌ **Don't**: Escalate to cloud without checking budget
✅ **Do**: Integrate with BudgetEnforcer, fallback to best local model if budget exceeded

## Version History

- **v1.0** (2026-03-21): Initial skill - 3-tier routing with domain detection, OOM safety for multi-session environment

---

**Implementation Status**: ✅ Phase 1 Complete (Model Pool + Complexity Classifier)
**Next Phase**: Implement TipOfTheSpearRouter with confidence-based escalation
**Expected Impact**: 70-85% cloud token reduction, <5% quality degradation
