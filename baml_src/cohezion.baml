// BAML source of truth for Cohezion LLM calls (adopted 2026-09-08).
// Prompts live here as typed functions; baml_client/ is generated from
// this directory (uv run baml-cli generate) and is type-checked by mypy
// like any other code. Routed through ClientRegistry at runtime — never
// hardcode provider names/ports in call sites (AGENTS.md port-bypass rule).

generator cohezion_target {
  output_type "python/pydantic"
  output_dir ".."
  default_client_mode "sync"
  version "0.226.2"
}

// OpenAI-compatible local endpoints. base_url comes from env at runtime;
// api_key is a placeholder the endpoints ignore but the SDK requires.
client<llm> LemonadeLocal {
  provider "openai-generic"
  options {
    base_url "http://127.0.0.1:13305/api/v1"
    api_key "local"
    model "deepseek-r1-0528-8b-FLM"
  }
}

client<llm> OllamaCloud {
  provider "openai-generic"
  options {
    base_url "http://127.0.0.1:11434/v1"
    api_key "local"
    model "deepseek-v4-pro:cloud"
  }
}

// Runtime routing is via ClientRegistry in Python (baml_py.ClientRegistry) —
// per docs, no static mock provider exists in 0.226.2; tests mock the
// generated client in pytest instead (tests/unit/test_baml_client.py).

class NextStep {
  action string
  rationale string
  risk_level "low" | "medium" | "high"
}

function RecommendNextStep(context: string, candidates: string) -> NextStep {
  client "LemonadeLocal"
  prompt #"
    You are a senior engineer planning the next step for the Cohezion repo.
    Context: {{ context }}
    Candidate actions:
    {{ candidates }}
    Pick the highest-leverage next step. Respond with the action, a one-sentence
    rationale, and a risk level.
  "#
}