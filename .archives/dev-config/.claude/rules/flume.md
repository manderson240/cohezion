---
paths:
  - "src/cohezion/flume/**"
---

# FLUME Module Rules

- FLUME = Fluid Latent Understanding through Manifold Encoding (256D latent space)
- `autoencoder.py` contains single `FlumeEncoder` class (line 155) — duplicate class bug has been resolved
- `morphospace.py`, `bioelectric.py`, and `lcsp.py` implement the manifold geometry — changes here affect the entire encoding pipeline
- `predictor.py` handles latent-space prediction — keep it decoupled from the encoder/decoder
- All FLUME operations should be batch-friendly for token efficiency
- FLUME is a PRIME skill hub (`FLUME_METHODOLOGY`) — changes here have high compound impact across the system
- `git_encoder.py` wraps FlumeEncoder for analyzing git commit sequences
- `vliw_latent_alignment.py` uses FlumeEncoder for VLIW (Very Long Instruction Word) latent alignment
