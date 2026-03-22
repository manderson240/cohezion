# Cohezion Local Model Finetuning - Updated Strategy

## Learnings So Far

### Learning #1: ROCm Not Installed
- AMD GPU present (`renderD128`) but ROCm drivers not installed
- Cannot use PyTorch with AMD GPU acceleration
- Default PyTorch has CUDA 12.8 (won't work on AMD)

### Learning #2: CPU Training Impractical for 8B Models
- Qwen3-8B too large for CPU-only QLoRA
- Would take many hours/days
- Need GPU for tractable training

### Learning #3: Modelfile Approach Works
- Ollama Modelfiles create soft finetuning via system prompts
- `cohezion_v1` (phi3:mini) and `cohezion_v2` (qwen3:8b) deployed
- Quick iteration, practical for current setup

## Updated Strategy

### Phase 1: Rapid Iteration (Current)
Use Modelfiles for quick soft-finetuning:
- Generate more journey data → Update Modelfile → Redeploy
- Cycle time: minutes
- Works on current setup

### Phase 2: Collect More Experiences
Run agent simulations to gather real journey data:
- Target: 500+ high-quality journeys
- Each journey = one training example
- Quality filter: phi_score ≥ 0.7

### Phase 3: GPU-Enabled Training (Future)
When GPU available:
- Install ROCm drivers
- Full QLoRA with LlamaFactory
- True weight updates

## Immediate Actions

1. Generate more journey data via agent runs
2. Update Modelfile with new patterns
3. Redeploy model
4. Test and measure improvement

## Files

- Pipeline: `src/cohezion/flume/journey_finetune_pipeline.py`
- Modelfile v2: `data/models/cohezion_v2/Modelfile`
- Training data: `data/training/finetune_journeys.jsonl`
- LlamaFactory: `~/LlamaFactory` (ready for GPU)
