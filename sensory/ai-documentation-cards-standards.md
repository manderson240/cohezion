---
title: "AI Documentation Cards: Model Cards, System Cards, Agent Cards, and Embedding Cards"
date: 2026-03-05
tags: [ai-safety, documentation, standards, model-card, system-card, agent-card, governance]
aspect: knower
neural:
  activation: 0.71
  stage: growing
  synapse_in: 0
  synapse_out: 4
---

# AI Documentation Cards: Standards Landscape

> [!abstract] Summary
> Comprehensive survey of structured documentation formats for AI systems — model cards, system cards, agent cards, and embedding cards. Covers origins, standard sections, and emerging interoperability protocols. Informs Cohezion's card system in `specs/`.

## Model Cards

**Origin:** Google Research, 2018 ([Mitchell et al., "Model Cards for Model Reporting"](https://arxiv.org/abs/1810.03993))

Standard 9-section structure: Model Details, Intended Use, Factors, Metrics, Evaluation Data, Training Data, Quantitative Analyses, Ethical Considerations, Caveats & Recommendations.

**De facto standard:** [Hugging Face Annotated Template](https://huggingface.co/docs/hub/en/model-card-annotated) extends with environmental impact, model examination, societal impact, and YAML metadata headers.

**Adopted by:** Hugging Face (all models), Meta (LLaMA), Google, academic ML community.

## System Cards

**Origin:** OpenAI (GPT-4, 2023), Anthropic (Claude 3, 2024). Distinguish from model cards by documenting the entire **deployed system** — model + safety mitigations, guardrails, deployment context, and risk evaluations.

Key differences from model cards:
- 20-200+ pages (vs 1-5 for model cards)
- Safety evaluations are primary focus (red teaming, CBRN, cyber, autonomy)
- Preparedness/RSP frameworks
- Third-party audits standard
- Alignment evaluations (scheming, deception, self-preservation)
- Model welfare (Anthropic, since Claude 4)

**Anthropic structure:** Introduction → Capabilities → Safeguards → Alignment → Agentic Safety → RSP Evaluations
**OpenAI structure:** Introduction → Training → Risk Assessment → Third-Party Assessments → Societal Impacts

**References:**
- [Anthropic System Cards Index](https://www.anthropic.com/system-cards)
- [OpenAI GPT-4o System Card](https://openai.com/index/gpt-4o-system-card/)

## Agent Cards

Two emerging standards:

### A2A Protocol Agent Card (Google / Linux Foundation)

Machine-readable JSON "business card" for agent capability discovery and interoperability. Published at `/.well-known/agent.json`. Part of the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/latest/specification/).

Required fields: `name`, `url`, `version`, `capabilities`, `skills`, `authentication`.

Supported by 50+ partners (Atlassian, Salesforce, SAP, LangChain, MongoDB, ServiceNow).

### MICAI 2025 Agent Cards (Academic)

Documentation standard for transparency and governance. Sections: Agent Identity, Roles, Memory Taxonomy, Tool Integrations, Communication Protocols, Monitoring Hooks, Governance Scope, Evaluation Metrics.

### NIST AI Agent Standards Initiative

[Announced February 2026](https://www.nist.gov/caisi/ai-agent-standards-initiative). Still in early stages — guidelines for secure, interoperable AI agents. May merge A2A and documentation perspectives.

## Embedding Cards

No formal standard. MTEB `ModelMeta` schema is the de facto standard.

Key embedding-specific fields: `embed_dim`, `similarity_fn_name`, `max_tokens`, `languages`, `n_parameters`, `training_datasets` (contamination tracking), `use_instructions` (query vs document prefixes).

**Reference:** [MTEB GitHub](https://github.com/embeddings-benchmark/mteb)

## Cross-Card Comparison

| Feature | Model Card | System Card | A2A Agent Card | Embedding Card |
|---------|------------|-------------|----------------|----------------|
| **Format** | Markdown + YAML | PDF/HTML | JSON | Markdown + YAML |
| **Length** | 1-5 pages | 20-200+ pages | ~50 lines | 1-5 pages |
| **Primary audience** | ML practitioners | Safety teams | Other AI agents | Search engineers |
| **Safety focus** | Brief ethics | Primary focus | None | Minimal |
| **Machine-readable** | YAML header | No | Fully | YAML + Pydantic |
| **Standardization** | Google 2018 + HF | Ad hoc per company | Linux Foundation | MTEB (de facto) |

## Relevance to Cohezion

Cohezion adapts all four card types as structured vault notes in `specs/`:
- `specs/systems/` — System cards (infrastructure components)
- `specs/models/` — Model cards (AI models we use)
- `specs/agents/` — Agent cards (agent definitions)
- `specs/embeddings/` — Embedding cards (embedding models and indexes)

Templates inspired by Anthropic system cards (safety/alignment sections), Hugging Face model cards (structured metadata), A2A agent cards (capability discovery), and MTEB (embedding metrics).

## Related

- [[2026-03-05-vault-as-system-of-record]] — ADR establishing the specs directory
- [[ai-safety-alignment]] — AI safety and alignment concepts
- [[agentic-ai]] — Agent architecture concepts
- [[semantic-search]] — Embedding-based search

## Primary Sources

- [Model Cards for Model Reporting (Google, 2018)](https://arxiv.org/abs/1810.03993)
- [Hugging Face Annotated Model Card Template](https://huggingface.co/docs/hub/en/model-card-annotated)
- [Anthropic System Cards](https://www.anthropic.com/system-cards)
- [OpenAI System Cards](https://openai.com/index/gpt-4o-system-card/)
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [NIST AI Agent Standards Initiative](https://www.nist.gov/caisi/ai-agent-standards-initiative)
- [MTEB (Massive Text Embedding Benchmark)](https://github.com/embeddings-benchmark/mteb)
- [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/)
