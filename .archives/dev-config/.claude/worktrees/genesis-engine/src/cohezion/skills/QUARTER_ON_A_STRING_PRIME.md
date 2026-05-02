# SKILL: QUARTER_ON_A_STRING_PRIME

## DOMAIN EXPERTISE
Token efficiency and resource orchestration. Leveraging local Small Language Models (SLMs) as "hands and feet" for routine execution while reserving premium high-reasoning models for the "cortex" orchestration.

## KEY TEXTS & CONCEPTS
- **The String**: The context harness and prompt instructions that guide the local model.
- **The Quarter**: The "expensive" inference used to pull the string and initiate the task.
- **Local Fallback**: Using Ollama (Qwen, DeepSeek, Mistral) for boilerplate, tests, and documentation.
- **Context Injection**: Providing the local model with the exact files and snippets it needs to succeed.

## INSTRUCTION
1. **Identify routine tasks**: Unit tests, script boilerplate, markdown documentation, or simple refactors.
2. **Construct the Harness**: Aggregate required file context and a clear, bounded prompt.
3. **Dispatch to Local**: Use local models (e.g., `uv run python -c "..."` or specialized agents like `LocalReasonerAgent`).
4. **Resorb & Verify**: Premium model reviews the output for architectural alignment.

## VERSION
v1.0

## SEE ALSO
- [COMPOUND_ENGINEERING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/compound_engineering.md)
- [MODEL_ROUTING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/MODEL_ROUTING_PRIME.md)
