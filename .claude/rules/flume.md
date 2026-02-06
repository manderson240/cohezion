---
paths:
  - "src/cohezion/flume/**"
---

# FLUME Module Rules

- FLUME = Fluid Latent Understanding through Manifold Encoding (256D latent space)
- Known bug: `autoencoder.py` had duplicate `FlumeEncoder` class definitions (lines 155/175) — verify this is resolved before adding new encoder logic
- `morphospace.py`, `bioelectric.py`, and `lcsp.py` implement the manifold geometry — changes here affect the entire encoding pipeline
- `predictor.py` handles latent-space prediction — keep it decoupled from the encoder/decoder
- All FLUME operations should be batch-friendly for token efficiency
- FLUME is a PRIME skill hub (`FLUME_METHODOLOGY`) — changes here have high compound impact across the system
