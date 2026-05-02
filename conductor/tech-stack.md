# Cohezion Technology Stack

## 1. Core Languages: The Polyglot Mandate
We utilize the right language for the right task to maximize Cohezion, ensuring zero-defect evolution through strict Test-Driven Development (TDD) and full structural traceability.
- **Python (3.13+)**: The primary orchestration, logic, and ML language, strictly managed via `uv` for lightning-fast dependency resolution.
- **Rust (via PyO3)**: Integrated for compute-heavy, high-performance physical simulations (e.g., Magnetohydrodynamics, plasma physics, and 12D state calculations) to ensure maximum compute density and direct substrate integration.
- **TypeScript**: Utilized for the immersive, multimodal frontend interfaces and complex state management in the browser.
- **Go**: Reserved for high-concurrency microservices and routing logic where extreme throughput is required.

## 2. Machine Learning & AI Inference (Subscription-Optimized & Dynamic)
*Note: The AI landscape is highly volatile. We proactively update our model roster based on mission requirements, but we strictly adhere to a zero-additional-API-cost policy by leveraging existing subscriptions and local hardware.*

- **Development & Orchestration (Zero Extra Cost)**:
  - **Anthropic Claude Suite**: Utilizing Claude Code with the newest Opus, Sonnet, and Haiku models via our existing subscription for heavy architectural reasoning, BMAD-METHOD orchestration, and code generation.
  - **Google Gemini 3.0+**: Leveraged via existing subscriptions for multimodal context, advanced reasoning, and CLI orchestration.
- **Execution & Simulation (Dynamic Roster)**:
  - **Local SOTA SLMs**: Rapid adoption and fine-tuning of the latest sub-35B models (e.g., **Gemma 4 31B Dense/26B MoE/E4B/E2B**, Llama 4 Scout, Qwen3-Coder) to maximize performance on our specific UMA hardware (AMD Ryzen with 128GB Unified RAM) for localized agentic (EVO) execution.
  - **Ollama Cloud Models**: Utilizing open-weight models hosted on Ollama Cloud (via existing subscription) for scalable, parallel execution tasks and the "Thinker" layer of the Triune Manifold.
- **Frameworks**: 
  - **PyTorch**: Primary framework for the FLUME VAE (256D continuous thought vectors), custom embedding generation, and local fine-tuning pipelines.
  - **Gymnasium**: Standardized API for reinforcement learning environments (FlumeNav-v0).
  - **Sentence-Transformers**: For high-quality, task-specific local embedding generation.

## 3. Backend & Interoperability
- **Web Framework**: **FastAPI** (Async) for high-performance, concurrent endpoint management.
- **Protocols**: **Universal Commerce Protocol (UCP)**, **Model Context Protocol (MCP)**, and **Agent-to-Agent (A2A)** standardizations to ensure alignment with the Agentic AI Foundation (AAIF).
- **Concurrency**: Deeply integrated Python `asyncio` for non-blocking I/O during agentic execution loops.

## 4. Persistence & The Knowledge Graph
- **Graph/Document Database**: **SurrealDB 3.0** (Async). Chosen for its ability to handle complex relational graphs and document storage simultaneously, essential for full structural traceability and 12D/512D/2048D trajectory indexing.
- **Knowledge Vault**: **Obsidian (via MCP)**. Serves as the persistent, human-readable, and semantically linked memory layer for the swarm.
- **System Telemetry**: **Ouroboros** (System flight recorder) and **Reward & Ratchet** mechanisms log directly to the DB to permanently commit successful skills to the "Root of Trust."

## 5. Quality Assurance & Anti-Workslop Defenses
- **Test-Driven Development (TDD)**: **Pytest** is the core testing framework, enforcing the Red-Green-Refactor cycle.
- **Automated Synthesis**: **Mycelium (ShadowScripter)** organically grows regression tests around newly generated code.
- **Static Analysis & Security**: **Ruff** (formatting/linting) and **Mypy** (strict type checking) ensure the codebase remains free of "workslop", backed by rigorous multi-perspective adversarial reviews.

## 6. Execution, Orchestration & UI
- **Sandboxing**: Container-based isolation using **Docker** to ensure safe, idempotent execution of sovereign agent code.
- **Immersive Interfaces**: React/Three.js (or equivalent) for the 3D manifold visualization layer, and **Tone.js** for real-time HIHO dissonance sonification.
- **Interactive Mentorship**: **Marimo** and **Quarto** for reactive, living research documents that blend live-coding (via Colab/CodeSignal integrations) with deep technical exposition.