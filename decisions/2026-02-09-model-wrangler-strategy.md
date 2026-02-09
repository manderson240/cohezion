---
title: "Model Wrangler Strategy - Local LLM Management & Optimization"
date: 2026-02-09
status: proposed
tags: [decision, local-llms, model-management, fine-tuning, benchmarking]
---

# Model Wrangler Strategy - Local LLM Lifecycle Management

**Role**: **DAILY DRIVER** - Continuous model monitoring, rapid benchmarking, aggressive swapping, on-demand fine-tuning
**Goal**: Maintain cutting-edge local LLM performance in a volatile, fast-moving ecosystem
**Cadence**: **Daily monitoring**, **same-day benchmarking** on major releases, **24-hour swap cycles**, continuous fine-tuning

---

## Responsibilities

### 1. Model Monitoring (DAILY)

**Track Latest Releases** (automated feeds + manual checks):
- Llama family (Meta) - llama3.2, llama3.3, etc.
- Mistral family - mistral-small, mistral-nemo, etc.
- Phi family (Microsoft) - phi-3, phi-4, etc.
- Gemma family (Google) - gemma-2, gemma-3, etc.
- Qwen family (Alibaba) - qwen2.5, qwen3, etc.
- Specialized models - nomic-embed-text, codegemma, etc.

**Monitor Sources** (checked DAILY, 9am):
- ✅ Hugging Face "Trending Models" page (top 20)
- ✅ Ollama library updates (new model announcements)
- ✅ LM Studio Discord #model-releases channel
- ✅ Reddit /r/LocalLLaMA sorted by "new" (last 24 hours)
- ✅ Papers with Code leaderboards (MMLU, HumanEval, etc.)
- ✅ Twitter/X: @ollama, @huggingface, @MetaAI, @MistralAI
- ✅ GitHub: Watch repos for llama.cpp, ollama, transformers
- ✅ Discord: LocalLLaMA, Ollama official, LM Studio

**Automated Alerts** (via RSS/webhooks):
```bash
# Daily digest script (runs at 9am)
python daily_model_digest.py

# Output:
# ──────────────────────────────────────────────
# 📊 Model Wrangler Daily Digest - 2026-02-09
# ──────────────────────────────────────────────
# 🆕 NEW RELEASES (last 24 hours):
#   - qwen2.5-14b-coder (8 hours ago) - Claims +15% HumanEval vs qwen2.5
#   - phi-4.5-mini (12 hours ago) - Microsoft's 3.8B model, 90% of phi-4 performance
#
# 🔥 TRENDING:
#   - deepseek-r1:7b (3 days old, 500+ upvotes on HF)
#   - llama3.3:8b (1 week old, Meta claims 12% speed improvement)
#
# ⚠️ ALERTS:
#   - Current model (llama3.2:8b) now 2 versions behind
#   - Recommendation: Benchmark llama3.3:8b TODAY
# ──────────────────────────────────────────────
```

### 2. Benchmarking (SAME-DAY on Major Releases)

**Response Time Targets**:
- **Critical release** (e.g., llama4, gpt-4-local): Benchmark within **4 hours**
- **Major release** (e.g., new model family): Benchmark within **24 hours**
- **Minor release** (e.g., version bump): Benchmark within **48 hours**
- **Experimental model**: Queue for weekend testing

**COHEZION-Specific Benchmarks**:

#### Benchmark Suite A: Gap Analysis
```python
# Test dataset: 20 sample papers from vault
# Task: Identify conceptual gaps between paper clusters

def benchmark_gap_analysis(model: str) -> dict:
    results = {
        "accuracy": 0.0,    # % of human-validated gaps found
        "speed": 0.0,       # seconds to process 20 papers
        "false_positives": 0.0,  # % of invalid gaps suggested
        "cost": 0.0         # inference cost (if any)
    }

    # Run model on test set
    gaps = run_gap_analysis(model, test_papers)

    # Compare to Claude Opus ground truth
    ground_truth = load_ground_truth("gap_analysis_opus.json")
    results["accuracy"] = compute_overlap(gaps, ground_truth)

    return results
```

