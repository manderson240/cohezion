## Codebase Patterns
- FLUME tests use class-based pytest style with direct imports from `cohezion.flume.*`
- Global pytest timeout is **10s** (`setup.cfg addopts = --timeout=10`). Subprocess tests need `@pytest.mark.timeout(N)` to override.
- Integration tests that call subprocesses should use `--load-data` with pre-made hash embeddings (not Ollama) to avoid ~60s Ollama cold-start latency per subprocess.
- `build_parser()` functions in CLI scripts allow clean import by tests without running `main()`.
- The FLUME VAE v2 API lives in `cohezion.flume.{vae, train_vae, evaluate_vae, data_pipeline, embedding_provider}` — distinct from the old v1 API in `cohezion.flume.training`.
- `create_embedding_provider(require_ollama=False)` gracefully falls back to 256D hash embeddings when Ollama is unavailable.
- `FlumeVAE(input_dim=..., latent_dim=256)` — input_dim comes from embeddings.shape[1], not hardcoded.

---

## 2026-02-24 - US-001
- Rewrote `scripts/train_flume.py` using FLUME v2 API (VAETrainer, FlumeVAE, TrainingDataPipeline, VAEEvaluator)
- Added all required flags: `--epochs`, `--batch-size`, `--lr`, `--n-samples`, `--evaluate`, `--checkpoint-dir`, `--require-ollama`, `--save-data`, `--load-data`, `--load-checkpoint`
- `--epochs 0` skips training; exit code 0/1; evaluation writes `evaluation_results.json`
- Created `tests/flume/test_cli_train.py`: 27 tests (19 argument parsing + 8 integration)
- Integration tests use `--load-data` with pre-made 256D hash embeddings to avoid Ollama latency in subprocess tests
- **Files changed**: `scripts/train_flume.py`, `tests/flume/test_cli_train.py`, `.chief/prds/main/prd.json`
- **Learnings for future iterations:**
  - Global 10s pytest timeout breaks subprocess tests; use `@pytest.mark.timeout(60)` on integration test classes
  - Ollama embedding via subprocess takes 60–120s per call (model loading + inference); always use `--load-data` in tests
  - `build_parser()` exposed at module level makes tests clean: `importlib.util.spec_from_file_location` + `mod.build_parser()`
  - `--load-data` + `--save-data` can test the save path without triggering Ollama
  - 185 FLUME tests now collected (158 pre-existing + 27 new)
---
