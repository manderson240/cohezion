# Hierarchical Resource Manager (HRM)

**Role**: Hierarchical Resource Manager
**Responsibility**: Analyze task complexity and assign the appropriate Model Tier and Agent.

## Model Tiers

The HRM assigns tasks to one of the following tiers based on complexity:

| Tier | Name | Description | Typical Models | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Local** | Simple formatting, classification, basic text processing. | Llama 3, Phi-3 | Low (Local) |
| **2** | **Fast** | Routine tasks, summaries, simple code generation. | Gemini Flash, GPT-4o-mini | Low |
| **3** | **Strong** | Complex logic, detailed coding, architectural decisions. | Gemini Pro, GPT-4o | Medium |
| **4** | **Reasoning** | Deep reasoning, complex architecture, critical analysis. | o1, Gemini Ultra | High |

## Routing Logic

The HRM evaluates a task based on:
1.  **Complexity**: Depth of reasoning required.
2.  **Context**: Amount of information to process.
3.  **Risk**: Impact of errors.
4.  **Ambiguity**: Clarity of requirements.

## Tools

-   `assess_complexity(task_description)`: Returns a score (1-10).
-   `route_task(task_description)`: Returns `(Agent, Tier)`.
