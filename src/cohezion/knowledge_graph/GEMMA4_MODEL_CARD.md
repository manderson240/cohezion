# Gemma 4 Model Card (Cohezion Grounding)

## Technical Specifications
- **Architecture**: Multimodal family with Dense and Mixture-of-Experts (MoE) variants.
- **Attention Mechanism**: Hybrid attention (Global + Sliding Window).
- **Context Window**: Up to 256K tokens.
- **Thinking Mode**: Configurable step-by-step reasoning support.
- **Per-Layer Embeddings (PLE)**: Native support for on-device efficiency.
- **Modality Support**: Text, Image, Video (all variants); Native Audio (E2B and E4B).

## Usage Patterns for Cohezion
- **Thinking Mode**: To be utilized by `EcoResilienceAgent` for complex synthesis of TEK and HIHO Physics.
- **Context Handling**: 256K window allows for massive historical trajectory analysis and multi-source grounding (NOAA + Copernicus).
- **On-Device Optimization**: PLE should be leveraged when running on local AMD/Blackwell hardware.

## Safety & Principles
- Rigorous CSAM and sensitive data filtering.
- Evaluated against Google's AI principles.

---
*Source: https://ai.google.dev/gemma/docs/core/model_card_4*
*Date Grounded: April 5, 2026*