#### Benchmark Suite B: Semantic Similarity
```python
# Test dataset: 100 paper pairs with human similarity ratings (0-1)
# Task: Compute embedding similarity, compare to human ratings

def benchmark_embeddings(model: str) -> dict:
    results = {
        "correlation": 0.0,  # Pearson correlation with human ratings
        "speed": 0.0,        # ms per embedding
        "dimension": 0       # embedding dimension size
    }

    # Generate embeddings for test papers
    embeddings = generate_embeddings(model, test_papers)

    # Compare to human ratings
    predicted_sim = cosine_similarity_matrix(embeddings)
    results["correlation"] = pearsonr(predicted_sim, human_ratings)

    return results
```

#### Benchmark Suite C: Agent Journey Affinity
```python
# Test dataset: 10 agent contexts + 84 papers
# Task: Score papers by relevance to agent context

def benchmark_affinity_scoring(model: str) -> dict:
    results = {
        "precision_at_5": 0.0,  # Top 5 papers actually relevant?
        "speed": 0.0,           # seconds to score 84 papers
        "context_sensitivity": 0.0  # How well does it use agent context?
    }

    for agent_context in test_contexts:
        scores = score_papers(model, agent_context, all_papers)
        # Compare to human expert rankings
        results["precision_at_5"] += precision_at_k(scores, expert_ranking, k=5)

    return results
```

### 3. Model Selection Criteria

**Decision Matrix**:

| Criterion | Weight | Measurement |
|-----------|--------|-------------|
| **Accuracy** | 40% | Gap analysis accuracy vs Opus ground truth |
| **Speed** | 30% | Inference time (must be < 2s for real-time tasks) |
| **Resource Usage** | 20% | RAM consumption, CPU/GPU utilization |
| **Context Window** | 10% | Tokens supported (prefer 8K+) |

**Minimum Thresholds**:
- Gap analysis accuracy: ≥ 70% (compared to Claude Opus)
- Embedding correlation: ≥ 0.80 (Pearson r)
- Real-time affinity scoring: < 1 second for 84 papers
- RAM usage: < 16GB (must run on typical workstation)

### 4. Model Swapping (On Better Release)

**Swap Decision**:
```python
def should_swap_model(current_model: str, new_model: str) -> bool:
    """Decision criteria for model replacement"""

    current_bench = load_benchmark(current_model)
    new_bench = run_benchmark(new_model)

    # Compute improvement score
    improvements = {
        "accuracy": (new_bench["accuracy"] - current_bench["accuracy"]) * 0.4,
        "speed": (1 / new_bench["speed"] - 1 / current_bench["speed"]) * 0.3,
        "resource": (current_bench["ram"] - new_bench["ram"]) / current_bench["ram"] * 0.2,
        "context": (new_bench["context_window"] - current_bench["context_window"]) / 8192 * 0.1
    }

    total_improvement = sum(improvements.values())

    # Swap if ≥ 10% improvement OR critical bug fix
    return total_improvement >= 0.10 or new_model.has_critical_fix()
```

**Swap Process**:
1. Benchmark new model on COHEZION test suite
2. Compare to current model performance
3. If improvement ≥ 10%, prepare swap
4. Update `ai_config.yaml` with new model name
5. Test integration (run gap analysis on 5 sample papers)
6. If tests pass, deploy to production
7. Monitor for 24 hours, rollback if issues
8. Document swap in vault: `daily/2026-XX-XX-model-swap-[old]-to-[new].md`

### 5. Fine-Tuning (Monthly)

**When to Fine-Tune**:
- Accuracy < 70% on COHEZION benchmarks
- Repeated false positives in gap analysis
- Poor understanding of vault-specific concepts (MCP, compound engineering, etc.)
- New domain added to vault (e.g., 20 biology papers added)

**Fine-Tuning Dataset**:
```python
# Generate training data from vault + Claude Opus labels

def generate_finetuning_dataset():
    dataset = []

    # Task 1: Gap Analysis
    for cluster_pair in all_cluster_pairs:
        gaps = claude_opus.find_gaps(cluster_pair)  # Ground truth
        dataset.append({
            "input": f"Find gaps between clusters: {cluster_pair}",
            "output": json.dumps(gaps),
            "task": "gap_analysis"
        })

    # Task 2: Semantic Similarity
    for paper_pair in all_paper_pairs:
        similarity = claude_opus.compute_similarity(paper_pair)
        dataset.append({
            "input": f"Rate similarity: {paper_pair}",
            "output": str(similarity),
            "task": "similarity"
        })

    # Task 3: Agent Affinity
    for agent_context, paper in all_context_paper_pairs:
        affinity = claude_opus.score_affinity(agent_context, paper)
        dataset.append({
            "input": f"Score relevance: {agent_context} | {paper}",
            "output": str(affinity),
            "task": "affinity"
        })

    return dataset  # ~500 examples total
```

