---
title: "Prompt Engineering"
date: 2026-02-07
tags: [concept, context-management, agent-loop-architecture, agentic-ai]
related_concepts: [context-management, agent-context, transformer-architecture, tool-use, compound-engineering]
aspect: knower
neural:
  activation: 0.82
  stage: mature
  synapse_in: 14
  synapse_out: 11
---

## Definition

The discipline of crafting AI inputs to elicit desired responses, pioneered by Brown et al.'s GPT-3 few-shot learning (NeurIPS 2020) and Wei et al.'s chain-of-thought prompting (2022). GPT-3 (175B parameters) demonstrated that scaling enables in-context learning through task demonstrations, while chain-of-thought showed intermediate reasoning steps improve complex task performance by 10-40%.

Prompt engineering has rapidly matured from ad-hoc techniques into a systematic discipline. As of 2025, comprehensive surveys catalog over 200 distinct prompting techniques across text, multimodal, and agent-based contexts.

## Taxonomy of Techniques

The Prompt Report (Schulhoff et al., 2025) provides the most comprehensive taxonomy, organizing 58 LLM prompting techniques and 40 multimodal techniques into major categories:

| Category | Techniques | Description |
|----------|------------|-------------|
| **In-Context Learning** | Few-shot, one-shot, zero-shot | Providing examples or instructions within the prompt |
| **Thought Generation** | Chain-of-thought, tree-of-thought, graph-of-thought | Eliciting explicit reasoning steps |
| **Decomposition** | Least-to-most, plan-and-solve, skeleton-of-thought | Breaking complex tasks into subtasks |
| **Ensembling** | Self-consistency, universal self-consistency | Running multiple reasoning paths and aggregating |
| **Self-Criticism** | Self-refine, reflexion, chain-of-verification | Having the model critique and improve its own output |

A complementary taxonomy by Liu et al. (Frontiers of Computer Science, 2026) organizes techniques along four aspects: **profile and instruction** (task framing), **knowledge** (domain context), **reasoning and planning** (logical structure), and **reliability** (bias reduction and output stability).

## Key Properties

- **Few-shot**: 1-5 labeled examples steer models without fine-tuning
- **Chain-of-thought**: Intermediate reasoning steps improve accuracy 10-40% on arithmetic and reasoning
- **Self-consistency**: Multiple reasoning paths with majority vote for robustness
- **Meta-prompting**: Prompts that instruct the model on how to construct its own prompts
- **Role-based prompting**: Assigning personas or expert roles to shape response style and expertise
- **Structured output**: Constraining model output to specific formats (JSON, XML, tables) for programmatic consumption
- **Tool-augmented prompting**: Prompts that enable models to use external [[tool-use|tools]] (calculators, search, code execution) as part of their reasoning

## Examples

- Chain-of-thought: GPT-3 with 8 CoT exemplars achieves 94.6% on GSM8K math, surpassing fine-tuned GPT-3
- Few-shot domain transfer: 3-4 medical diagnosis examples enable GPT-3 to generalize to new patient scenarios
- Self-consistency: Running 40 reasoning chains with majority vote improves GSM8K accuracy from 56.5% to 74.4% with PaLM-540B
- Tree-of-thought: Exploring multiple reasoning branches enables solving the Game of 24 at 74% vs. 4% with standard prompting

## Primary Sources

- Tom B. Brown, Benjamin Mann, Nick Ryder et al. (2020). *Language Models are Few-Shot Learners*. [https://arxiv.org/abs/2005.14165](https://arxiv.org/abs/2005.14165)
- Jason Wei, Xuezhi Wang et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. [https://arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)
- Sander Schulhoff et al. (2025). *The Prompt Report: A Systematic Survey of Prompting Techniques*. [https://arxiv.org/abs/2406.06608](https://arxiv.org/abs/2406.06608)
- Pranab Sahoo et al. (2025). *A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications*. [https://arxiv.org/abs/2402.07927](https://arxiv.org/abs/2402.07927)
- Liu et al. (2026). *A Comprehensive Taxonomy of Prompt Engineering Techniques for Large Language Models*. Frontiers of Computer Science, Vol. 20. [https://link.springer.com/article/10.1007/s11704-025-50058-z](https://link.springer.com/article/10.1007/s11704-025-50058-z)
- DAIR.AI Community (2024). *Prompt Engineering Guide*. [https://www.promptingguide.ai/](https://www.promptingguide.ai/)

## Related Papers

- [[few-shot-prompting-agentic-coding]]
- [[testing-agent-skills-with-evals]]
- [[emoticons-llm-silent-failures]]

## Related Concepts

- [[context-management]] -- prompt engineering operates within context window constraints
- [[agent-loop-architecture]] -- agentic systems compose prompts dynamically across loop iterations
- [[agentic-ai]] -- prompt engineering is the primary interface for directing agent behavior
- [[self-attention-mechanism]] -- the transformer mechanism that processes prompts at the model level
- [[transformer-architecture]] -- the underlying architecture that prompt engineering targets
- [[tool-use]] -- tool-augmented prompting enables models to call external tools as part of reasoning
- [[token-efficiency]] -- prompt optimization directly impacts token budget usage

## Relevance to Cohezion

Prompt engineering techniques directly inform how Cohezion's ContextEngineeringInfrastructure constructs prompts for CompoundExecutor agents, using chain-of-thought and few-shot principles via log_decision's structured reasoning traces. The vault's stored decision logs and patterns serve as in-context learning examples, while [[context-management]] strategies help optimize information payloads delivered to agents within their context windows.

In the Cohezion framework, prompt engineering is not a one-time activity but a continuous optimization loop. Agent prompts are versioned, tested via [[concept-testing|evals]], and refined based on observed output quality. The vault itself functions as a retrieval-augmented generation (RAG) knowledge base, where concept notes are injected into agent prompts as grounding context.

## Skills

- BATCHING_PROTOCOL_PRIME -- High-density prompt consolidation
- compound_prompt -- Compound prompt orchestration
- EXTERNAL_RESEARCH_PRIME -- API hygiene for research extraction
- SYSTEM_DEFINITION_PRIME -- System rules file optimization
