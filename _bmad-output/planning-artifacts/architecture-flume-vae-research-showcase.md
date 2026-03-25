---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prd-flume-vae-research-showcase.md
  - _bmad-output/planning-artifacts/product-brief-concurrent-discovering-bubble-2026-03-23.md
  - _bmad-output/planning-artifacts/ux-design-flume-vae-research-showcase.md
  - _bmad-output/project-context.md
  - docs/archive/FLUME_PAPER_DRAFT.md
  - docs/archive/FLUME_HF_MODEL_CARD.md
  - docs/patents/FLUME_PROVISIONAL_APPLICATION.md
workflowType: 'architecture'
project_name: 'concurrent-discovering-bubble'
user_name: 'Mike-anderson'
date: '2026-03-23'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

This is a brownfield assembly project with 5 MVP features (6-8 hour timeline):

1. **Enhanced Marimo Notebook** (3 hours, Critical): Modify `notebooks/marimo/flume_showcase.py` to load real trained checkpoint (`data/flume/checkpoints/flume_vae_ep5.pt`, 14MB) instead of synthetic data. Display actual training metrics from JSON. Visualize latent space with real samples.

2. **Reproducibility README** (1 hour, Critical): Create `README_FLUME.md` with one-command setup: `git clone → uv venv → marimo run notebooks/marimo/flume_showcase.py`. Document expected outputs (2D projection plot, metrics table). Zero configuration required.

3. **Published Blog Post** (2 hours, High): Publish existing `docs/blog/01_flume_thought_autoencoders.md` (458 lines, VAE architecture + equations) at web-accessible URL. Link from portfolio and Marimo notebook.

4. **Portfolio Updates** (1 hour, High): Update `/portfolio` page to remove 4 "COMING SOON" cards. Focus on FLUME VAE as single complete artifact. Update stats (4,658 tests, specific metrics).

5. **GitHub Accessibility** (1 hour, Critical): Make repo public. Add "For Evaluators: Start Here" section to root README. Ensure reproducibility instructions are clear.

**Architectural Implications:**
- **No New Components**: All features involve assembly/configuration of existing code
- **Integration Focus**: Connect Marimo notebook → checkpoint → API → webapp → portfolio
- **Path Resolution**: Marimo runs from `notebooks/marimo/`, API from project root - need consistent checkpoint loading
- **Type Safety**: Python (Pydantic) ↔ TypeScript (interfaces) - maintain schema compatibility

**Non-Functional Requirements:**

1. **Reproducibility** (Gate 1 - Critical):
   - **Target**: 100% success rate for `git clone → marimo run` on fresh Linux/macOS system
   - **Constraint**: Zero configuration files (.env, config.yaml) - PEP 723 inline dependencies only
   - **Validation**: Test on clean VM before submission
   - **Architectural Impact**: All paths must be relative or auto-resolved, no hardcoded absolute paths

2. **Speed** (Gate 2 - Critical):
   - **Target**: <5 minutes from portfolio landing → technical review decision
   - **Breakdown**: 2 min portfolio scan + 2 min demo interaction + 1 min blog skim
   - **Architectural Impact**: Pre-compute expensive operations (PCA projections), lazy-load heavy components

3. **Verifiability** (Gate 3 - Critical):
   - **Target**: 100% of claims verifiable by evaluators
   - **Claims to Verify**: 4,658 tests (run `uv run pytest`), MSE 0.023 (in metrics JSON), 14MB checkpoint (file size)
   - **Architectural Impact**: Metrics must be programmatically extractable, not manually typed

4. **Performance** (User Experience):
   - **Target**: Marimo notebook renders 200-500 samples in <2 seconds
   - **Baseline**: Existing webapp (`FlumeNavigator.tsx`) achieves this with real-time API calls
   - **Architectural Impact**: Notebook may need caching or pre-computed projections

5. **Error Recovery** (Robustness):
   - **Required**: Graceful degradation for missing checkpoint, API timeout, WebGL unavailable
   - **Existing**: Webapp has error boundaries, context loss recovery, retry buttons
   - **Architectural Impact**: Marimo should match webapp's defensive programming patterns

