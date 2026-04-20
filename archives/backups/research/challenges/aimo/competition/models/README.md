# AIMO3 Models Gallery

> **Source**: https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/models  
> **Last Updated**: 2026-04-07 22:10 UTC

---

## Back Links

← [Back to Competition Index](../README.md) | [Submissions](../submissions/README.md) | [Leaderboard](../leaderboard/README.md)

---

## Popular Models Used in Competition

### Top Performing Models

| Model | Framework | Users | Best Public Score | Notes |
|-------|-----------|-------|-------------------|-------|
| **Unsloth AI** | Transformers | 153 | **44** | Highest usage, strong performance |
| **Qwen 3 30b-a3b-thinking** | Transformers | 17 | 23 | Latest Qwen3 series |
| **Tong Hui Kang** | Transformers | 8 | **42** | Custom approach |
| **DeepSeek R1 0528** | Transformers | 5 | **42** | Reasoning-first model |

---

## Model Categories

### 1. Qwen Series (Alibaba)

| Model | Parameters | Usage | Best Score |
|-------|------------|-------|------------|
| Qwen 3 30b-a3b-thinking | 30B | 17 users | 23 |
| Qwen2.5 Math 7b-instruct | 7B | 6 users | N/A |
| Qwen2.5 Math 72b-instruct | 72B | 3 users | N/A |
| Qwen2.5 | Various | 3 users | N/A |

**Description**: Qwen3 is the latest generation of large language models in Qwen series, offering a comprehensive suite of dense and mixture-of-experts (MoE) models.

---

### 2. DeepSeek Series

| Model | Parameters | Usage | Best Score |
|-------|------------|-------|------------|
| DeepSeek R1 0528 | 8B (distilled) | 5 users | **42** |
| DeepSeek R1 distill Qwen 7b | 7B | 5 users | N/A |
| DeepSeek R1 distill Qwen 14b | 14B | 3 users | 1 |
| DeepSeek Math 7b-instruct | 7B | 7 users | N/A |

**Description**: DeepSeek-R1-0528 model is unique for its "reasoning-first" approach, achieved through extensive reinforcement learning which allows it to naturally explore complex problem-solving chains of thought. DeepSeek Math focuses on pushing the limits of mathematical reasoning in open language models.

---

### 3. Gemma Series (Google)

| Model | Parameters | Usage | Best Score |
|-------|------------|-------|------------|
| Gemma 3 variants | Various | Multiple | Various |

---

### 4. Other Notable Models

| Model | Owner | Framework | Users | Best Score |
|-------|-------|-----------|-------|------------|
| ShelterW variants | ShelterW | Transformers | Various | 25-36 |
| Nguyen | Nguyen | Transformers | 6 | 34 |
| Lewis Tunstall | Lewis Tunstall | Transformers | 4 | N/A |

---

## Model Performance Analysis

### By Best Score Achieved

| Score | Models | Users |
|-------|--------|-------|
| **44** | Unsloth AI variants | 153 |
| **42** | DeepSeek R1 0528, Tong Hui Kang | 13 total |
| **36** | ShelterW variants | 6 |
| **34** | ShelterW, Nguyen | 10 |
| **33** | Unsloth AI | 15 |
| **25** | ShelterW | 9 |
| **23** | Qwen 3 30b | 17 |
| **1-22** | Various | Multiple |

### Key Insights

1. **Unsloth AI dominance**: 153 users, best score 44 — likely fine-tuned or optimized base
2. **DeepSeek R1 strong**: Reasoning-first approach shows promise (42 score)
3. **Qwen3 underperforming**: Despite being latest, only achieving 23 — may need tuning
4. **Smaller models competitive**: DeepSeek 8B matches larger models

---

## My Local Models (Available)

From `ollama list`:

| Model | Parameters | Quantization | Potential for AIMO3 |
|-------|------------|--------------|---------------------|
| qwen3-coder:30b | 30.5B | Q4_K_M | ✅ Strong candidate |
| deepseek-r1:7b | 7.6B | Q4_0 | ✅ Good for reasoning |
| qwen2-math:7b | 7.6B | Q4_0 | ✅ Math specialized |
| qwen2-math:1.5b | 1.5B | Q4_0 | ⚠️ May be too small |
| gemma4:31b | 31.3B | Q4_K_M | ✅ Good candidate |
| deepcoder:14b | 14.8B | Q4_K_M | ✅ Code/math hybrid |
| holo3-35b | 34.7B | Q4_K_M | ✅ Strong candidate |
| phi4:latest | 14.7B | Q4_K_M | ⚠️ General purpose |

---

## Recommended Model Strategy

### Tier 1: Primary Candidates
1. **qwen3-coder:30b** — Latest, best performance
2. **deepseek-r1:7b** — Reasoning specialized
3. **holo3-35b** — Strong overall capability

### Tier 2: Secondary/Backup
1. **qwen2-math:7b** — Math specialized
2. **deepcoder:14b** — Code/math hybrid
3. **gemma4:31b** — General strong performer

### Ensemble Approach
- Run multiple models
- Use voting/consensus
- Weight by confidence scores

---

## External Links

- [Models on Kaggle](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/models)
- [Competition Overview](../docs/OVERVIEW.md)
- [My Submissions](../submissions/README.md)

---

← [Back to Competition Index](../README.md)