**Fine-Tuning Pipeline**:
```bash
# Using Ollama Modelfile for fine-tuning

# 1. Generate training data
python generate_training_data.py --vault /path/to/vault --output finetuning.jsonl

# 2. Create Modelfile
cat > Modelfile << EOF
FROM llama3.2:8b

# Fine-tuning for COHEZION vault analysis
PARAMETER temperature 0.7
PARAMETER top_p 0.9

# Add training examples
ADAPTER ./finetuning.jsonl
EOF

# 3. Build custom model
ollama create cohezion-llama:latest -f Modelfile

# 4. Benchmark custom model
python benchmark.py --model cohezion-llama:latest

# 5. If accuracy improved, swap in production
```

**Fine-Tuning Frequency**:
- **Monthly**: General accuracy tuning
- **On-Demand**: New domain added (e.g., vault grows to 200 papers)
- **Quarterly**: Major model version upgrade (e.g., llama3 → llama4)

---

## Model Registry (Current Recommendations)

### Tier 1: Production Models (Currently Deployed)

| Task | Model | Version | RAM | Speed | Accuracy | Last Updated |
|------|-------|---------|-----|-------|----------|--------------|
| **Embeddings** | nomic-embed-text | v1.5 | 274MB | 50ms/doc | 0.85 | 2025-11 |
| **Gap Analysis** | llama3.2:8b | 8B | 4.7GB | 2s/20 papers | 72% | 2025-10 |
| **Quick Inference** | mistral:7b | 7B | 4.1GB | 500ms | 68% | 2025-09 |
| **Deep Analysis** | llama3.2:70b | 70B | 40GB | 20s | 88% | 2025-10 |

### Tier 2: Candidate Models (Under Evaluation)

| Model | Version | RAM | Benchmark Status | Notes |
|-------|---------|-----|------------------|-------|
| **qwen2.5:14b** | 14B | 8GB | ✅ 75% accuracy | Faster than llama3.2:8b, better accuracy |
| **phi-4:14b** | 14B | 7GB | 🔄 Testing | Microsoft's latest, claims better reasoning |
| **gemma-2:9b** | 9B | 5GB | ⏳ Queued | Google's updated model |
| **deepseek-r1:7b** | 7B | 4GB | ⏳ Queued | Strong on reasoning tasks |

### Tier 3: Experimental Models (Research Only)

| Model | Version | RAM | Status | Notes |
|-------|---------|-----|--------|-------|
| **aya-expanse:8b** | 8B | 5GB | 🔬 Research | Multilingual, good for diverse papers |
| **solar-pro:22b** | 22B | 12GB | 🔬 Research | Claims SOTA on reasoning |

---

## Model Upgrade Calendar (Example)

### Week of 2026-02-09: Initial Setup
- ✅ Deploy llama3.2:8b (gap analysis)
- ✅ Deploy nomic-embed-text (embeddings)
- ✅ Deploy mistral:7b (quick inference)
- ✅ Benchmark all 3 models on COHEZION test suite
- ✅ Document baseline performance

### Week of 2026-02-16: Candidate Evaluation
- 🔄 Test qwen2.5:14b (reported better accuracy)
- 🔄 Compare qwen vs llama3.2 on gap analysis benchmark
- 🔄 If qwen ≥ 10% better, prepare swap

### Week of 2026-02-23: First Swap (If Justified)
- 🔄 Swap llama3.2:8b → qwen2.5:14b (if benchmarks pass)
- 🔄 Monitor production for 7 days
- 🔄 Document swap in vault

### Month of March 2026: Fine-Tuning
- 🔄 Generate 500-example training dataset from vault
- 🔄 Fine-tune qwen2.5:14b on COHEZION data
- 🔄 Benchmark cohezion-qwen:latest
- 🔄 Deploy if accuracy ≥ 80%

### Ongoing: DAILY DRIVER Operations
- **Every morning 9am**: Run daily digest script, check for new releases
- **Within 4 hours**: Benchmark critical releases (llama4, gpt-4-local)
- **Within 24 hours**: Benchmark major releases (new model families)
- **Same day**: Emergency swap if critical bug fix or security issue
- **Continuous**: Monitor production metrics (accuracy, speed, RAM)
- **Weekly**: Fine-tuning dataset refresh (add new papers, update labels)
- **Monthly**: Full model registry audit, deprecate old models

