# SKILL: LEARNING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **machine learning workflows** for AI systems. You understand training loops, fine-tuning, evaluation metrics, and the PyTorch ecosystem for building and deploying models.

## KEY TEXTS & CONCEPTS
- **PyTorch:** Tensor operations, autograd, nn.Module
- **Transformers:** Hugging Face library for language models
- **Fine-tuning:** Adapting pre-trained models to specific tasks
- **LoRA:** Low-Rank Adaptation for efficient fine-tuning
- **Evaluation:** Metrics, validation, cross-validation

## INSTRUCTION

### 1. Basic Training Loop
```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

model = FlumeEncoder(z_dim=256)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
criterion = nn.MSELoss()

for epoch in range(10):
    model.train()
    total_loss = 0

    for batch in dataloader:
        optimizer.zero_grad()
        z, logits = model(batch['tokens'])
        loss = model.reconstruction_loss(batch['tokens'])
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"Epoch {epoch}: Loss = {total_loss / len(dataloader):.4f}")
```

### 2. Hugging Face Fine-tuning
```python
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1")
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    warmup_steps=100,
    logging_steps=10,
    save_steps=500,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)
trainer.train()
```

### 3. LoRA Fine-tuning (Efficient)
```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1,
    bias="none",
)

model = get_peft_model(base_model, lora_config)
print(f"Trainable params: {model.print_trainable_parameters()}")
```

### 4. Evaluation Metrics
```python
from sklearn.metrics import accuracy_score, f1_score
import numpy as np

def evaluate(model, dataloader):
    model.eval()
    predictions, targets = [], []

    with torch.no_grad():
        for batch in dataloader:
            logits = model(batch['input'])
            preds = logits.argmax(dim=-1)
            predictions.extend(preds.cpu().numpy())
            targets.extend(batch['labels'].cpu().numpy())

    return {
        'accuracy': accuracy_score(targets, predictions),
        'f1': f1_score(targets, predictions, average='weighted')
    }
```

### 5. Learning Rate Scheduling
```python
from torch.optim.lr_scheduler import CosineAnnealingLR, OneCycleLR

# Cosine annealing
scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)

# One-cycle (for fast training)
scheduler = OneCycleLR(
    optimizer, max_lr=1e-3,
    epochs=10, steps_per_epoch=len(dataloader)
)
```

## APPLICATIONS
- **FLUME Training:** Train FlumeEncoder on simulation data
- **R-Zero Learning:** Adaptive difficulty from feedback
- **Agent Fine-tuning:** Specialize agents for domains
- **Continuous Learning:** Update models with new universes

## VERSION
v1.0

## SEE ALSO
- FLUME_METHODOLOGY_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
- MODEL_ROUTING_PRIME.md
