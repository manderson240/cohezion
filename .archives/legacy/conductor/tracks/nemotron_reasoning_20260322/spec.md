# Specification: NVIDIA Nemotron Model Reasoning Challenge

## Overview
This track focuses on competing in the Kaggle "NVIDIA Nemotron Model Reasoning Challenge". The goal is to improve the structured reasoning accuracy of the `Nemotron-3-Nano-30B-A3B` model on a novel benchmark developed by NVIDIA Research. 

## Competitive Research & Constraints
- **Submission Format**: Participants must submit a **LoRA (Low-Rank Adaptation) adapter** compatible with the base model, including an `adapter_config.json`.
- **Evaluation**: Accuracy is measured by the model's ability to solve tasks and place the final answer within a LaTeX `\boxed{}` command using the vLLM inference engine.
- **Submission Limits**: Strictly limited to **5 submissions per day**.
- **Licensing**: Winning models must be open-sourced under the **CC BY 4.0** license. External data/tools must be "reasonably accessible" at minimal cost.
- **Reproduction**: Winners must provide code and environment descriptions capable of fully reproducing their results.

## Hardware Strategy
- **Local (AMD Orchestration)**: Local AMD hardware (128GB RAM, RX 7700S) will be used for dataset curation, FLUME VAE embeddings, script generation, and utilizing local SLMs via Ollama for data preprocessing.
- **Kaggle (GPU/TPU Execution)**: The actual LoRA fine-tuning of the 30B parameter model will be offloaded to Kaggle Notebooks. Kaggle provisions Google Cloud G4 VMs automatically and for free within their environment. We will use the Kaggle API to push jobs from our local machine to these VMs.

## Functional Requirements
1. **Kaggle API Integration**: Automate the downloading of datasets and pushing local training scripts/data to Kaggle Notebooks via the API. *(Note: This can be shared with the AIMO track).*
2. **LoRA Fine-tuning Pipeline**: Develop a training script (to be executed on Kaggle) to fine-tune the `Nemotron-3-Nano-30B-A3B` model using LoRA.
3. **Local Evaluation Suite**: Build a local testbed to measure reasoning accuracy on smaller subset data or quantized models, ensuring outputs are properly formatted with the LaTeX `\boxed{}` command.
4. **FLUME Integration**: Utilize Cohezion's FLUME VAE locally to encode the problem space, curate datasets, or generate synthetic data to feed into the fine-tuning process.

## Non-Functional Requirements
- **Resource Constraints**: The training scripts must be optimized to run within the memory limits of Kaggle's provided hardware.
- **Dependency Management**: Ensure compatibility with required libraries such as `mamba_ssm` (as noted in competition guidelines) within the Kaggle environment.
- **Traceability**: All experiments and models must be tracked via Cohezion's tracking systems locally.

## Acceptance Criteria
- [ ] Kaggle API is integrated to fetch data and push scripts/notebooks.
- [ ] A local evaluation suite can successfully run and evaluate outputs using the `\boxed{}` metric.
- [ ] A baseline LoRA training script is written locally and successfully executed on Kaggle's hardware.
- [ ] The resulting LoRA adapter (`adapter_config.json` + weights) is successfully submitted to the competition.
- [ ] FLUME VAE is integrated into the local data curation pipeline.

## Out of Scope
- Full parameter fine-tuning of the 30B model.
- Local training of the 30B model (training is strictly offloaded to Kaggle).