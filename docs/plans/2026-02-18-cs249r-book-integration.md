# CS249R ML Systems Book Integration Plan

Created: 2026-02-18
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Ingest the full Harvard CS249R "Machine Learning Systems" textbook (https://github.com/harvard-edge/cs249r_book) into Cohezion's knowledge ecosystem: vault concepts, PRIME skills, and TinyTorch code integration.

**Architecture:** Three-layer integration pipeline:
1. **Knowledge Layer** - Clone repo, parse structured data (656 glossary terms, 21 concept maps, quizzes), create vault entries and SurrealDB-indexed concepts
2. **Skills Layer** - Create PRIME skill definitions from the book's 6 major topic areas (foundations, design, performance, deployment, trustworthy systems, frontiers)
3. **Code Layer** - Adapt TinyTorch's 20 from-scratch ML modules into Cohezion's codebase as `src/cohezion/tinytorch/`

**Tech Stack:** Python 3.13+, uv, SurrealDB, vault MCP tools, existing ingestion patterns

## Scope

### In Scope

- Clone `harvard-edge/cs249r_book` repo for local access
- Automated ingestion script to parse all chapter `*_concepts.yml`, `*_glossary.json`, and `*_quizzes.json` files
- Create vault concept notes for each of the 21 core chapters + 9 advanced chapters
- Ingest 656 glossary terms into vault as a searchable reference
- Create 8 new PRIME skills covering the book's major ML systems engineering topics
- Adapt TinyTorch's 20 progressive modules (tensor through capstone) into `src/cohezion/tinytorch/`
- Tests for the ingestion pipeline and TinyTorch integration

### Out of Scope

- Rendering the Quarto book itself (no book build toolchain)
- Importing bibliographies/citations (`.bib` files) - too large, low ROI
- Importing images/figures from chapters
- Modifying existing Cohezion PRIME skills
- Running TinyTorch training on real datasets (validation only)
- The `labs/` directory content (marked "Coming 2026")

## Prerequisites

- Git access to clone `harvard-edge/cs249r_book`
- SurrealDB running locally (ws://localhost:8000) for concept indexing
- Vault MCP server accessible for vault writes
- `uv` for Python package management

## Context for Implementer

> This section is critical for cross-session continuity.

- **Patterns to follow:**
  - Ingestion script: Follow `scripts/ingest_research.py` pattern (SurrealClient + KnowledgeMapper)
  - Vault concepts: Follow existing format in `/home/mike-anderson/vaults/cohezion-vault/concepts/` (markdown with frontmatter)
  - PRIME skills: Follow existing `src/cohezion/skills/*_PRIME.md` format (DOMAIN EXPERTISE, KEY TEXTS, INSTRUCTION sections)
  - Python modules: Follow `src/cohezion/` package conventions (type hints, `__init__.py`, async where needed)

- **Conventions:**
  - All vault concept files use kebab-case: `ml-systems-engineering.md`
  - PRIME skills use UPPER_SNAKE: `EFFICIENT_AI_PRIME.md`
  - Python modules use snake_case
  - Every `src/` directory must have `__init__.py`

- **Key files:**
  - `scripts/ingest_research.py` - Existing ingestion pattern
  - `src/cohezion/skills/RESEARCH_PATTERNS_PRIME.md` - Example PRIME skill
  - `/home/mike-anderson/vaults/cohezion-vault/concepts/` - Where vault concepts live
  - `tests/conftest.py` - Test isolation patterns

- **Gotchas:**
  - TinyTorch modules are Jupytext-formatted `.py` files (percent format with `# %%` cells) - need to extract pure Python
  - TinyTorch depends only on NumPy - keep this constraint, don't add PyTorch deps
  - Chapter concept files are YAML, glossary files are JSON - different parsers needed
  - Some chapters may have missing or empty concept/glossary files
  - The repo's default branch is `dev`, not `main`

- **Domain context:**
  - CS249R is Harvard's ML Systems course (Prof. Vijay Janapa Reddi)
  - Book covers 6 parts: Systems Foundations, Design Principles, Performance Engineering, Robust Deployment, Trustworthy Systems, Frontiers
  - TinyTorch is a from-scratch ML framework teaching implementation of tensor ops, autograd, transformers, quantization etc. using only NumPy
  - Book site: https://mlsysbook.ai/

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [ ] Task 1: Clone repository and set up data access
- [ ] Task 2: Build chapter knowledge ingestion script
- [ ] Task 3: Ingest glossary terms into vault
- [ ] Task 4: Create vault concept notes for all chapters
- [ ] Task 5: Create ML Systems Foundations PRIME skills
- [ ] Task 6: Create Performance & Deployment PRIME skills
- [ ] Task 7: Create Trustworthy Systems & Frontiers PRIME skills
- [ ] Task 8: Integrate TinyTorch core modules (01-09)
- [ ] Task 9: Integrate TinyTorch advanced modules (10-20)
- [ ] Task 10: End-to-end validation and SurrealDB indexing

**Total Tasks:** 10 | **Completed:** 0 | **Remaining:** 10

## Implementation Tasks

### Task 1: Clone Repository and Set Up Data Access

**Objective:** Clone the CS249R book repository locally and create a helper module that provides structured access to the book's data files (concepts, glossary, quizzes per chapter).

**Dependencies:** None

**Files:**
- Create: `scripts/cs249r/repo_access.py` - Helper to navigate the cloned repo structure
- Create: `scripts/cs249r/__init__.py`

**Key Decisions / Notes:**
- Clone to `/home/mike-anderson/dev/cs249r_book` (sibling to cohezion, not inside it). This is a TEMPORARY reference clone for ingestion; can be deleted after Task 10 verification
- Default branch is `dev` - clone that branch. Pin to specific commit hash for reproducibility
- The repo access module should enumerate all chapters and their associated data files (concepts YAML, glossary JSON, quizzes JSON)
- Each chapter directory follows pattern: `book/quarto/contents/core/<name>/` with `<name>_concepts.yml`, `<name>_glossary.json`, `<name>_quizzes.json`
- Advanced chapters follow: `book/quarto/contents/advanced/<name>/`
- **VALIDATION STEP**: After cloning, enumerate actual chapter count, glossary term count, and TinyTorch module count. If they differ from plan assumptions (21 core + 9 advanced chapters, ~656 glossary terms, 20 TinyTorch modules), update subsequent tasks accordingly
- TinyTorch source files are Jupytext percent-format. Test extraction regex `^# %%(?!\[markdown\])` on 2 sample modules before batch-processing

**Definition of Done:**
- [ ] Repository cloned to `/home/mike-anderson/dev/cs249r_book`
- [ ] `repo_access.py` can list all chapters (expected ~30: 21 core + 9 advanced) and prints actual count
- [ ] `repo_access.py` can load concepts YAML, glossary JSON, and quizzes JSON for any chapter
- [ ] Actual chapter count, glossary term count, and TinyTorch module count validated and logged
- [ ] All tests pass

**Verify:**
- `uv run pytest tests/cs249r/test_repo_access.py -q` - repo access tests pass
- `uv run python -c "from scripts.cs249r.repo_access import CS249RRepo; r = CS249RRepo(); print(f'Chapters: {len(r.chapters)}, Glossary: {r.glossary_term_count}, Modules: {len(r.tinytorch_modules)}')"` - prints actual counts

### Task 2: Build Chapter Knowledge Ingestion Script

**Objective:** Create an ingestion script that parses all chapter concept maps and writes vault-compatible markdown notes for each chapter, including primary concepts, secondary concepts, technical terms, methodologies, and applications.

**Dependencies:** Task 1

**Files:**
- Create: `scripts/cs249r/ingest_chapters.py` - Main ingestion script
- Create: `tests/cs249r/__init__.py`
- Create: `tests/cs249r/test_ingest_chapters.py`

**Key Decisions / Notes:**
- Each chapter's `*_concepts.yml` has structure: `concept_map.primary_concepts`, `secondary_concepts`, `technical_terms`, `methodologies`, `applications`
- Output vault concept notes to `/home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/` subdirectory (use absolute paths, not `~`)
- Each note follows vault format: YAML frontmatter (tags, source, chapter) + markdown body with concept lists
- **Vault tagging convention**: All CS249R concepts use tags: `[concept, ml-systems, cs249r, <domain>]` where domain is one of: `foundations`, `architectures`, `data-eng`, `performance`, `deployment`, `trustworthy`, `edge`. Follow existing vault frontmatter format
- Use direct file writes (faster than MCP for bulk)
- Handle missing/malformed concept files gracefully (log warning, skip)

**Definition of Done:**
- [ ] Script parses all available `*_concepts.yml` files from the repo
- [ ] Creates one vault concept note per chapter in `/home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/`
- [ ] Notes contain frontmatter with tags, source chapter, and date
- [ ] Notes contain structured sections for primary concepts, technical terms, methodologies
- [ ] Script handles missing concept files without crashing
- [ ] All tests pass

**Verify:**
- `uv run pytest tests/cs249r/test_ingest_chapters.py -q`
- `uv run python scripts/cs249r/ingest_chapters.py --dry-run` - lists chapters and concept counts without writing
- `ls /home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/ | wc -l` - shows ~30 files after real run

### Task 3: Ingest Glossary Terms into Vault

**Objective:** Parse the global glossary (656 terms) and per-chapter glossaries, then create a structured vault reference document and individual concept links.

**Dependencies:** Task 1

**Files:**
- Create: `scripts/cs249r/ingest_glossary.py` - Glossary ingestion script
- Create: `tests/cs249r/test_ingest_glossary.py`

**Key Decisions / Notes:**
- Global glossary at `book/quarto/contents/data/global_glossary.json` has 656 terms
- Per-chapter glossaries at `book/quarto/contents/core/<name>/<name>_glossary.json`
- Create a single comprehensive vault note: `/home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/ml-systems-glossary.md`
- Also create a SurrealDB-importable JSON for later indexing (Task 10)
- Terms should be cross-referenced with chapter concept notes via wiki-links
- Group terms by domain/category if the glossary data supports it

**Definition of Done:**
- [ ] Script parses global glossary JSON (656 terms)
- [ ] Script parses all per-chapter glossary files
- [ ] Creates comprehensive glossary vault note with all terms
- [ ] Creates `data/cs249r_glossary_surreal.json` for SurrealDB import
- [ ] Terms are cross-linked to chapter concept notes
- [ ] All tests pass

**Verify:**
- `uv run pytest tests/cs249r/test_ingest_glossary.py -q`
- `uv run python scripts/cs249r/ingest_glossary.py --dry-run` - reports term counts
- `wc -l /home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/ml-systems-glossary.md` - shows substantial content

### Task 4: Create Vault Concept Notes for All Chapters

**Objective:** Run the ingestion pipeline from Tasks 2-3 to actually populate the vault, then create a master index note linking all CS249R content.

**Dependencies:** Task 2, Task 3

**Files:**
- Create: `/home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/index.md` - Master index of all CS249R content
- Modify: (vault concept files created by Tasks 2-3 scripts)

**Key Decisions / Notes:**
- This is the "run it for real" task - execute the ingestion scripts
- Create a master index note that links to all chapter notes, organized by book part
- Include the book's 6-part structure: Systems Foundations, Design Principles, Performance Engineering, Robust Deployment, Trustworthy Systems, Frontiers
- **Systematic cross-linking**: Use grep to find existing vault concepts matching CS249R topics. Add bidirectional wiki-links in both notes. Specifically check: `meta-learning.md`, `multi-agent-systems.md`, `ai-safety-alignment.md`, `anomaly-detection.md`
- **Quality spot-check**: Sample 5 vault notes (1 from each book part). Verify: (1) frontmatter complete, (2) primary concepts section has 3+ items, (3) no truncation, (4) wiki-links render correctly

**Definition of Done:**
- [ ] All chapter concept notes exist in `/home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/`
- [ ] Master index note created with links to all chapters organized by part
- [ ] Glossary vault note exists with 656+ terms
- [ ] Cross-links added between CS249R notes and existing Cohezion concepts where relevant
- [ ] `vault_find_relevant_context(query="ML systems")` returns CS249R content

**Verify:**
- `ls /home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/ | wc -l` - shows 30+ files
- `grep -l "cs249r" /home/mike-anderson/vaults/cohezion-vault/concepts/cs249r/index.md` - index exists

### Task 5: Create ML Systems Foundations PRIME Skills

**Objective:** Create PRIME skills for the book's first two parts: Systems Foundations (introduction, ML systems, DL primer, DNN architectures) and Design Principles (workflow, data engineering, frameworks, training).

**Dependencies:** Task 4

**Files:**
- Create: `src/cohezion/skills/ML_SYSTEMS_FOUNDATIONS_PRIME.md`
- Create: `src/cohezion/skills/DNN_ARCHITECTURES_PRIME.md`
- Create: `src/cohezion/skills/DATA_ENGINEERING_PRIME.md`

**Key Decisions / Notes:**
- Each PRIME skill follows the standard format: DOMAIN EXPERTISE, KEY TEXTS & CONCEPTS, INSTRUCTION sections
- `ML_SYSTEMS_FOUNDATIONS_PRIME.md` covers: ML system lifecycle, AI Triangle framework (data + algorithms + infrastructure), silent degradation patterns, five-pillar framework
- `DNN_ARCHITECTURES_PRIME.md` covers: CNNs, RNNs, Transformers, attention mechanisms, architecture selection criteria, computational complexity analysis
- `DATA_ENGINEERING_PRIME.md` covers: data pipelines, feature engineering, data quality, distribution shift detection, data versioning
- Draw content from chapter concept maps and the actual chapter `.qmd` content
- Reference TinyTorch modules where applicable (e.g., DNN architectures skill references TinyTorch modules 09-13)

**Definition of Done:**
- [ ] `ML_SYSTEMS_FOUNDATIONS_PRIME.md` created with complete skill definition
- [ ] `DNN_ARCHITECTURES_PRIME.md` created with architecture patterns and selection criteria
- [ ] `DATA_ENGINEERING_PRIME.md` created with pipeline patterns and quality checks
- [ ] All skills reference CS249R vault concepts and TinyTorch modules
- [ ] Skills follow existing PRIME format conventions
- [ ] No diagnostics errors

**Verify:**
- `grep -c "INSTRUCTION" src/cohezion/skills/ML_SYSTEMS_FOUNDATIONS_PRIME.md` - has instruction section
- `grep -c "INSTRUCTION" src/cohezion/skills/DNN_ARCHITECTURES_PRIME.md`
- `grep -c "INSTRUCTION" src/cohezion/skills/DATA_ENGINEERING_PRIME.md`

### Task 6: Create Performance & Deployment PRIME Skills

**Objective:** Create PRIME skills for the book's Part III (Performance Engineering) and Part IV (Robust Deployment) covering efficient AI, model optimization, hardware acceleration, benchmarking, MLOps, on-device learning, and security.

**Dependencies:** Task 4

**Files:**
- Create: `src/cohezion/skills/EFFICIENT_AI_PRIME.md`
- Create: `src/cohezion/skills/MODEL_OPTIMIZATION_PRIME.md`
- Create: `src/cohezion/skills/MLOPS_DEPLOYMENT_PRIME.md`

**Key Decisions / Notes:**
- `EFFICIENT_AI_PRIME.md` covers: knowledge distillation, pruning, quantization (int8/int4), neural architecture search, efficient inference on edge devices. Directly references TinyTorch modules 15 (quantization), 16 (compression), 17 (acceleration)
- `MODEL_OPTIMIZATION_PRIME.md` covers: operator fusion, graph optimization, memory optimization, hardware-aware optimization, benchmarking methodology. References TinyTorch modules 14 (profiling), 19 (benchmarking)
- `MLOPS_DEPLOYMENT_PRIME.md` covers: model serving, A/B testing, monitoring for drift, on-device learning, CI/CD for ML, privacy-preserving techniques
- These skills are particularly relevant to Cohezion's AMD Ryzen AI hardware profile
- Reference HARDWARE_PROFILE_PRIME.md where hardware acceleration is discussed

**Definition of Done:**
- [ ] `EFFICIENT_AI_PRIME.md` created with quantization, pruning, distillation patterns
- [ ] `MODEL_OPTIMIZATION_PRIME.md` created with profiling and optimization techniques
- [ ] `MLOPS_DEPLOYMENT_PRIME.md` created with deployment and monitoring patterns
- [ ] Skills reference CS249R vault concepts and relevant TinyTorch modules
- [ ] Skills reference Cohezion's hardware profile where applicable
- [ ] No diagnostics errors

**Verify:**
- `grep -c "INSTRUCTION" src/cohezion/skills/EFFICIENT_AI_PRIME.md`
- `grep -c "INSTRUCTION" src/cohezion/skills/MODEL_OPTIMIZATION_PRIME.md`
- `grep -c "INSTRUCTION" src/cohezion/skills/MLOPS_DEPLOYMENT_PRIME.md`

### Task 7: Create Trustworthy Systems & Frontiers PRIME Skills

**Objective:** Create PRIME skills for the book's Part V (Trustworthy Systems: responsible AI, sustainable AI, AI for good) and Part VI (Frontiers), plus a skill covering the advanced chapters.

**Dependencies:** Task 4

**Files:**
- Create: `src/cohezion/skills/RESPONSIBLE_AI_PRIME.md`
- Create: `src/cohezion/skills/EDGE_INTELLIGENCE_PRIME.md`

**Key Decisions / Notes:**
- `RESPONSIBLE_AI_PRIME.md` covers: fairness metrics, bias detection, explainability (SHAP, LIME), environmental impact of training, carbon-aware scheduling, safety alignment. Draws from responsible_ai, sustainable_ai, and robust_ai chapters
- `EDGE_INTELLIGENCE_PRIME.md` covers: federated learning, split computing, communication-efficient training, fault tolerance, distributed inference, edge-cloud collaboration. Draws from advanced chapters (edge_intelligence, distributed_training, fault_tolerance, inference, communication)
- These align with Cohezion's CONSTITUTION.md principles (safety, honesty, responsible AI)
- Edge intelligence skill is highly relevant to Cohezion's local-first Ollama architecture

**Definition of Done:**
- [ ] `RESPONSIBLE_AI_PRIME.md` created with fairness, sustainability, and safety patterns
- [ ] `EDGE_INTELLIGENCE_PRIME.md` created with distributed/edge ML patterns
- [ ] Skills reference CS249R vault concepts
- [ ] `RESPONSIBLE_AI_PRIME.md` cross-references `.agent/CONSTITUTION.md` principles
- [ ] No diagnostics errors

**Verify:**
- `grep -c "INSTRUCTION" src/cohezion/skills/RESPONSIBLE_AI_PRIME.md`
- `grep -c "INSTRUCTION" src/cohezion/skills/EDGE_INTELLIGENCE_PRIME.md`

### Task 8: Integrate TinyTorch Core Modules (01-09)

**Objective:** Adapt TinyTorch's core modules (tensor, activations, layers, losses, dataloader, autograd, optimizers, training, convolutions) into Cohezion's codebase as `src/cohezion/tinytorch/`.

**Dependencies:** Task 1

**Files:**
- Create: `src/cohezion/tinytorch/__init__.py`
- Create: `src/cohezion/tinytorch/tensor.py` (from module 01)
- Create: `src/cohezion/tinytorch/activations.py` (from module 02)
- Create: `src/cohezion/tinytorch/layers.py` (from module 03)
- Create: `src/cohezion/tinytorch/losses.py` (from module 04)
- Create: `src/cohezion/tinytorch/dataloader.py` (from module 05)
- Create: `src/cohezion/tinytorch/autograd.py` (from module 06)
- Create: `src/cohezion/tinytorch/optimizers.py` (from module 07)
- Create: `src/cohezion/tinytorch/training.py` (from module 08)
- Create: `src/cohezion/tinytorch/convolutions.py` (from module 09)
- Create: `tests/tinytorch/__init__.py`
- Create: `tests/tinytorch/test_core.py`

**Key Decisions / Notes:**
- **ISOLATION**: TinyTorch is a STANDALONE educational subpackage. NO imports from `cohezion.compound`, `cohezion.swarm`, or any other Cohezion module. Only numpy and stdlib. This preserves it as a self-contained learning resource and prevents test coupling
- TinyTorch source files are Jupytext percent-format `.py` files. Extract code cells using regex `^# %%(?!\[markdown\])`, skip markdown cells. Test extraction on modules 01 and 06 first, verify output is valid Python before batch-processing
- TinyTorch depends only on NumPy - maintain this constraint
- Each source file contains a complete module. Extract the exported functions/classes
- The `tinytorch/` package in the original repo has `core/` and `perf/` subpackages with `__init__.py` only - the actual code is in `src/01_tensor/01_tensor.py` etc.
- Adapt imports: TinyTorch internal imports like `from tinytorch.core.tensor import Tensor` become `from cohezion.tinytorch.tensor import Tensor`
- Add type hints where TinyTorch doesn't have them (it targets Python 3.8+, we target 3.13+)
- Keep files under 300 lines - split if needed

**Definition of Done:**
- [ ] All 9 core modules adapted and importable from `cohezion.tinytorch`
- [ ] Internal cross-imports work (e.g., `layers.py` imports from `tensor.py`)
- [ ] Tests verify basic tensor operations, autograd backward pass, and a simple training loop
- [ ] No diagnostics errors from `ruff check` on new files
- [ ] All files under 300 lines

**Verify:**
- `uv run pytest tests/tinytorch/test_core.py -q` - core module tests pass
- `uv run python -c "from cohezion.tinytorch import Tensor; t = Tensor([1,2,3]); print(t)"` - basic import works

### Task 9: Integrate TinyTorch Advanced Modules (10-20)

**Objective:** Adapt TinyTorch's advanced modules (tokenization, embeddings, attention, transformers, profiling, quantization, compression, acceleration, memoization, benchmarking, capstone) into `src/cohezion/tinytorch/`.

**Dependencies:** Task 8

**Files:**
- Create: `src/cohezion/tinytorch/tokenization.py` (from module 10)
- Create: `src/cohezion/tinytorch/embeddings.py` (from module 11)
- Create: `src/cohezion/tinytorch/attention.py` (from module 12)
- Create: `src/cohezion/tinytorch/transformers.py` (from module 13)
- Create: `src/cohezion/tinytorch/profiling.py` (from module 14)
- Create: `src/cohezion/tinytorch/quantization.py` (from module 15)
- Create: `src/cohezion/tinytorch/compression.py` (from module 16)
- Create: `src/cohezion/tinytorch/acceleration.py` (from module 17)
- Create: `src/cohezion/tinytorch/memoization.py` (from module 18)
- Create: `src/cohezion/tinytorch/benchmarking.py` (from module 19)
- Create: `tests/tinytorch/test_advanced.py`

**Key Decisions / Notes:**
- Same extraction approach as Task 8: parse Jupytext files, extract code cells
- Modules 10-13 (tokenization through transformers) form the NLP/attention stack
- Modules 14-19 form the performance engineering stack
- Module 20 (capstone) ties everything together. Extract ONLY 2-3 core examples (full training loop, model evaluation). If >300 lines, create `capstone/` subpackage with split files. Do NOT port entire module verbatim
- These modules build on the core modules from Task 8 - ensure import chains work
- Quantization module (15) is particularly relevant to Cohezion's AMD hardware profile
- Keep files under 300 lines - the attention and transformer modules may need splitting

**Definition of Done:**
- [ ] All 10 advanced modules adapted and importable
- [ ] Attention mechanism works end-to-end (tokenize -> embed -> attend -> transform)
- [ ] Quantization module can quantize a simple model to int8
- [ ] Profiling module can time operations
- [ ] Tests cover attention forward pass and quantization round-trip
- [ ] No diagnostics errors
- [ ] All files under 300 lines

**Verify:**
- `uv run pytest tests/tinytorch/test_advanced.py -q` - advanced module tests pass
- `uv run python -c "from cohezion.tinytorch.attention import MultiHeadAttention; print('OK')"` - imports work

### Task 10: End-to-End Validation and SurrealDB Indexing

**Objective:** Run the complete integration pipeline, import CS249R concepts into SurrealDB for graph querying, validate cross-links, and run the full test suite.

**Dependencies:** Task 4, Task 5, Task 6, Task 7, Task 8, Task 9

**Files:**
- Create: `scripts/cs249r/index_to_surreal.py` - SurrealDB indexing script
- Create: `tests/cs249r/test_integration.py` - End-to-end integration tests
- Modify: `src/cohezion/skills/skill_registry.json` - Register new PRIME skills

**Key Decisions / Notes:**
- Import vault concepts to SurrealDB using the existing `surrealdb_import_concepts` MCP tool (which scans `/home/mike-anderson/vaults/cohezion-vault/concepts/`)
- Also import the glossary data from `data/cs249r_glossary_surreal.json` (created in Task 3) using format: `[{"id": "glossary:term-slug", "term": "...", "definition": "...", "chapter": "...", "tags": [...]}]`
- Validate that `vault_find_relevant_context` returns CS249R content for ML queries
- Run full Cohezion test suite to ensure no regressions
- **Skill registration**: Check if `skill_registry.json` is auto-generated by scanning `src/cohezion/skills/`. If auto-generated, run the scanner. If manual, add entries for all 8 new skills with name, path, and domain fields
- Create a summary report of what was ingested (chapter count, concept count, glossary terms, skills created, TinyTorch modules)

**Definition of Done:**
- [ ] All CS249R concepts indexed in SurrealDB
- [ ] `vault_find_relevant_context("quantization")` returns CS249R efficient AI content
- [ ] `vault_find_relevant_context("transformer architecture")` returns CS249R DNN content
- [ ] All 8 new PRIME skills registered in skill registry
- [ ] Full test suite passes: `uv run pytest tests/ -q` (no regressions)
- [ ] Summary report printed showing ingestion statistics

**Verify:**
- `uv run pytest tests/ -q` - full suite passes with no regressions
- `uv run pytest tests/cs249r/ -q` - all CS249R-specific tests pass
- `uv run pytest tests/tinytorch/ -q` - all TinyTorch tests pass

## Testing Strategy

- **Unit tests:** Test each ingestion function (YAML parsing, JSON parsing, vault note generation) in isolation
- **Integration tests:** Test the full pipeline from repo access through vault write
- **TinyTorch tests:** Test core operations (tensor math, autograd, training loop) and advanced features (attention, quantization)
- **Regression tests:** Run full Cohezion test suite to ensure no existing tests break
- **Manual verification:** Spot-check vault notes for content quality, query SurrealDB for cross-links

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TinyTorch modules are too large for 300-line limit | High | Low | Split into submodules (e.g., `attention/multi_head.py`, `attention/scaled_dot.py`) |
| Some chapter concept files are missing or malformed | Medium | Low | Graceful error handling in ingestion scripts: log warning, skip file, continue |
| TinyTorch code depends on features not in NumPy 2.x | Low | Medium | Pin NumPy version or add compatibility shims during adaptation |
| SurrealDB not running during indexing task | Medium | Low | Task 10 can be deferred; vault files work independently of SurrealDB |
| Repository structure changes upstream | Low | Low | Pin to specific commit hash when cloning |
| Full test suite fails due to new imports | Medium | Medium | Keep `tinytorch/` fully isolated with no imports from other Cohezion modules |

## Open Questions

- Should we also extract quiz data from chapters for use in Cohezion's evaluation/testing framework?

### Deferred Ideas

- Interactive TinyTorch notebook integration with Marimo
- Using CS249R quiz data as training evaluation benchmarks for Cohezion agents
- Building a Cohezion "ML Systems Tutor" agent using the ingested knowledge
- Importing the advanced chapters' content (storage, infrastructure, communication) as additional skills
- Exposing TinyTorch modules via the Cohezion API (FastAPI endpoints for educational use)
