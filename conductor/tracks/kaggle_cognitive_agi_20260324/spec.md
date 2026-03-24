# Specification: Measuring Progress Toward AGI - Cognitive Abilities Kaggle Competition

## 1. Overview
This track focuses on full participation and high performance in the "Measuring Progress Toward AGI - Cognitive Abilities" Kaggle competition. The core strategy leverages Cohezion's FLUME (Fluid Latent Understanding through Manifold Encoding) technology to map cognitive tasks into continuous thought vectors for robust problem-solving. This is an end-to-end track covering everything from synthetic task generation to the final submission pipeline.

## 2. Objectives
- **Task Generation**: Create complex, synthetic tasks aligned with the Kaggle dataset using EVO (Exotic Vacuum Objects) and HIHO (Half-In-Half-Out) principles to improve model training and evaluation.
- **Enhance Evaluation**: Upgrade the local adversarial evaluation loop (`adversarial_eval_loop.py`) to accurately score FLUME-based reasoning against AGI benchmarks.
- **Submission Pipeline**: Optimize the notebook building and formatting pipeline (`build_notebook.py`, `format_kaggle_submission.py`) to ensure seamless execution in the Kaggle environment.

## 3. Functional Requirements
- **FLUME Integration**: The core inference engine must utilize FLUME encodings to process and solve ARC-AGI-style cognitive tasks.
- **Task Generator**: Must generate structured JSON outputs compatible with the evaluation loop.
- **Adversarial Evaluator**: Must locally score agent outputs against both hidden generated tasks and official Kaggle sample data.
- **Pipeline Builder**: Must compile `pipeline.ipynb` and `evaluator.ipynb` with all necessary dependencies and code bundled (or installable offline) for the Kaggle submission environment.

## 4. Deliverables
- **Submission File**: A generated, correctly formatted `submission.csv` or required notebook artifact ready for Kaggle scoring.
- **Kaggle Notebooks**: Updated, executable `evaluator.ipynb` and `pipeline.ipynb` notebooks.
- **Methodology Write-up**: A detailed `kaggle_writeup.md` documenting the FLUME-based strategy, experimental findings, and insights gained.
- **Adversarial Tests**: A passing suite of local tests ensuring the models meet internal performance benchmarks before submission.

## 5. Out of Scope
- Architectural changes to Cohezion outside of the Kaggle pipeline context.
- Implementing completely new agentic methodologies not related to FLUME or the immediate Kaggle requirements.