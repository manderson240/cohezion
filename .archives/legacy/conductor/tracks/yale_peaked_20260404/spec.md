# Yale Peaked Hackathon 2026 Specification

## Overview
This track focuses on participating in and successfully completing the **Yale Peaked Hackathon 2026** on the BlueQubit platform. The goal is to solve a series of quantum computing challenges (P1-P10) by identifying heavy output bitstrings from peaked circuits. We have a total of **$20 in credits** and approximately **21 hours remaining**.

## Objectives
- **Maximize Free Tier Usage:** Attempt to solve problems P1-P8 using the free tier devices (e.g., `mps.cpu`) to conserve credits.
- **Strategic Credit Allocation:** Carefully use the $20 in credits for the most complex problems (P9-P10) or to retry failed problems with higher bond dimensions on paid devices (e.g., `mps.gpu`).
- **Rapid Execution:** Follow a phased execution plan: assessment, parallel submission, monitoring, and optimization.
- **Accurate Documentation:** Maintain a detailed log of all attempts, parameters used (qubits, bond_dim), and results.

## Functional Requirements
- **Circuit Analysis:** Automatically analyze downloaded circuits to determine qubit count and gate structure.
- **Problem Solving:** Implement a solver (e.g., `solve_peaked_circuit.py`) that uses Matrix Product States (MPS) to find the heavy output bitstring.
- **Batch Processing:** Support parallel submission of multiple problems to minimize idle time.
- **Submission Generation:** Generate manual submission text in Markdown format for each problem, including the problem ID and the identified bitstring.
- **Credit Monitoring & Approval:** 
    - Track and manage the $20 budget according to BlueQubit pricing (https://app.bluequbit.io/docs#pricing).
    - **CRITICAL:** Explicit user approval is REQUIRED for **ANY** action that incurs a cost (e.g., submitting to a paid device).
    - **Justification:** For any cost-associated action, the agent MUST provide a detailed explanation of the cost, why it is necessary, and what the expected benefit is.

## Non-Functional Requirements
- **Time Constraint:** Complete all tasks and submissions within the remaining 21-hour window.
- **Reliability:** Ensure that bitstring reversal (LSB to MSB) is handled correctly for the hackathon's submission format.
- **Resource Efficiency:** Optimize bond dimensions to balance accuracy and runtime/cost.

## Acceptance Criteria
- [ ] Successfully downloaded all challenge circuits (P1-P10).
- [ ] Submitted verified answers for at least P1-P5 (free tier baseline).
- [ ] Strategic plan developed and executed for using the $20 in credits on P9-P10.
- [ ] Generated a comprehensive `FINAL_SUBMISSION_REPORT.md` containing all problem answers.
- [ ] Documented lessons learned in `LESSONS_LEARNED_PLAYBOOK.md`.

## Out of Scope
- Integration with real QPU devices (e.g., `ibm.heron`) unless specifically required and budget allows.
- Developing new simulation algorithms from scratch (rely on existing BlueQubit SDK and templates).