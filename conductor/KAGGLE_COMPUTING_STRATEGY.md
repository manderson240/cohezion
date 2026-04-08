# Kaggle Computing & Submission Strategy

## 1. Deadlines & Priority
| Competition | Deadline | Status | Priority |
| :--- | :--- | :--- | :--- |
| **Measuring Progress Toward AGI** | **April 16, 2026** | Phase 5: Leaderboard Optimization | **CRITICAL** (9 Days Remaining) |
| **AIMO Progress Prize 3** | May 22, 2026 | Phase 4: Production Deployment | HIGH |
| **NVIDIA Nemotron Challenge** | TBD | Phase 5: Execution & Monitoring | HIGH |
| **ARC Prize 2026** | June 30, 2026 | Phase 4: ARC-AGI-2 (Static) | MEDIUM |
| **BirdCLEF 2026** | TBD | Phase 2: Baseline Model | MEDIUM |

## 2. Resource Allocation (Quota Mapping)

### A. AI Models API Quota ($50/day, $500/month)
*   **Target:** Measuring Progress Toward AGI
*   **Rationale:** The competition requires high-fidelity baseline evaluations using `kbench`. The rules permit commercial models for benchmarking. We must burn this daily resetting quota to evaluate our synthetic tasks against frontier models (e.g., Gemini 1.5 Pro/Flash) directly on Kaggle without incurring out-of-pocket API costs.

### B. Standard GPU Quota (30h/week)
*   **Targets:** BirdCLEF 2026 & ARC Prize 2026
*   **Rationale:** These tracks involve parallelizable, heavy compute (spectrogram processing, JEPA World Model Test-Time Training) but do not have dedicated sponsor hardware. We will utilize Kaggle's dual T4s/P100s to offload this training from our local AMD orchestration machine.

### C. Dedicated Sponsor Compute (Free - No Quota Drain)
*   **Targets:** AIMO Progress Prize 3 & NVIDIA Nemotron Challenge
*   **Rationale:** These competitions provide their own isolated hardware environments. 
    *   **AIMO:** Submissions run on dedicated **H100 (80GB)** GPUs with a 5-hour limit. (Rule constraint: runtime models must be open-weight pre-March 15, 2026).
    *   **Nemotron:** Training scripts run on dedicated **Google Cloud G4 (Blackwell)** VMs.

## 3. Submission Governance
*   Strictly adhere to the 1-5 submissions/day limits per competition.
*   All submissions must be logged via `scripts/DAILY_SUBMISSION_GOVERNANCE.py` to `.gemini_security/submission_log.jsonl`.
*   For Kaggle Notebook submissions, always verify the environment (e.g., the "Blackwell Handshake" for Nemotron) and ensure dependencies are bundled or installed via pre-built wheels to prevent compilation timeouts.
