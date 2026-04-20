---
stepsCompleted: [1]
inputDocuments: []
workflowType: 'research'
lastStep: 2
research_type: 'technical'
research_topic: 'Marimo reactive notebooks for scientific publications with small local LLMs and cloud AI providers'
research_goals: 'Ensure Cohezion project aligns with best practices for scientific quality publications using reactive marimo notebooks with small local language models (SOTA performance) and cloud providers (Ollama, OpenCode, Claude Code, Gemini CLI)'
user_name: 'Mike-anderson'
date: '2026-03-06'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-03-06
**Author:** Mike-anderson
**Research Type:** technical

---

## Research Overview

This research investigates how marimo reactive notebooks can serve as the scientific publication and experimentation layer for Cohezion's compound AI orchestration platform. The scope extends to integration with small local language models via Ollama, cloud AI providers (Claude Code, Gemini CLI, OpenCode), and concrete implementation patterns using Cohezion's existing MCP server fleet (11 servers on ports 8360-8399).

---

## Technical Research Scope Confirmation

**Research Topic:** Marimo reactive notebooks for scientific publications with small local LLMs and cloud AI providers
**Research Goals:** Ensure Cohezion project aligns with best practices for scientific quality publications using reactive marimo notebooks with small local language models (SOTA performance) and cloud providers (Ollama, OpenCode, Claude Code, Gemini CLI)

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability (with Cohezion MCP servers)
- Performance Considerations - scalability, optimization, patterns
- Implementation Plan - concrete steps for Cohezion integration

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-03-06

---

## Technology Stack Analysis

### Core Platform: marimo Reactive Notebooks

marimo is a reactive Python notebook that models each notebook as a **directed acyclic graph (DAG)** on cells, where edges represent variable dependencies inferred via static analysis. When a cell runs, all descendant cells are automatically executed or marked stale, eliminating the hidden state problem that plagues traditional notebooks.

**Key architectural properties:**

- **Pure Python file format** - notebooks are stored as `.py` files, fully Git-friendly with meaningful diffs
- **Deterministic execution** - cell execution order is determined by the dependency graph, not cell position
- **No hidden state** - deleting a cell scrubs its variables from memory
- **Reproducibility via PEP 723** - dependencies are inlined at the top of notebooks using `uv` integration, ensuring exact package version reproducibility
- **Multiple execution modes** - edit, run, script, WASM deployment
- **SQL first-class** - SQL cells can depend on Python values and execute against dataframes, databases, lakehouses, CSVs, and Google Sheets

**Reproducibility evidence:** A 2019 study found only 24% of nearly 1M Jupyter notebooks on GitHub could be re-run, and just 4% reproduced the same results. marimo's DAG-based execution and dependency serialization directly address this crisis. A Nature-published paper documents these reproducibility features.