**Scale & Complexity:**

- **Primary Domain**: Full-Stack (Python backend, React frontend, Marimo notebooks)
- **Complexity Level**: Medium (brownfield assembly, not greenfield engineering)
- **Estimated Architectural Components**: 3 integration layers (Marimo ↔ Checkpoint, API ↔ Checkpoint, Webapp ↔ API)
- **Existing Infrastructure**: 26 Python modules (`src/cohezion/flume/`), 375-line React component (`FlumeNavigator.tsx`), 10 Marimo notebooks

### Technical Constraints & Dependencies

**Technology Stack (Non-Negotiable):**
- Python 3.13+, `uv` package manager (never bare pip per project context)
- FastAPI >=0.104.0 (existing API at `:8080` with 72 routes)
- Next.js 16 + React 19 (existing webapp at `:3000`)
- Marimo notebooks with PEP 723 inline dependencies (reproducibility requirement)
- PyTorch >=2.0.0 for checkpoint loading
- TailwindCSS 4.0 for styling (existing portfolio uses this)

**Existing Infrastructure:**
- **FLUME VAE Implementation**: 26 Python modules in `src/cohezion/flume/` (encoder, decoder, trainer, latent projection utilities)
- **Trained Checkpoints**: 3 files (ep2: 889KB, ep5: 14MB, ep50: 889KB) - using ep5 for demo
- **Training Metrics**: `data/flume/checkpoints/training_metrics.json` (5 epochs, MSE/KL divergence data)
- **Test Suite**: 4,658 tests at 99.9% pass rate (<90 seconds execution) - CANNOT regress
- **Documentation**: 1,130 lines (paper draft, HF model card, blog post, patent application)

**Deployment Constraints:**
- Must work with: `git clone → uv venv → uv pip install -e . → marimo run notebooks/marimo/flume_showcase.py`
- No Docker containers (evaluator friction)
- No config files (.env, YAML) - PEP 723 handles dependencies
- No external services (SurrealDB, Redis) required for FLUME demo - standalone only

**Timeline Constraint:**
- **Total**: 6-8 hours for all 5 features (per PRD)
- **Breakdown**: 3hr notebook + 1hr README + 2hr blog + 1hr portfolio + 1hr GitHub = 8 hours
- **Architectural Impact**: Favor simple solutions over complex abstractions

### Cross-Cutting Concerns Identified

1. **Checkpoint File Path Resolution**:
   - **Issue**: Marimo runs from `notebooks/marimo/` (relative path: `../../data/flume/checkpoints/flume_vae_ep5.pt`), FastAPI runs from project root (relative path: `data/flume/checkpoints/flume_vae_ep5.pt`)
   - **Risk**: Hardcoded relative paths break when working directory changes
   - **Architectural Decision Needed**: Use `Path(__file__).parent.parent.parent` resolution or environment-agnostic absolute paths

2. **Type Safety Across Language Boundaries**:
   - **Issue**: Python API returns `LatentSpaceData` (Pydantic model with `latent_dim`, `samples`, `samples_3d`, `variance_explained`, `coherence_scores`), TypeScript webapp expects matching interface
   - **Risk**: Schema drift when backend adds/removes fields
   - **Architectural Decision Needed**: Generate TypeScript types from Pydantic OR use OpenAPI schema validation

3. **Error Messaging Consistency**:
   - **Webapp Standard**: User-friendly messages ("WEBGL CONTEXT LOST" with "RELOAD PAGE" button), not technical stack traces
   - **Marimo Standard**: Python tracebacks (technical, evaluator-appropriate)
   - **Architectural Decision Needed**: Match error verbosity to audience (evaluators = technical, portfolio visitors = friendly)

4. **Performance Expectations**:
   - **Webapp Baseline**: 200 samples render in <2 seconds (measured in production)
   - **Marimo Target**: Match or exceed webapp performance (evaluator perception)
   - **Architectural Decision Needed**: Pre-compute PCA projections vs. compute on-demand? Cache latent samples vs. regenerate?

