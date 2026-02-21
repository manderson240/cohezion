# Session 57: Local Model Finetuning Pipeline

## Date: 2026-02-21

## Hypothesis
Agentic experiences (journeys) can be collected and used to finetune local models, creating a closed-loop improvement system.

## Method
1. Created journey-to-finetune pipeline
2. Deployed Ollama Modelfiles for soft finetuning (cohezion_v1, cohezion_v2)
3. Installed LlamaFactory for full QLoRA training
4. Attempted ROCm installation for AMD GPU

## Results

### What Worked
- Ollama Modelfile approach: Creates soft finetuning via system prompts
- Journey data converted to JSONL training format
- cohezion_v1 (phi3:mini, 2.2GB) and cohezion_v2 (qwen3:8b, 5.2GB) deployed

### What Failed
- ROCm not installed on system - AMD GPU present but inaccessible
- CPU training impractical for 8B models

## Learnings
1. **ROCm needs sudo**: Cannot install without interactive terminal
2. **Python version matters**: ROCm PyTorch only supports Python 3.8-3.12
3. **Modelfile is practical fallback**: Quick iteration without GPU
4. **Never parse SUDO_PASSWORD from .env**: Security violation

## Next Steps
1. Install ROCm manually (needs user interaction)
2. Collect more journey data (target: 500+)
3. Run full QLoRA training when GPU available