_Source: [marimo DAG blog](https://marimo.io/blog/dataflow), [GitHub](https://github.com/marimo-team/marimo), [Real Python](https://realpython.com/marimo-notebook/)_

### Programming Languages and Frameworks

**Primary language: Python 3.12+** - marimo is Python-native, aligning with Cohezion's Python 3.13+ codebase. No language mismatch.

**Key frameworks in the stack:**

| Framework | Role | Cohezion Alignment |
|-----------|------|-------------------|
| **marimo** | Reactive notebook runtime | New addition - research/publication layer |
| **FastAPI** | API server | Already used (Cohezion API on :8080) |
| **aiohttp** | MCP server HTTP layer | Already used (all MCP servers) |
| **mcp (Python SDK)** | Model Context Protocol | Already used (gateway MCP server) |
| **uv** | Package management | Already used (project standard) |
| **Pydantic** | Data validation | Already used (boundary validation) |
| **pytest** | Testing | Already used (3,200+ tests) |

**Emerging framework:** marimo supports **anywidget** for custom interactive widgets, enabling domain-specific research UIs without leaving the notebook.

_Source: [marimo docs](https://docs.marimo.io/), [marimo features](https://marimo.io/features/feat-ai)_

### LLM Providers and Model Configuration

marimo has **native multi-provider LLM support** with three model roles:

| Role | Purpose | Recommended Config |
|------|---------|-------------------|
| `chat_model` | Chat panel / research Q&A | `ollama/qwen3-coder:30b` (local) or `anthropic/claude-opus-4-6` (cloud) |
| `edit_model` | Cell refactoring / AI generation | `ollama/deepseek-r1:70b` (local) or `openai/gpt-4o` (cloud) |
| `autocomplete_model` | Inline code completion | `ollama/phi3:mini` (local, fast) |

**Ollama configuration (local models):**
```toml
[ai.models]
chat_model = "ollama/qwen3-coder:30b"
edit_model = "ollama/deepseek-r1:70b"
autocomplete_model = "ollama/phi3:mini"

[ai.ollama]
base_url = "http://127.0.0.1:11434/v1"
```

**Anthropic configuration (cloud):**
```toml
[ai.models]
chat_model = "anthropic/claude-3-7-sonnet-latest"

[ai.anthropic]
api_key = "sk-ant-..."
```

**Google Gemini configuration:**
```toml
[ai.models]
chat_model = "google/gemini-2.5-pro"

[ai.google]
api_key = "AI..."
```

**Custom OpenAI-compatible providers** (DeepSeek, Mistral, Together AI, xAI, LM Studio):
```toml
[ai.models]
chat_model = "deepseek/deepseek-chat"

[ai.custom_providers.deepseek]
api_key = "dsk-..."
base_url = "https://api.deepseek.com/"
```

_Source: [marimo LLM providers](https://docs.marimo.io/guides/configuration/llm_providers/)_

### Small Local Language Models - SOTA for Strix Halo Hardware

Cohezion runs on AMD Ryzen AI MAX+ 395 with 128 GiB LPDDR5X unified memory. This enables running models up to 70B parameters (4-bit quantized ~40GB) with headroom for the OS, SurrealDB, and MCP servers.

**Recommended model tier for scientific research:**

| Model | Size | VRAM (Q4) | Strength | Use Case |
|-------|------|-----------|----------|----------|
| **DeepSeek-R1:70B** | 70B | ~40GB | Math, reasoning, STEM | Complex analysis, paper drafts |
| **Qwen3-Coder:30B** | 30B | ~18GB | Code generation, refactoring | Notebook cell generation |
| **Phi-4 Mini** | 3.8B | ~3GB | Fast inference, RAG | Autocomplete, quick lookups |
| **Llama 3.2 3B** | 3B | ~2.5GB | General instruction-following | Light tasks, classification |
| **Gemma3 4B** | 4B | ~3GB | Balanced quality/speed | Fallback, experimentation |

**Performance on Strix Halo:** With the Radeon 8060S iGPU and unified memory, Ollama can offload model layers to the iGPU automatically. Expect 15-25 tokens/sec on 7B models, 8-12 tokens/sec on 30B, and 3-6 tokens/sec on 70B (all at Q4 quantization).

**Key insight:** Open-weight models now trail proprietary SOTA by only ~3 months (Epoch AI). Fine-tuning smaller models on domain-specific data produces results that generic frontier models cannot replicate, at far lower serving cost.

_Source: [DataCamp top SLMs 2026](https://www.datacamp.com/blog/top-small-language-models), [Best Mini PC for Ollama 2026](https://www.mayhemcode.com/2026/02/best-mini-pc-for-ollama-and-local-llms.html), [BentoML open-source LLMs](https://www.bentoml.com/blog/navigating-the-world-of-open-source-large-language-models)_

### AI CLI Coding Tools Landscape (2026)

The three primary AI coding CLI tools relevant to Cohezion workflows:

| Tool | Context Window | Free Tier | Best For |
|------|---------------|-----------|----------|
| **Claude Code** | 1M tokens (Opus 4.6) | $20/mo subscription | Autonomous coding, complex refactors (80.8% SWE-bench) |
| **Gemini CLI** | 1M tokens (Gemini 2.5 Pro) | 1,000 req/day free | Planning, spec writing, cost-effective bulk work |
| **OpenCode** | Varies (75+ providers) | Free (open source) | Provider flexibility, local model support, zero API cost |

**Emerging consensus:** Claude Code for serious implementation, Gemini CLI for planning/specification, OpenCode for flexibility and local model workflows. All three support MCP, making them natural consumers of both Cohezion's and marimo's MCP servers.

_Source: [Educative comparison](https://www.educative.io/blog/claude-code-vs-codex-vs-gemini-code-assist), [sanj.dev comparison](https://sanj.dev/post/comparing-ai-cli-coding-assistants), [DEV Community review](https://dev.to/mendesbarreto/opencode-vs-claude-code-vs-copilot-vs-gemini-very-simple-review-1dpm)_

### Database and Storage Technologies

**Current Cohezion stack (no changes needed):**

| Technology | Role | marimo Integration |
|------------|------|-------------------|
| **SurrealDB v3.0** | Primary database (ws://localhost:8000) | marimo SQL cells can query SurrealDB directly |
| **Redis** | Caching layer (semantic cache L1/L2/L3) | No direct marimo integration needed |
| **JSONL** | Session persistence, metrics | marimo can read/write JSONL as data sources |
| **Git** | Version control | marimo `.py` format enables meaningful diffs |

**marimo SQL integration:** SQL cells in marimo can execute against databases, including SurrealDB via WebSocket, enabling direct querying of Cohezion's knowledge graph, journey data, and skill registries from within research notebooks.

### Cloud Infrastructure and Deployment

**marimo deployment options for scientific publications:**

| Method | Use Case | Cost |
|--------|----------|------|
| **HTML export** | Static publication artifacts | Free |
| **WASM deployment** | Interactive browser-based papers | Free (GitHub Pages) |
| **molab** | Cloud-hosted interactive notebooks | Free tier available |
| **Docker container** | Self-hosted with Cohezion stack | Existing infra |

**Cohezion alignment:** marimo notebooks can be exported as HTML for publication, deployed as WASM apps on GitHub Pages for interactive supplementary materials, or run alongside the existing Cohezion docker-compose stack.

### Technology Adoption Trends

- **Reactive notebooks replacing Jupyter** - marimo, Observable, and Pluto.jl represent the next generation; marimo leads in Python ecosystem
- **Local-first AI** - Ollama adoption accelerating; unified memory architectures (like Strix Halo) make 70B models practical on workstations
- **MCP as universal protocol** - MCP is becoming the standard for AI tool integration; marimo, Claude Code, Gemini CLI, and OpenCode all support it
- **uv as Python standard** - PEP 723 inline dependencies + uv lockfiles are becoming the reproducibility standard

_Source: [Towards Data Science marimo switch](https://towardsdatascience.com/why-im-making-the-switch-to-marimo-notebooks/), [marimo MCP docs](https://docs.marimo.io/guides/editor_features/mcp/)_

<!-- Content will be appended sequentially through research workflow steps -->