---

## Monitoring Dashboard

**Metrics to Track** (stored in SurrealDB `model_performance` table):

```sql
-- Model performance tracking schema
CREATE TABLE model_performance SCHEMAFULL;
DEFINE FIELD model_name ON model_performance TYPE string;
DEFINE FIELD version ON model_performance TYPE string;
DEFINE FIELD task ON model_performance TYPE string;  -- "gap_analysis", "embeddings", etc.
DEFINE FIELD accuracy ON model_performance TYPE float;
DEFINE FIELD speed_ms ON model_performance TYPE float;
DEFINE FIELD ram_mb ON model_performance TYPE int;
DEFINE FIELD timestamp ON model_performance TYPE datetime;

-- Example query: Compare models over time
SELECT model_name, version, accuracy, speed_ms
FROM model_performance
WHERE task = 'gap_analysis'
ORDER BY timestamp DESC
LIMIT 10;
```

**Weekly Report** (auto-generated):
```markdown
# Model Performance Report - Week of 2026-02-16

## Current Production Models
- **Gap Analysis**: qwen2.5:14b (75% accuracy, 1.8s avg)
- **Embeddings**: nomic-embed-text v1.5 (0.85 correlation)
- **Quick Inference**: mistral:7b (68% accuracy, 450ms avg)

## Models Under Test
- **phi-4:14b**: Accuracy 77% (+2% vs qwen) - **RECOMMEND SWAP**
- **gemma-2:9b**: Accuracy 71% (-4% vs qwen) - Reject

## Recommended Actions
1. ✅ Swap qwen2.5:14b → phi-4:14b (2% accuracy gain)
2. ⏳ Begin fine-tuning phi-4 on COHEZION dataset
3. ⏳ Monitor phi-4 production for 7 days

## Upcoming Releases
- llama3.3:8b (expected Feb 28) - Meta claims 10% speedup
- mistral-small-2 (expected March 15) - Mistral claims better reasoning
```

---

## Integration with AI Features Specialist

**Division of Responsibilities**:

| Responsibility | Model Wrangler | AI Features Specialist |
|----------------|---------------|------------------------|
| **Model Selection** | ✅ Benchmark & recommend | Uses recommended models |
| **Model Swapping** | ✅ Execute swaps | Validates functionality after swap |
| **Fine-Tuning** | ✅ Generate dataset & train | Provides training examples |
| **Monitoring** | ✅ Track performance metrics | Reports accuracy issues |
| **Algorithm Design** | Uses models | ✅ Designs gap analysis algorithms |
| **Integration** | Provides API | ✅ Integrates into plugin |

**Collaboration Flow**:
1. **AI Features Specialist**: "Gap analysis accuracy dropped to 65%"
2. **Model Wrangler**: Benchmarks new candidates, finds phi-4:14b with 77% accuracy
3. **Model Wrangler**: Swaps model, validates integration
4. **AI Features Specialist**: Confirms gap analysis working correctly
5. **Model Wrangler**: Monitors for 7 days, documents swap

---

## Rollback Procedures

**When to Rollback**:
- Accuracy drop > 5% in production
- Speed regression > 50%
- Critical bugs (crashes, infinite loops, etc.)
- User complaints about quality

**Rollback Steps**:
```bash
# 1. Stop using new model
ollama stop phi-4:14b

# 2. Switch back to previous model in config
sed -i 's/phi-4:14b/qwen2.5:14b/g' ai_config.yaml

# 3. Restart services
systemctl restart cloud-vault-mcp

# 4. Verify rollback
python test_gap_analysis.py --model qwen2.5:14b

# 5. Document incident
echo "Rollback: phi-4 → qwen due to accuracy drop" >> rollback_log.txt
```

**Rollback Time Target**: < 5 minutes

---

## Cost Analysis

**Local LLM Management Costs**:

| Activity | Frequency | Time Investment | Value |
|----------|-----------|-----------------|-------|
| **Weekly monitoring** | 52x/year | 1 hour/week | Stay current with releases |
| **Benchmarking new models** | ~10x/year | 2 hours/model | Ensure optimal performance |
| **Model swapping** | ~4x/year | 1 hour/swap | Performance improvements |
| **Fine-tuning** | 4x/year | 4 hours/session | COHEZION-specific optimization |
| **Total annual** | - | ~100 hours | Continuous optimization |

