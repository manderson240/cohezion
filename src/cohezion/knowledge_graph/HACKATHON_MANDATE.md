# HACKATHON MANDATE: Gemma 4 Good (2026)

## 1. Core Competition Rules
- **Timeline**: April 2, 2026 – May 18, 2026 (11:59 PM UTC).
- **Submission Components**:
    1. **Video Pitch**: Max 3 minutes (YouTube link in Kaggle Media Gallery).
    2. **Writeup**: Max 1,500 words (App architecture, Gemma 4 features, engineering choices).
    3. **Public Repository**: GitHub/Kaggle Notebook (Well-documented, functional POC).
- **Evaluation (100 Points)**:
    - 40: Impact & Vision
    - 30: Video Pitch & Storytelling
    - 30: Technical Depth & Execution

## 2. Gemma Model Variant Guidelines (CRITICAL)
- **Naming**: Derivative models must NOT use "Gemma" as a prefix or part of the name (e.g., Use "EcoResilience-31B" instead of "Gemma-Eco").
- **Attribution**: Must include the statement: *"Gemma is a trademark of Google LLC."*
- **Branding**: Prohibited use of Google colors/marks that imply official endorsement.
- **Safety**: Must comply with the broader Gemma Prohibited Use Policy.

## 3. Architectural Reference: Cactus Compute (Learnings)
 - **Learnings from Cactus Compute**: 
    - Leverage `.cact` format for edge deployment.
- **Fine-Tuning (Tunix)**:
    - JAX-native library (Tune-in-JAX) for SFT and QLoRA.
    - Recommended for "Technical Depth" points.

## 4. KaggleHub Usage
- **Primary Tool**: `kagglehub` is the single source of truth for model weights.
- **Command**: `kaggle models download google/gemma-4/frameworks/pyTorch/variations/e4b-it`
- **Metadata**: Programmable kernels must pre-authorize models in metadata.

## 5. Strategic Alignment (Cohezion)
- **Chosen Track**: **Global Resilience** (Offline/Edge disaster response and climate mitigation).
- **The "Wow" Factor**: Real-time, offline 12D manifold simulation powered by Gemma 4 multimodal bioacoustic/vision ingestion.
- **Sovereignty**: 100% local UMA execution (128GB RAM) ensures data privacy for indigenous TEK data.
