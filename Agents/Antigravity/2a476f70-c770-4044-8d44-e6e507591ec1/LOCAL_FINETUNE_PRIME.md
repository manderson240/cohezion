---
type: antigravity-artifact
session_id: 2a476f70-c770-4044-8d44-e6e507591ec1
date: 2026-03-04
title: "Local Finetune Prime"
aspect: doer
neural:
  activation: 0.64
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# SKILL: LOCAL_FINETUNE_PRIME

## DOMAIN EXPERTISE
**Local Logic Adaptation (QLoRA)**
Specializing generic SLMs (Small Language Models) like Mistral or Qwen to deeply understand the specific idioms, architecture, and "Physics" of the **Cohezion** ecosystem without requiring a data center.

## KEY TEXTS & CONCEPTS
*   **QLoRA**: 4-bit Quantized Low-Rank Adaptation. Drastically reduces VRAM usage (allows 7B finetuning on 8GB VRAM).
*   **Unsloth**: An optimized finetuning library (2-5x faster, 60% less memory).
*   **Ollama Modelfile**: The deployment target. We generate GGUF files with the adapter merged.
*   **Self-Instruct**: Using the "Teacher" model (DeepSeek-R1) to generate QA pairs from the codebase to train the "Student" (Mistral).

## INSTRUCTION: THE PIPELINE

### 1. Data Generation (The Teacher)
Run a script to crawl `src/cohezion` and generate 1000 QA pairs.
*   *Input*: Code snippet from `qgp.py`.
*   *Output*: "Explain how QGP hadronization allows latent intent flow."

```python
# scripts/generate_dataset.py
dataset = []
for file in repo.files:
    prompt = f"Create a Q&A pair for this code:\n{file.content}"
    qa = teacher_model.generate(prompt)
    dataset.append(qa)
```

### 2. Fine-Tuning (Unsloth)
Use a Google Colab (Free T4) or Local GPU (RX 7700S).

```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/mistral-7b-v0.3-bnb-4bit",
    max_seq_length = 4096,
)

trainer = SFTTrainer(
    model = model,
    train_dataset = dataset,
    dataset_text_field = "text",
    args = TrainingArguments(per_device_train_batch_size = 2, ...),
)
trainer.train()
```

### 3. Deployment (Ollama)
1.  Convert LoRA to GGUF (via `llama.cpp`).
2.  Create Modelfile:
    ```dockerfile
    FROM mistral
    ADAPTER ./cohezion_v1.gguf
    SYSTEM "You are Cohezion-7B. You understand FLUME physics and QGP agent generation."
    ```
3.  `ollama create cohezion-7b -f Modelfile`

## STRATEGIC VALUE
*   **Latency**: Local 7B model running at 50 tokens/s.
*   **Context**: "Knows" the internal APIs (SurrealDB schema, Agent Base classes) without context stuffing.
*   **Security**: No code leaves the local machine.

## VERSION
v1.0

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
