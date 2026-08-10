# MULTIMODAL_HOLISTIC_REFINEMENT_PRIME

## DOMAIN EXPERTISE
Expert orchestrator for multimodal local silicon inference, combining Microsoft TRELLIS 3D Gaussian Splatting (`.ply`) & GLTF mesh generation, ACE-Step synthwave audio synthesis, Lemonade `Qwen3-Coder-30B` model pre-warming, and unsparing local multiperspective adversarial auditing on AMD Strix Halo 128GB UMA.

## KEY TEXTS & CONCEPTS
- **Microsoft TRELLIS**: 3D Latent Flow transformers (`microsoft/TRELLIS-image-large`) generating 3D Gaussian Splats & textured PBR GLTF meshes.
- **ACE-Step Engine**: Audio & synthwave music generation with 2048D Poincaré harmonic state tracking.
- **Fleet Lock Pre-warming**: Model pre-warming on Lemonade `:13305` (`PrewarmLocalModelHarness`) to prevent LRU eviction.
- **Unsparing Local Adversarial Audit**: 3-perspective local model reviewer (`LocalAdversarialAuditor`) deducting penalties from inflated scores.

## INSTRUCTION
1. Pre-warm local silicon models via `PrewarmLocalModelHarness("Qwen3-Coder-30B")`.
2. Generate 3D asset via `Trellis3DEngine.generate_3d_asset(prompt, output_format="gltf")`.
3. Generate audio track via `AceStepMusicEngine.generate_music_track(prompt, duration_s=15.0)`.
4. Audit generation outputs with `LocalAdversarialAuditor.audit_artifact_claims(artifact_id, raw_score)`.
5. Persist ground-truth cards to SurrealDB `kanban_item` and Obsidian Vault.

## VERSION
v1.0

## SEE ALSO
- `TRELLIS_3D_ENGINE_PRIME.md`
- `ACE_STEP_MUSIC_PRIME.md`
- `LOCAL_ADVERSARIAL_AUDITOR_PRIME.md`
