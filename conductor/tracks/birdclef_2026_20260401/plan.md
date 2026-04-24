# Implementation Plan: BirdCLEF 2026: Bioacoustic Monitoring Challenge

## Objective
Initialize Phase 1 (Research & Setup) for the BirdCLEF 2026 Kaggle competition. This involves comprehensive literature review, dataset acquisition, baseline model identification, and local environment setup using our 30h/week heavy training quota. We will rigorously follow the Systems Engineering V-Model to ensure a deterministic, reproducible baseline.

## V-Model Lifecycle Mapping
- **Phase 1 (The Thinker)**: Descending (Latent) - Requirements, Architecture, Dataset Acquisition, and AutoHarness Design.
- **Phase 2 & 3 (The Doer)**: Apex - TDD Implementation, Baseline Training, and Submission Wiring.
- **Phase 4 (The Knower)**: Ascending (Axiomatic) - System Validation, Key Learning Extraction, and Leaderboard Submission.

## Compound Engineering Principles
- **Foundational Primitives**: Establish deterministic AutoHarnesses for data loading and baseline evaluation.
- **Automated Skill Extraction**: Capture insights into audio processing and spectrogram generation into the Knowledge Vault.
- **Hermetic Persistence**: Log all research findings and training metrics to SurrealDB and Obsidian.

---

## Phase 1: The Thinker (Descending - Design & Architecture)
- Task: Look Outward (SOTA Research & Discovery)
    - [x] Activate `huggingface-papers` and query arXiv for recent breakthroughs in "Bioacoustic Monitoring", "BirdNET", and "Audio Transformers".
    - [x] Search the Hugging Face Hub (`hf-cli`) for relevant pre-trained audio classification models and existing BirdCLEF datasets.
    - [x] Use GitHub (via `google_web_search` or direct tools) to review winning solutions from BirdCLEF 2025 and 2024 to identify robust audio processing pipelines (e.g., `librosa`, `audiomentations`).
- Task: Kaggle Setup & Data Acquisition
    - [x] Activate the `kaggle` skill.
    - [x] Run `python3 shared/check_all_credentials.py` to verify Kaggle API access.
    - [x] Use `kaggle competitions download -c birdclef-2026` to acquire the dataset.
    - [x] Generate a competition landscape report using the `comp-report` module to understand the evaluation metric (e.g., macro-averaged ROC-AUC).
- Task: Define Schema & AutoHarness
    - [x] Synthesize a deterministic AutoHarness for the audio data loader, ensuring consistent spectrogram generation.
    - [x] Define the submission format (multi-column species probability) and validation schema (Macro-averaged ROC-AUC aligned).
    - [ ] Integrate Google Perch v2 for 1536-D embedding extraction as the core baseline backbone.
- Task: Incorporate ARC Lessons & V-Model
    - [x] Plan to orchestrate local SLMs for internal audits of our data processing pipeline, minimizing cloud token usage.
    - [x] Ensure the pipeline captures experiential learning via our newly validated git hook.

## Phase 2: The Doer (Apex - Core Implementation)
- Task: TDD Red Phase
    - [x] Write failing tests for audio loading, augmentation, and model forward pass.
- Task: Baseline Implementation (Local Quota)
    - [x] Implement a baseline CNN or Audio Spectrogram Transformer (AST) training script.
    - [x] Configure training loop to utilize the local 30h/week heavy GPU quota.
- Task: Competition Wiring
    - [x] Implement the Kaggle inference/submission notebook structure.

## Phase 3: The Doer (Apex - Persistence & Healing)
- Task: Telemetry & Logging
    - [~] Wire training metrics (loss, val_auc) into the `TelemetryBus` for storage in SurrealDB.
    - [~] Configure `Ouroboros` to monitor training divergence.

## Phase 4: The Knower (Ascending - Validation & Persistence)
- Task: System Validation
    - [ ] Execute a full local training and validation run on a small subset of the data.
    - [ ] Verify the generated submission `.csv` format against the competition schema.
- Task: Document & Extract
    - [ ] Perform a Journey Retrospective, extracting "Key Learnings" about the BirdCLEF data to the Knowledge Vault.
    - [ ] Transition to Phase 2 (Optimization).