5. **Brand/Visual Consistency**:
   - **Portfolio**: Neon Cyan (#00f2fe), Matte Black (#0A0A0A), monospace fonts (Cohezion brand identity)
   - **Marimo**: Default matplotlib colors (blue, orange) - doesn't match brand
   - **Architectural Decision Needed**: Shared theme configuration? Custom matplotlib style?

6. **Documentation Synchronization**:
   - **Claims**: Portfolio says "4,658 tests", README says "4,658 tests", blog says "4,658 tests"
   - **Risk**: Manual updates lead to inconsistency (e.g., test count changes to 4,700)
   - **Architectural Decision Needed**: Programmatically extract metrics (test count, checkpoint size, MSE) from source?

---

## Starter Template Evaluation

### Existing Technical Preferences from Project Context

**Languages & Frameworks:**
- **Python 3.13+** (mandatory)
- **FastAPI >=0.104.0** (72 existing routes)
- **Next.js 16 + React 19** (existing webapp at `:3000`)
- **Marimo notebooks** with PEP 723 inline dependencies
- **PyTorch >=2.0.0** for ML/checkpoint loading

**Development Tools:**
- **Package Manager**: `uv` (never bare pip - project context rule)
- **Linting**: ruff >=0.8.0 (format + lint)
- **Type Checking**: mypy >=1.5.0 (strict mode)
- **Testing**: pytest >=8.0.0 with pytest-asyncio

**Existing Infrastructure:**
- **Backend API**: FastAPI at `:8080`
- **Frontend**: Next.js/React at `:3000`
- **Web Components**: FlumeNavigator.tsx (375 lines, React Three Fiber + WebGL)
- **Test Suite**: 4,658 tests at 99.9% pass rate

### Primary Technology Domain

**Full-Stack Python + React** with specialized Marimo notebooks for research reproducibility

**Project Classification**: **Brownfield Assembly** (not greenfield starter)

### Starter Template Decision: N/A (Existing Infrastructure)

**Rationale for NO Starter Template:**

This is a **brownfield assembly project**, not greenfield development. All core infrastructure already exists:

1. **Backend (Python/FastAPI)**: 26 FLUME modules, existing `/flume/latent-space` endpoint, 4,658 tests
2. **Frontend (Next.js/React)**: Production webapp with FlumeNavigator (375 lines), portfolio pages deployed
3. **Research Artifacts (Marimo)**: 10 existing notebooks, target `flume_showcase.py` with PEP 723 dependencies

**Architectural Decisions Already Made:**

- **Language & Runtime**: Python 3.13+ with type hints (mypy --strict), Node.js 18+ for Next.js
- **Styling Solution**: TailwindCSS 4.0, brand tokens in `public/brand-tokens.css`
- **Build Tooling**: `uv` package manager, Next.js webpack, PEP 723 inline dependencies
- **Testing Framework**: pytest with pytest-asyncio (4,658 tests), React Testing Library + Playwright
- **Code Organization**: Python `src/cohezion/`, Next.js App Router, notebooks in `notebooks/marimo/`

### Architectural Implications for This Project

Since no starter template is used, architectural decisions focus on **integration patterns**:

1. **Checkpoint Loading Pattern**: Use existing `FlumeVAETrainer.from_checkpoint()` API in Marimo
2. **API Data Contract**: Match TypeScript `LatentSpaceData` interface to Pydantic model
3. **Error Handling Consistency**: Marimo uses `try/except` with evaluator-appropriate messages
4. **Performance Optimization**: Match webapp baseline (200 samples in <2 seconds)
5. **Visual Branding**: Custom matplotlib style matching Cohezion brand (Neon Cyan #00f2fe)
6. **Metrics Extraction**: Programmatic extraction from pytest, training_metrics.json, file stats

**Note:** Implementation focuses on Feature 1 (Enhanced Marimo Notebook) as primary integration point. No project initialization needed - enhancing existing artifacts.
