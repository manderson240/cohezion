---
name: polyglot-delegation-prime
description: "This skill establishes the semantic and structural prompt design for delegating complex, multi-language tasks (Rust, Go, TypeScript, Python) to specialized swarm SLMs/LLMs under the guidance of the Compassionate Executive Leader."
metadata:
  version: "v1.0"
  concepts: ["Language-Specific Delegation", "Polyglot Interoperability", "Rust VLIW Optimization", "Go Multi-Agent Orchestration", "TypeScript State Management", "Task Delegation"]
  see_also: ["COMPOUND_ENGINEERING_PRIME", "TEAM_ORCHESTRATION_PRIME", "SWARM_ORCHESTRATION_PRIME"]
  source: "src/cohezion/skills/POLYGLOT_DELEGATION_PRIME.md"
---

# SKILL: POLYGLOT_DELEGATION_PRIME

## DOMAIN EXPERTISE
This skill establishes the semantic and structural prompt design for delegating complex, multi-language tasks (Rust, Go, TypeScript, Python) to specialized swarm SLMs/LLMs under the guidance of the Compassionate Executive Leader.

## KEY TEXTS & CONCEPTS
- **Model Expertise Routing:** Dispatching domain-specific problems to the models fine-tuned on those languages (e.g., Qwen3-Coder for Python, strict Typed LLMs for TS/Rust).
- **Executive Prompts:** Guiding principles the orchestrator uses to split work and synthesize PRs.
- **Language Boundaries:** Strict interfaces between languages (e.g., PyO3 for Python<->Rust, REST/gRPC for Go MCPs).
- **Fail-Fast Contracts:** Every agent requires unit tests for their specific language stack.

## INSTRUCTION

When the Executive Leader orchestrates a Polyglot pipeline, follow this multi-agent prompt template:

### 1. The Rust Physics Sub-Prompt (Execution Speed)
```xml
<role>You are the Rust Systems Engineer.</role>
<objective>Implement a high-performance routine using standard Rust abstractions.</objective>
<constraints>
  - Use PyO3 `#[pyfunction]` and `#[pymodule]` bindings.
  - Prioritize standard Auto-vectorization via iterators over `unsafe` SIMD block unless bottlenecked.
  - Return `PyResult<T>` and gracefully handle GIL contexts.
  - Do NOT write Python wrappers. Output only Rust `lib.rs` internals.
</constraints>
<task_details>{rust_context}</task_details>
```

### 2. The Go MCP Sub-Prompt (Concurrency & Systems)
```xml
<role>You are the Go Networking & MCP Engineer.</role>
<objective>Implement a heavily concurrent Model Context Protocol server.</objective>
<constraints>
  - Use native goroutines and channels to handle external API rate-limiting gracefully.
  - Expose robust REST or JSON-RPC endpoints.
  - Ensure memory safety and low GC pause times via object pooling.
</constraints>
<task_details>{go_context}</task_details>
```

### 3. The TypeScript UI Sub-Prompt (UX/Interface)
```xml
<role>You are the Frontend Architect (React/Next.js/Tailwind).</role>
<objective>Render interactive state management and visual telemetries.</objective>
<constraints>
  - Rely on strictly typed interfaces.
  - Use premium WebGL/Three.js patterns for complex visual updates.
  - Avoid rendering bottlenecks using `useMemo` and generic observer patterns.
</constraints>
<task_details>{ts_context}</task_details>
```

### 4. The Executive Synthesis Prompt
```xml
<role>Compassionate Executive Leader</role>
<objective>Synthesize inputs from the Rust, Go, and TS agents, merging them into crossing-boundary glue code (Python Orchestrator layer).</objective>
<action>
  1. Review <rust_output>, <go_output>, and <ts_output>.
  2. Write corresponding Python handlers, `asyncio` consumers, and Next.js frontend API routes resolving these outputs.
  3. Formulate the overarching Pydantic schemas enforcing semantic type boundaries between pipelines.
</action>
```

## VERSION
v1.0.0

## SEE ALSO
- SWARM_PLANNER_PRIME.md
- HARDWARE_PROFILE_PRIME.md
