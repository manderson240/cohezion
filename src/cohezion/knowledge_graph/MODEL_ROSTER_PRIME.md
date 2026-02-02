# MODEL ROSTER PRIME (2026 Edition)
*High-Fidelity Intelligence, Low-Token Footprint*

## 1. The Strategy
To conserve high-vram/compute resources, the Swarm prioritizes **State-of-the-Art Small Language Models (SLMs)** for 80% of tasks.
We leverage the "Distillation Revolution" where <10B models rival previous 70B giants.

## 2. The Roster (128GB RAM / 12GB VRAM Optimized)

### A. The "Scout" (Routine Logic & JSON)
**Model**: `Microsoft Phi-4` (3.8B)
- **Role**: `issue_scout`, log parsing, simple classification.
- **Why**: Massive context window, reasoning rivals GPT-3.5, extremely fast.

### B. The "Engineer" (Code Generation)
**Model**: `Qwen-2.5-Coder-7B`
- **Role**: Refactoring, unit tests, bug fixes (`refine_skill`).
- **Why**: Current SOTA for <10B coding. Outperforms previous 34B models.

### C. The "Planner" (Reasoning & Consensus)
**Model**: `DeepSeek-R1-Distill-Llama-8B`
- **Role**: `implementation_plan`, architecture definition, 12-Agent Council votes.
- **Why**: Chain-of-Thought reasoning baked in.

### D. The "Eye" (Vision)
**Model**: `MiniCPM-V-2.6` (8B) or `Llava-Phi-3`
- **Role**: UI Verification (`NanoBananaSplash`), screenshot analysis.

## 3. The 12-Agent Council (Virtual Personas)
*Simulated via System Prompts on top of the generic Roster.*
1. Architect (Structrual)
2. Engineer (Implementation)
3. Biologist (Evolution)
4. Physicist (12D Manifold)
5. Historian (Project Memory)
6. Security (Guardrails)
7. UX Designer (Experience)
8. QA Tester (Mycelium)
9. Resource Guard (Hardware)
10. Ethicist (Alignment)
11. Scout (Discovery)
12. Critic (Adversarial)

## 4. Research Lab Protocol
The Research Lab autonomously monitors HuggingFace/arXiv for new SLM breakthroughs.
**Target Frequency**: Weekly Roster Review.