**ROI**:
- Without model management: Stuck with initial models, gradual accuracy decay
- With model management: 10-20% accuracy improvements over time, 2-3x speed gains as models evolve
- Value: Maintain competitive edge, avoid costly Claude API fallbacks

---

## Tools & Automation

### Automated Benchmarking Script
```python
# /home/mike-anderson/dev/cohezion/cloud-vault-mcp/scripts/benchmark_model.py

import ollama
import json
from pathlib import Path

def auto_benchmark(model_name: str):
    """Automatically benchmark a new model against COHEZION test suite"""

    results = {
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "benchmarks": {}
    }

    # Load test datasets
    gap_analysis_tests = load_test_data("gap_analysis_test.json")
    embedding_tests = load_test_data("embedding_test.json")
    affinity_tests = load_test_data("affinity_test.json")

    # Run benchmarks
    print(f"Benchmarking {model_name}...")

    results["benchmarks"]["gap_analysis"] = run_gap_analysis_bench(model_name, gap_analysis_tests)
    results["benchmarks"]["embeddings"] = run_embedding_bench(model_name, embedding_tests)
    results["benchmarks"]["affinity"] = run_affinity_bench(model_name, affinity_tests)

    # Save results
    output_file = f"benchmarks/{model_name.replace(':', '_')}.json"
    Path(output_file).write_text(json.dumps(results, indent=2))

    print(f"✅ Benchmark complete: {output_file}")

    # Auto-recommendation
    current_model = load_current_production_model()
    if should_swap_model(current_model, model_name):
        print(f"🔄 RECOMMENDATION: Swap {current_model} → {model_name}")
        print(f"   Run: python swap_model.py --from {current_model} --to {model_name}")

# Usage
if __name__ == "__main__":
    auto_benchmark("phi-4:14b")
```

### Model Swap Automation
```bash
#!/bin/bash
# swap_model.sh - Automated model swapping with rollback

OLD_MODEL=$1
NEW_MODEL=$2

echo "🔄 Swapping $OLD_MODEL → $NEW_MODEL"

# 1. Pull new model if not present
ollama pull $NEW_MODEL

# 2. Test new model on sample data
python test_integration.py --model $NEW_MODEL
if [ $? -ne 0 ]; then
    echo "❌ Integration test failed, aborting swap"
    exit 1
fi

# 3. Backup current config
cp ai_config.yaml ai_config.yaml.backup

# 4. Update config
sed -i "s/$OLD_MODEL/$NEW_MODEL/g" ai_config.yaml

# 5. Restart services
systemctl restart cloud-vault-mcp

# 6. Monitor for 60 seconds
sleep 60
python health_check.py
if [ $? -ne 0 ]; then
    echo "❌ Health check failed, rolling back"
    cp ai_config.yaml.backup ai_config.yaml
    systemctl restart cloud-vault-mcp
    exit 1
fi

echo "✅ Swap complete: $OLD_MODEL → $NEW_MODEL"
echo "   Monitor production for next 24 hours"
echo "   Rollback command: ./swap_model.sh $NEW_MODEL $OLD_MODEL"
```

---

## Success Criteria

**Model Wrangler is successful if**:

- ✅ Production models maintain ≥ 70% accuracy on COHEZION benchmarks
- ✅ Average inference speed stays < 2s for real-time tasks
- ✅ At least 2 model swaps per year (keeping up with ecosystem)
- ✅ Fine-tuned models achieve ≥ 80% accuracy (10% improvement over base)
- ✅ Zero production incidents due to bad model swaps (rollback procedures work)
- ✅ Weekly monitoring reports published on time

---

## Conclusion

**Model Wrangler ensures**:
- 🔄 Continuous performance optimization
- 📊 Data-driven model selection
- 🎯 COHEZION-specific fine-tuning
- 🚀 Quick adoption of breakthrough models
- 🛡️ Production stability via rigorous testing

**Result**: Local LLM infrastructure that evolves with the ecosystem, maintaining competitive performance while keeping costs at $0/month.

---

**Status**: Proposed role for 12D Graph project
**Next**: Add Model Wrangler to specialist team (Specialist #6)
**Related**: [[2026-02-09-ai-model-strategy]], [[2026-02-09-12d-graph-refined-plan]]
