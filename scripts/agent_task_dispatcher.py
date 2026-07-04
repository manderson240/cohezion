"""Agent Task Dispatcher — local inference agents claim and execute backlog tasks.

Architecture:
  SurrealDB agent_task table (pending items from fleet_research + teleport)
  → Lemonade :13305 Cohezion-Omni-Dense (Qwen3.6-35B-A3B-MTP backbone, Vulkan)
  → agent claims task, executes via local inference, writes result back

Tool-calling loop: the local model receives pending tasks as context and
calls route_task(task_id, agent_type, reasoning) to dispatch each one.

Cohezion-Omni-Dense is a collection.omni recipe — OmniRouter dispatches:
  - text/chat  → Qwen3.6-35B-A3B-MTP-GGUF (ctx=16384, Vulkan, 3B active params)
  - image gen  → Flux-2-Klein-9B-GGUF
  - TTS        → kokoro-v1
  - STT        → Whisper-Large-v3-Turbo

Usage:
  uv run python scripts/agent_task_dispatcher.py             # dispatch all pending
  uv run python scripts/agent_task_dispatcher.py --dry-run   # preview without claiming
  uv run python scripts/agent_task_dispatcher.py --claim-one # claim and run one task
  uv run python scripts/agent_task_dispatcher.py --status pending
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SURREAL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}
_LEMONADE = "http://localhost:13305"
# Qwen3.6-35B-A3B-NoThinking: 35B Qwen3.6 with thinking disabled. ctx=16384, Vulkan.
# Pure tool-call responses without <think> token overhead. Quality-first for dispatch.
# NOTE: collection.omni (Cohezion-Omni-Dense) requires live HuggingFace API for component
# resolution — use this direct GGUF model for air-gapped reliability.
_DISPATCH_MODEL = "Qwen3.6-35B-A3B-NoThinking"
# Fast path: DeepSeek-Qwen3-8B on Vulkan, ctx=16384 (thinking model — use --fast for small tasks)
_DISPATCH_MODEL_FAST = "DeepSeek-Qwen3-8B-GGUF"
# High-quality: Strix-optimized Q4_K_M, 51 t/s, verified tool-calling
_DISPATCH_MODEL_HQ = "Qwen3.6-35B-A3B-GGUF-Strix-Q4_K_M"
# N3 OOM guard: never load — ctx=0 or ctx=None on heavy models = crash risk
_CTX0_HAZARD_MODELS = {
    "Qwen3.6-35B-A3B-ThinkingCoder",   # known ctx=0 regression (harness N3)
    "gpt-oss-120b-GGUF",               # ctx=None on 120B = unbounded KV
    "gpt-oss-120b-mxfp-GGUF",         # same
    "Qwen3.5-122B-A10B-GGUF",         # 122B — verify ctx before loading
    "Cogito-v2-llama-109B-MoE-GGUF",  # 109B MoE — verify ctx before loading
}

# Tool schema for the local inference model to call
_ROUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "route_task",
        "description": (
            "Dispatch a pending agent_task to the correct specialist agent. "
            "Call this for each task that needs routing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The SurrealDB agent_task ID (e.g. agent_task:abc123)",
                },
                "agent_type": {
                    "type": "string",
                    "enum": [
                        "compound-engineering-specialist",
                        "surreal-dba",
                        "flume-specialist",
                        "hiho-stability-specialist",
                        "vault-keeper",
                        "general-purpose",
                        "autoharness-specialist",
                    ],
                    "description": "Which Cohezion specialist agent should handle this task",
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence explaining why this agent type was chosen",
                },
                "priority_override": {
                    "type": "integer",
                    "description": "Optional priority 1-5 override (1=urgent, 5=low)",
                },
            },
            "required": ["task_id", "agent_type", "reasoning"],
        },
    },
}


def _surreal(sql: str) -> list[dict[str, Any]]:
    r = httpx.post(_SURREAL, content=sql, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=10.0)
    r.raise_for_status()
    return r.json()


def _lemonade_chat(messages: list[dict], tools: list[dict] | None = None, model: str = _DISPATCH_MODEL) -> dict:
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
    # 35B backbone needs up to 120s; fast 8B path stays at 60s
    timeout = 120.0 if "35B" in model or "Omni-Dense" in model or "52B" in model else 60.0
    r = httpx.post(f"{_LEMONADE}/v1/chat/completions", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get_pending_tasks(limit: int = 10) -> list[dict]:
    data = _surreal(f"SELECT id, task_type, payload, status, priority, capability_tags, source_id FROM agent_task WHERE status = 'pending' LIMIT {limit};")
    return data[0].get("result", [])


def _claim_task(task_id: str, agent_type: str) -> bool:
    result = _surreal(
        f"UPDATE {task_id} SET status='in_progress', claimed_by='{agent_type}', updated_at=time::now() WHERE status='pending';"
    )
    rows = result[0].get("result", [])
    return bool(rows and rows[0].get("status") == "in_progress" or rows[0].get("claimed_by") == agent_type if rows else False)


def _complete_task(task_id: str, result_data: dict) -> None:
    result_json = json.dumps(result_data).replace("'", "''")
    _surreal(f"UPDATE {task_id} SET status='completed', result={result_json}, updated_at=time::now();")


def _fail_task(task_id: str, error: str) -> None:
    err = error.replace("'", "''")[:200]
    _surreal(f"UPDATE {task_id} SET status='failed', error='{err}', updated_at=time::now();")


def dispatch_with_local_inference(tasks: list[dict], dry_run: bool = False, model: str = _DISPATCH_MODEL) -> list[dict]:
    """Have Gemma-4-E4B route each pending task to the correct specialist."""
    if not tasks:
        logger.info("No pending tasks")
        return []

    task_summary = "\n".join(
        f"- ID: {t['id']} | tags: {t.get('capability_tags', [])} | "
        f"paper: {str(t.get('payload', {}).get('paper', ''))[:60]}"
        for t in tasks
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Cohezion task dispatcher. Route each pending agent_task "
                "to the most capable specialist agent. Call route_task() for EVERY task listed. "
                "compound-engineering-specialist handles Python code + compound loop work. "
                "surreal-dba handles database schema and queries. "
                "flume-specialist handles embeddings and semantic cache. "
                "hiho-stability-specialist handles physics/bioelectric/manifold work. "
                "vault-keeper handles memory and decision logging. "
                "autoharness-specialist handles tests and verification."
            ),
        },
        {
            "role": "user",
            "content": f"Route these {len(tasks)} pending tasks:\n\n{task_summary}",
        },
    ]

    try:
        response = _lemonade_chat(messages, tools=[_ROUTE_TOOL], model=model)
    except Exception as e:
        logger.error("Lemonade routing failed: %s — falling back to capability_tags", e)
        return _fallback_route(tasks, dry_run)

    dispatched = []
    choice = response.get("choices", [{}])[0]
    tool_calls = choice.get("message", {}).get("tool_calls", [])

    if not tool_calls:
        logger.warning("Lemonade returned no tool calls — using fallback routing")
        return _fallback_route(tasks, dry_run)

    for call in tool_calls:
        args = json.loads(call.get("function", {}).get("arguments", "{}"))
        task_id = args.get("task_id")
        agent_type = args.get("agent_type", "general-purpose")
        reasoning = args.get("reasoning", "")
        priority = args.get("priority_override")

        logger.info("ROUTE %s → %s (%s)", task_id, agent_type, reasoning)

        if dry_run:
            dispatched.append({"task_id": task_id, "agent_type": agent_type, "dry_run": True})
            continue

        claimed = _claim_task(task_id, agent_type)
        if claimed:
            if priority:
                _surreal(f"UPDATE {task_id} SET priority={priority};")
            dispatched.append({"task_id": task_id, "agent_type": agent_type, "claimed": True})
        else:
            logger.warning("Could not claim %s (already taken?)", task_id)

    return dispatched


def _fallback_route(tasks: list[dict], dry_run: bool) -> list[dict]:
    """Route by capability_tags when Lemonade is unavailable."""
    dispatched = []
    for task in tasks:
        tags = task.get("capability_tags", ["general-purpose"])
        agent_type = tags[0] if tags else "general-purpose"
        task_id = task["id"]
        logger.info("FALLBACK ROUTE %s → %s", task_id, agent_type)
        if not dry_run:
            _claim_task(task_id, agent_type)
        dispatched.append({"task_id": task_id, "agent_type": agent_type, "fallback": True})
    return dispatched


def run_one_task(model: str = _DISPATCH_MODEL) -> None:
    """Claim one pending task and execute it via local inference."""
    tasks = _get_pending_tasks(limit=1)
    if not tasks:
        print("No pending tasks")
        return

    task = tasks[0]
    task_id = str(task["id"])
    payload = task.get("payload", {})

    # Claim it
    _claim_task(task_id, f"lemonade:{model}")
    logger.info("Claimed %s", task_id)

    # Execute via local inference
    prompt = (
        f"You are a Cohezion research engineer. Analyze this research item and produce "
        f"a concrete implementation recommendation.\n\n"
        f"Paper: {payload.get('paper', 'unknown')}\n"
        f"Gap: {payload.get('gap', '')}\n"
        f"Recommendation: {payload.get('rec', '')}\n\n"
        f"Produce: (1) one-paragraph technical analysis, (2) top 3 implementation steps, "
        f"(3) which Cohezion module to modify first."
    )

    try:
        response = _lemonade_chat(
            [{"role": "user", "content": prompt}],
            model=model,
        )
        analysis = response["choices"][0]["message"]["content"]
        _complete_task(task_id, {"analysis": analysis, "model": model})
        print(f"✓ Completed {task_id}")
        print(analysis[:500])
    except Exception as e:
        _fail_task(task_id, str(e))
        print(f"✗ Failed {task_id}: {e}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Cohezion agent task dispatcher")
    parser.add_argument("--dry-run", action="store_true", help="Preview routing without claiming")
    parser.add_argument("--claim-one", action="store_true", help="Claim and execute one task via Lemonade")
    parser.add_argument("--model", default=_DISPATCH_MODEL,
                        help=f"Lemonade model (default: {_DISPATCH_MODEL}, hq: {_DISPATCH_MODEL_HQ})")
    parser.add_argument("--fast", action="store_true", help=f"Use fast 8B model ({_DISPATCH_MODEL_FAST}) for routing")
    parser.add_argument("--hq", action="store_true", help=f"Use high-quality Omni-Dense for routing")
    parser.add_argument("--status", default="", help="Show tasks by status (pending/in_progress/completed/failed)")
    args = parser.parse_args()

    if args.status:
        data = _surreal(f"SELECT id, status, claimed_by, task_type, payload.paper FROM agent_task WHERE status='{args.status}' LIMIT 20;")
        rows = data[0].get("result", [])
        print(f"{len(rows)} tasks with status={args.status}")
        for r in rows:
            print(f"  {r['id']} claimed_by={r.get('claimed_by','—')} paper={str(r.get('payload',{}).get('paper',''))[:50]}")
        return

    if args.fast:
        model = _DISPATCH_MODEL_FAST
    elif args.hq:
        model = _DISPATCH_MODEL_HQ
    else:
        model = args.model
    if model in _CTX0_HAZARD_MODELS:
        print(f"ERROR: {model} is in the N3 OOM hazard list. Use a safe model.")
        return

    if args.claim_one:
        run_one_task(model=model)
        return

    tasks = _get_pending_tasks(limit=20)
    print(f"Found {len(tasks)} pending tasks")
    if not tasks:
        return

    dispatched = dispatch_with_local_inference(tasks, dry_run=args.dry_run, model=model)
    print(f"Dispatched {len(dispatched)} tasks{' (dry-run)' if args.dry_run else ''}")
    for d in dispatched:
        print(f"  {d['task_id']} → {d['agent_type']}")


if __name__ == "__main__":
    main()
