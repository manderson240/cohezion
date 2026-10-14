# 🌐 Grounded Research Clarifications: Claude Fable 5.1, Kaggriculture Seat Mechanics, Biohub Metric & ARC-AGI-3

**Date**: 2026-09-28 00:40 UTC  
**Sources**: Official Anthropic Fable 5.1 Specs, Kaggle Environment Source Code, ARC-Prize 2026 Discussions, Biohub Cell Tracking Metric Publications  

---

## 1. Claude Fable 5.1 (`claude-fable-5-1`) Official Specifications

*   **Class & Architecture**: Released in September 2026 as Anthropic's flagship "Mythos-class" intelligence specifically tuned for long-horizon autonomous tasks, high-stakes system evaluation, and deep scientific research.
*   **Context Window**: **1,000,000 tokens** (1M).
*   **API Identifiers**: `claude-fable-5-1`, aliased to `claude-fable-5-1[1m]`.
*   **Headless CLI Execution**: Non-interactive print mode (`claude -p`) requires an active OAuth session (`CLAUDE_CODE_OAUTH_TOKEN`). Injecting custom doctrines via `--append-system-prompt` enables zero-hook, pure doctrine evaluation without loading unwanted plugin hooks.

---

## 2. Kaggriculture Observation Mechanics: Root Cause of v7 Rating Drop

*   **Turn Structure**: 30 days $\times$ 24 turns/day = **720 turns** per episode.
*   **Observation Dictionary Keys**: The environment passes `observation["day"]` (0–29) and `observation["hour"]` (0–23).
*   **The Seat-1 Bug in v7**:
    *   In Seat 1 (Player 2), `observation.get("step")` is omitted by the engine.
    *   In `submission_v7.py`, lines 7026, 7108, and 7381 executed:
        ```python
        step = int(observation.get("step", 0))
        ```
    *   As a result, for 50% of matches (all Seat 1 games), `step` was permanently evaluated as `0`. The agent never advanced past Day 0, never harvested, never planted, and dumped inventory into a vacuum, driving tournament ratings down to 1232.9.
*   **The Proven Invariant**: `main_SOTA_2945.py` and `main_GM_41ROUTE.py` explicitly implement:
    ```python
    def _step_of(observation):
        raw = _get(observation, "step")
        if raw is not None:
            return _int(raw)
        return _int(_get(observation, "day", 0)) * 24 + _int(_get(observation, "hour", 0))
    ```
    This function guarantees full 720-turn functionality across both Seat 0 and Seat 1, validating the immediate re-upload of `main_SOTA_2945.py` (2119.5) and `main_GM_41ROUTE.py` (2138.5).

---

## 3. Biohub 3D Cell Tracking Metric Reality

*   **Competition Metric**: Rather than the legacy Cell Tracking Challenge AOGM with $w_{FN}=10$, the official formula is:
    $$\text{Score} = J_{\text{edge}} \cdot \left(1 - 0.1 \cdot \frac{N_{\text{pred}} - N_{\text{est}}}{N_{\text{est}}}\right) + 0.1 \cdot J_{\text{div}}$$
*   **Symmetric Error Penalty**: Unlinked false positive nodes only incur the scalar penalty $0.1 / N_{\text{est}}$, while false edges incur symmetric Jaccard degradation.
*   **Leaderboard Decision**:
    *   **Slot 1**: V7 (Ref `#56433510`, score **0.946**) — clean, highly generalizable Hungarian matching.
    *   **Slot 2**: V21 (Ref `#56621668`, currently pending) if score $\ge 0.946$; otherwise `run79` fork (Ref `#56263700`, score **0.944**) to hedge against private shakeup.

---

## 4. ARC-AGI-3 Interactive Agent Scoring Formula

*   **Action Budget Efficiency Formula**:
    $$\text{Level Score} = \min\left(115, \left(\frac{\text{baseline\_actions}}{\text{your\_actions}}\right)^2 \times 100\right)$$
*   **Implication**: Scoring is quadratic in action efficiency. Any unguided BFS, random walk, or reactive prompt loops in the live environment multiply `your_actions`, collapsing the score toward $0.00$.
*   **Strategic Policy**: Do not burn daily submissions on live exploration. The interactive solver must be trained or planned offline on an internal transition model, executing only minimal verified paths. Keep `scripts/kaggle/arc3_v1_submitted.flag` armed and focus compute on ARC-AGI-2 (31.81%) and the Paper Track.
