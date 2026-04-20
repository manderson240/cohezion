# Multi-Track Sprint Plan: Hybrid Cloud Swarm Deployment

This sprint plan orchestrates the Hybrid Cloud Swarm (Gemini 2.5 Pro/Flash + Ollama) across three active tracks, leveraging their specific context windows and capabilities to maximize parallel execution without exceeding hardware limits.

## Track 1: NVIDIA Nemotron Reasoning (Unblocking)
**Objective:** Upload ROCm-compatible `trl` and `bitsandbytes` wheels to a Kaggle dataset to resolve the dependency block on the G4 Blackwell environment.
**Assigned Agents:**
- **Local Prototyping Specialist (Ollama - glm-4.7-flash-256k):** Fast automation and scripting.

**Implementation Steps:**
1. **Script Automation:** Create a script (`scripts/upload_rocm_wheels.py`) that automates downloading the required `.whl` files using `pip download --no-deps`.
2. **Dataset Curation:** Programmatically generate the `dataset-metadata.json` required by Kaggle.
3. **API Integration:** Utilize the `kaggle datasets create/version` API to push the wheels as a public dataset that the Nemotron notebook can mount and install offline.

## Track 2: ARC Prize 2026 (Advancing)
**Objective:** Implement exploitation loop detection and EXPLORE/EXPLOIT pivoting logic in `arc_topology_navigation.py` to prevent the agent from getting stuck in repetitive state cycles in the 12D manifold.
**Assigned Agents:**
- **Gemini System Architect (Cloud - gemini-2.5-pro - 2M Context):** Design the topological state analysis and loop detection algorithm based on historical trajectory embeddings.
- **Gemini Code Specialist (Cloud - gemini-2.5-flash - 1M Context):** Implement the precise loop detection mathematical logic and the state-switching mechanism.

**Implementation Steps:**
1. **Trajectory Analysis:** Update `TopologicalRouter` to maintain a rolling window of recent 12D coordinates.
2. **Distance Thresholding:** Implement logic to calculate cosine similarity/L2 distance over the window. If the agent remains within a tight radius for $N$ steps, flag as an "Exploitation Loop".
3. **Pivoting:** Force a `TopologicalRegime.PIVOT` state that dramatically injects noise (simulated temperature increase) into the Axiomatic Projector to break the loop.

## Track 3: Measuring Progress Toward AGI (Execution)
**Objective:** Finalize the 75-task local evaluation using the `evaluator_kbench.py` script and prepare the official Kaggle submission writeup.
**Assigned Agents:**
- **Local Math Specialist (Ollama - phi4-256k):** Oversee the local `kbench` evaluation run, ensuring numerical tracking and error-free evaluation of the 75 tasks.
- **Gemini System Architect (Cloud - gemini-2.5-pro):** Synthesize the empirical findings and FLUME integration details into the final `KAG_BENCHMARK_WRITEUP.md`.

**Implementation Steps:**
1. **Local Benchmark Run:** Execute `uv run python kaggle-agi-benchmark/evaluator_kbench.py` using `qwen3-coder:30b` (or equivalent) to get the final baseline score.
2. **Results Synthesis:** Collect the track-by-track breakdown (Learning, Metacognition, Attention, Executive Function, Social Cognition).
3. **Writeup Drafting:** Generate the final markdown document formatted according to Kaggle benchmark standards.

## Execution Governance
- **Concurrency:** Maximum of 2 Ollama models will be running concurrently (Local Prototyping Specialist and Local Math Specialist), preserving 1 slot for background system tasks.
- **Cloud Fallback:** If any local execution fails or times out, the tasks will automatically escalate to the Gemini Code Specialist.

---
**Status:** Awaiting user approval to exit plan mode and begin autonomous execution.
