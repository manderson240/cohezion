# Specification: BirdCLEF 2026

## Objective
Develop a high-performance bioacoustic monitoring system to identify bird species in audio recordings, leveraging the Cohezion swarm and audio processing capabilities.

## Requirements
- Identify 100+ bird species from short audio clips.
- Handle noisy environmental data (rain, wind, other animals).
- Optimize for inference speed on Kaggle's submission environment.
- Integrate with Cohezion's latent manifold for feature extraction.

## Technical Stack
- Python 3.11 (uv)
- PyTorch / Torchaudio
- Cohezion Swarm (Multi-agent ensemble)
- FastMCP for audio processing tools
