---
title: "Prompt Engineering"
date: 2026-02-07
tags: [concept, context-management, agent-loop-architecture, agentic-ai]
---

## Definition

The discipline of crafting AI inputs to elicit desired responses, pioneered by Brown et al.'s GPT-3 few-shot learning (NeurIPS 2020) and Wei et al.'s chain-of-thought prompting (2022). GPT-3 (175B parameters) demonstrated that scaling enables in-context learning through task demonstrations, while chain-of-thought showed intermediate reasoning steps improve complex task performance by 10-40%.

## Key Properties

- Few-shot: 1-5 labeled examples steer models without fine-tuning
- Chain-of-thought: intermediate reasoning steps improve accuracy 10-40% on arithmetic and reasoning
- Self-consistency: multiple reasoning paths with majority vote for robustness
- Advanced techniques include meta-prompting, role-based prompting, and zero-shot instructions
- 2024 research cataloged 50+ distinct text-based and 40 multimodal prompting techniques

## Examples

- Chain-of-thought: GPT-3 with 8 CoT exemplars achieves 94.6% on GSM8K math, surpassing fine-tuned GPT-3
- Few-shot domain transfer: 3-4 medical diagnosis examples enable GPT-3 to generalize to new patient scenarios

## Primary Sources

- Tom B. Brown, Benjamin Mann, Nick Ryder et al. (2020). *Language Models are Few-Shot Learners*. [https://arxiv.org/abs/2005.14165](https://arxiv.org/abs/2005.14165)
- Jason Wei, Xuezhi Wang et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. [https://arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)
- DAIR.AI Community (2024). *Prompt Engineering Guide*. [https://www.promptingguide.ai/](https://www.promptingguide.ai/)

## Related Papers

- [[few-shot-prompting-agentic-coding]]
- [[testing-agent-skills-with-evals]]
- [[emoticons-llm-silent-failures]]

## Related Concepts

- [[context-management]]
- [[agent-loop-architecture]]
- [[agentic-ai]]

## Relevance to Cohezion

Prompt engineering techniques directly inform how Cohezion's ContextEngineeringInfrastructure constructs prompts for CompoundExecutor agents, using chain-of-thought and few-shot principles via log_decision's structured reasoning traces. The vault's stored decision logs and patterns serve as in-context learning examples, while context management strategies help optimize information payloads delivered to agents within their context windows.
