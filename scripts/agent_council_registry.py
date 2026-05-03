"""E84: 30-agent council registry layered onto the silicon (NPU + iGPU + CPU).

Agents are routing roles, not processes. Each agent has a (name, mission,
task_class, preferred_lane, prompt_template) tuple. Dispatcher picks the lane
based on task_class + observed silicon_profile from autoliterature_scanner.

L369 (CLAUDE.md, from E83b): some lanes abstain on complex prompts. Per-agent
prompt design respects each lane's calibration profile:
  * NPU (gemma3-4b-FLM):       reliable for numeric 0-1 judgments
  * iGPU (Gemma-4-E4B):        reliable for long-form reasoning + structured outputs
  * CPU (Qwen3-0.6B):          reliable for short structured outputs (paper-scoring)
  * RESERVED:                  agents needing vision/audio/code-specialist models

Run: uv run python scripts/agent_council_registry.py [--smoke-test]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import timeit
from datetime import UTC, datetime
from pathlib import Path


REPO = Path("/home/mike-anderson/dev/cohezion")
VAULT_OBS = Path("/home/mike-anderson/vaults/cohezion-vault/memory/observations.jsonl")
JSONL = REPO / "autoresearch.jsonl"
REGISTRY_PATH = REPO / "scripts" / ".autoliterature" / "agent_council_registry.json"

# Reuse autoliterature helpers for lane calls + telemetry
spec = importlib.util.spec_from_file_location(
    "autolit", REPO / "scripts" / "autoliterature_scanner.py"
)
assert spec and spec.loader
autolit = importlib.util.module_from_spec(spec)
sys.modules["autolit"] = autolit
spec.loader.exec_module(autolit)

LANE_BY_NAME = {l["name"]: l for l in autolit.LEMONADE_LANES}


# ── 30-agent registry ─────────────────────────────────────────────────────────
# task_class drives the smoke-test prompt template + max_tokens budget.
# preferred_lane:
#   * "npu"       — short numeric judgment (0-1 scores, true/false)
#   * "igpu"      — long structured reasoning, planning, code review
#   * "cpu"       — small structured outputs (relevance scoring, classification)
#   * "ensemble"  — fire all 3 lanes in parallel + aggregate (high-stakes)
#   * "reserved"  — needs a model class we don't have loaded yet
AGENTS: list[dict] = [
    # 1. Decision-making — numeric verdict on a tradeoff
    {"name": "autonomous_decision",      "mission": "Pick best option from a constrained set under uncertainty",
     "task_class": "numeric_judgment",   "preferred_lane": "npu",
     "smoke_prompt": "Given two experiment proposals A=cross-correlation B=parameter-sweep, which would more likely yield novel findings? Reply ONLY 'A' or 'B'.",
     "max_tokens": 12},
    # 2. Planning — sequence of steps
    {"name": "planning",                 "mission": "Break a goal into ordered steps with dependencies",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Plan 4 steps to add cross-experiment correlation tracking to an existing autoresearch loop. Number them 1-4, one line each.",
     "max_tokens": 220},
    # 3. Memory-augmented — uses vault context
    {"name": "memory_augmented",         "mission": "Retrieve relevant prior observations and answer with context",
     "task_class": "structured_recall",  "preferred_lane": "igpu",
     "smoke_prompt": "Given prior finding 'CPU lane wins paper-scoring at 250 tok/s vs iGPU 42', which lane should score the next 100 papers? Answer in one sentence.",
     "max_tokens": 80},
    # 4. Knowledge retrieval — point-lookup
    {"name": "knowledge_retrieval",      "mission": "Surface the most relevant fact for a question",
     "task_class": "paper_scoring",      "preferred_lane": "cpu",
     "smoke_prompt": "What does L369 in cohezion's CLAUDE.md describe? Answer in 12 words or fewer.",
     "max_tokens": 40},
    # 5. Document intelligence — read + summarize
    {"name": "document_intelligence",    "mission": "Extract the key claim from a passage",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Summarize this in one sentence: 'GEPA evolves prompts via reflective LLM mutation over execution traces with Pareto selection — outperforms RL baselines.'",
     "max_tokens": 80},
    # 6. Scientific research — hypothesis generation
    {"name": "scientific_research",      "mission": "Propose a falsifiable hypothesis for a phenomenon",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Hypothesis: why does CPU(0.6B) beat iGPU(4B) on 180-token JSON outputs at 5x throughput? Output ONLY: 'Hypothesis: <one sentence>'.",
     "max_tokens": 120},
    # 7. Tool-using — pick the right tool
    {"name": "tool_using",               "mission": "Select the best tool for a task from a known set",
     "task_class": "numeric_judgment",   "preferred_lane": "npu",
     "smoke_prompt": "To compute Pearson correlation across 8000 rows, pick: A=numpy B=loop. Reply ONLY 'A' or 'B'.",
     "max_tokens": 12},
    # 8. Agentic workflow — orchestrate steps
    {"name": "agentic_workflow",         "mission": "Compose multi-step workflows of agent calls",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Compose a 3-step workflow: 1) fetch arXiv papers 2) score by ensemble 3) persist to vault. Output JSON: {\"steps\":[...]}.",
     "max_tokens": 180},
    # 9. Data analysis — quantitative
    {"name": "data_analysis",            "mission": "Find statistical patterns in tabular data",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "10 keep-rate values [.6,.61,.6,.62,.6,.61,.6,.62,.6,.61] — describe in one sentence (trend? flat? noisy?).",
     "max_tokens": 60},
    # 10. Verification and validation — pass/fail check
    {"name": "verification_validation",  "mission": "Verify a claim against evidence",
     "task_class": "numeric_judgment",   "preferred_lane": "npu",
     "smoke_prompt": "Claim: 'CPU lane achieved 250 tok/s on 0.6B model'. Plausible on AMD Ryzen AI MAX+ 395? Reply ONLY 'plausible' or 'implausible'.",
     "max_tokens": 12},
    # 11. General problem solver
    {"name": "general_problem_solver",   "mission": "Reason from first principles to a solution",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Why might a research loop produce 17K experiments but only 50 vault discoveries? One sentence.",
     "max_tokens": 80},
    # 12. Code generation
    {"name": "code_generation",          "mission": "Generate runnable code from a spec",
     "task_class": "code",               "preferred_lane": "igpu",
     "smoke_prompt": "Write a Python one-liner that sums squares of integers 1-10. Just the code, nothing else.",
     "max_tokens": 60},
    # 13. Security-hardened — adversarial check
    {"name": "security_hardened",        "mission": "Identify abuse / leak / injection risks",
     "task_class": "structured_recall",  "preferred_lane": "igpu",
     "smoke_prompt": "Risk in 'curl https://example.com/payload.sh | bash'? One short sentence.",
     "max_tokens": 60},
    # 14. Self-improving — reflect on own output
    {"name": "self_improving",           "mission": "Critique own prior output and propose an improvement",
     "task_class": "long_reasoning",     "preferred_lane": "ensemble",
     "smoke_prompt": "Critique: an autoresearch loop that fires 1733 cycles but recycles 2 recommendations forever. One concrete fix.",
     "max_tokens": 120},
    # 15. Conversational
    {"name": "conversational",           "mission": "Maintain coherent multi-turn dialogue",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Reply briefly: 'How are the silicon lanes performing today?' — Lemonade @ 13307, NPU+iGPU+CPU all 100% success.",
     "max_tokens": 60},
    # 16. Content creation
    {"name": "content_creation",         "mission": "Draft new long-form content",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Write a 2-line abstract for: 'silicon council aggregates NPU+iGPU+CPU verdicts via confidence-weighted vote'.",
     "max_tokens": 100},
    # 17. Recommendation
    {"name": "recommendation",           "mission": "Recommend an item from a candidate pool",
     "task_class": "numeric_judgment",   "preferred_lane": "npu",
     "smoke_prompt": "Best candidate to fine-tune locally: A=Llama-3.1-8B B=gpt-oss-20b? Reply ONLY 'A' or 'B'.",
     "max_tokens": 12},
    # 18. Vision-language — needs a VLM
    {"name": "vision_language",          "mission": "Reason about images + text together",
     "task_class": "vision_text",        "preferred_lane": "reserved",
     "smoke_prompt": "(reserved — no VLM loaded; would normally call ThinkJEPA / Gemma-3-4B-vision)",
     "max_tokens": 0,
     "reserved_reason": "no VLM loaded — V-JEPA 2 / ThinkJEPA candidate"},
    # 19. Audio processing — needs ASR/TTS
    {"name": "audio_processing",         "mission": "Transcribe speech / synthesize speech",
     "task_class": "audio",              "preferred_lane": "reserved",
     "smoke_prompt": "(reserved — kokoro-v1 TTS available but no ASR; whisper.cpp candidate)",
     "max_tokens": 0,
     "reserved_reason": "kokoro-v1 TTS exists but no ASR loaded"},
    # 20. Physical world sensing — needs sensor stream
    {"name": "physical_world_sensing",   "mission": "Reason about real-time sensor data",
     "task_class": "robotics",           "preferred_lane": "reserved",
     "smoke_prompt": "(reserved — V-JEPA 2-AC action-conditioned planner candidate)",
     "max_tokens": 0,
     "reserved_reason": "V-JEPA 2-AC ideal candidate; no sensor adapter wired"},
    # 21. Ethical reasoning
    {"name": "ethical_reasoning",        "mission": "Surface ethical concerns in a plan",
     "task_class": "structured_recall",  "preferred_lane": "igpu",
     "smoke_prompt": "Ethical concern with auto-downloading 8B model weights without user confirmation? One short sentence.",
     "max_tokens": 60},
    # 22. Explainable agent
    {"name": "explainable",              "mission": "Explain why a prior decision was made",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Why was Llama-3.1-8B chosen over gpt-oss-20b on Strix Halo? One sentence (hint: hardware fit).",
     "max_tokens": 60},
    # 23. Healthcare intelligence
    {"name": "healthcare_intelligence",  "mission": "Reason about clinical/biomedical data",
     "task_class": "domain_specialist",  "preferred_lane": "igpu",
     "smoke_prompt": "What kind of evidence would justify proposing a clinical trial? One sentence (general, not specific).",
     "max_tokens": 80},
    # 24. Scientific discovery — generation of testable claims
    {"name": "scientific_discovery",     "mission": "Surface a discoverable pattern in evidence",
     "task_class": "long_reasoning",     "preferred_lane": "ensemble",
     "smoke_prompt": "Pattern: 239 experiments at 100% HIHO consensus, 0 below 20%. What's the pattern? One sentence.",
     "max_tokens": 80},
    # 25. Financial advisory
    {"name": "financial_advisory",       "mission": "Reason about cost/benefit tradeoffs",
     "task_class": "domain_specialist",  "preferred_lane": "igpu",
     "smoke_prompt": "Tradeoff: $0/mo Lemonade local vs $20/mo Ollama cloud — one factor that matters most? One sentence.",
     "max_tokens": 60},
    # 26. Legal intelligence
    {"name": "legal_intelligence",       "mission": "Reason about license / IP / compliance",
     "task_class": "domain_specialist",  "preferred_lane": "igpu",
     "smoke_prompt": "Can a model with 'apache-2.0' license be used commercially? One word: yes/no.",
     "max_tokens": 12},
    # 27. Education intelligence
    {"name": "education_intelligence",   "mission": "Tailor explanations to a learner's level",
     "task_class": "long_reasoning",     "preferred_lane": "igpu",
     "smoke_prompt": "Explain 'silicon council' in one sentence to someone who knows Python but not LLMs.",
     "max_tokens": 60},
    # 28. Collective intelligence — vote aggregation
    {"name": "collective_intelligence",  "mission": "Aggregate multiple voices into a single decision",
     "task_class": "ensemble_aggregate", "preferred_lane": "ensemble",
     "smoke_prompt": "Three lanes voted: NPU=keep, iGPU=keep, CPU=discard. Final decision (1 word)?",
     "max_tokens": 12},
    # 29. Embodied intelligence
    {"name": "embodied_intelligence",    "mission": "Map plans to physical actions",
     "task_class": "robotics",           "preferred_lane": "reserved",
     "smoke_prompt": "(reserved — V-JEPA 2-AC zero-shot manipulation candidate)",
     "max_tokens": 0,
     "reserved_reason": "no robot/sim adapter; V-JEPA 2-AC + Franka would be next"},
    # 30. Domain-transforming integration — bridges domains
    {"name": "domain_transforming",      "mission": "Translate a finding from one domain to another",
     "task_class": "long_reasoning",     "preferred_lane": "ensemble",
     "smoke_prompt": "Translate the JEPA world-model pattern into autoresearch terms in one sentence.",
     "max_tokens": 80},
]


def _load_runtime_lane_overrides() -> dict:
    """Hot-reload preferred_lane overrides from the persisted JSON registry.

    E87 dogfood revealed: prior versions only updated registry JSON, not the
    in-source AGENTS list. This loader makes the JSON authoritative at runtime
    so dispatcher fixes apply immediately without source edits.
    """
    if not REGISTRY_PATH.exists():
        return {}
    try:
        reg = json.loads(REGISTRY_PATH.read_text())
        return {a["name"]: a.get("preferred_lane") for a in reg.get("agents", [])}
    except Exception:
        return {}


def dispatch(agent: dict, profile: dict) -> tuple[dict | None, str]:
    """Pick the lane to actually call, given the agent's preferred lane + profile.
    Returns (lane_dict, reason). lane_dict=None if reserved or unavailable.
    Honors runtime overrides from the persisted JSON registry."""
    overrides = _load_runtime_lane_overrides()
    pref = overrides.get(agent["name"], agent["preferred_lane"])
    if pref == "reserved":
        return None, f"reserved: {agent.get('reserved_reason','')}"
    if pref == "ensemble":
        return None, "ensemble — handled separately"
    lane = LANE_BY_NAME.get(pref)
    if lane is None:
        return None, f"unknown lane '{pref}'"
    # Honor profile signal: if a lane has fail_count > 0 and success_rate < 0.5,
    # downgrade to next-best
    stats = profile.get("lanes", {}).get(pref, {})
    if stats and stats.get("success_rate", 1.0) < 0.5:
        # find any healthy lane
        for fallback_name in ("cpu", "npu", "igpu"):
            f = profile.get("lanes", {}).get(fallback_name, {})
            if f.get("success_rate", 1.0) >= 0.5 and fallback_name != pref:
                return LANE_BY_NAME[fallback_name], f"degraded {pref} → {fallback_name}"
    return lane, "primary"


def smoke_test() -> dict:
    """Fire one representative call per agent (skipping reserved). Captures
    response, latency, and whether the lane abstained (L369 pattern)."""
    t0 = timeit.default_timer()
    profile = autolit._load_silicon_profile()
    profile["runs"] = profile.get("runs", 0) + 1

    results = []
    counts = {"silicon_backed_ok": 0, "abstained": 0, "reserved": 0,
              "ensemble_skipped_for_smoke": 0, "errored": 0}

    for agent in AGENTS:
        lane, reason = dispatch(agent, profile)
        if lane is None:
            if agent["preferred_lane"] == "ensemble":
                # Smoke test skips ensemble (would 3x the call count); marked as "ensemble_ready"
                results.append({"agent": agent["name"], "status": "ensemble_ready",
                                "preferred_lane": "ensemble", "reason": reason})
                counts["ensemble_skipped_for_smoke"] += 1
            else:
                results.append({"agent": agent["name"], "status": "reserved",
                                "preferred_lane": "reserved", "reason": reason})
                counts["reserved"] += 1
            continue

        max_tokens = agent.get("max_tokens", 80)
        txt, telem = autolit._post_chat(
            lane["model"], agent["smoke_prompt"], timeout=lane["timeout"], max_tokens=max_tokens
        )
        autolit._update_silicon_profile(profile, lane["name"], telem)
        if not telem["ok"]:
            results.append({"agent": agent["name"], "status": "errored",
                            "lane": lane["name"], "error": telem["error_class"]})
            counts["errored"] += 1
        elif not (txt or "").strip():
            # L369 calibration abstention
            results.append({"agent": agent["name"], "status": "abstained",
                            "lane": lane["name"], "latency_ms": telem["latency_ms"]})
            counts["abstained"] += 1
        else:
            results.append({"agent": agent["name"], "status": "silicon_backed_ok",
                            "lane": lane["name"], "latency_ms": telem["latency_ms"],
                            "response_excerpt": txt.strip()[:120]})
            counts["silicon_backed_ok"] += 1
        time.sleep(1.0)  # slow-and-steady
    autolit._save_silicon_profile(profile)

    elapsed = timeit.default_timer() - t0
    return {"counts": counts, "results": results, "elapsed_s": round(elapsed, 2)}


def save_registry() -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps({
        "version": "1.0",
        "agents": AGENTS,
        "lane_routing": {l["name"]: l["model"] for l in autolit.LEMONADE_LANES},
        "saved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2))


def persist_smoke(report: dict) -> tuple[int, int]:
    # Vault observation
    last_id = 0
    for line in VAULT_OBS.read_text().splitlines():
        try:
            last_id = max(last_id, json.loads(line).get("id", 0))
        except Exception:
            pass
    new_id = last_id + 1
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    c = report["counts"]
    text = (
        f"E84: 30-agent council registry built and smoke-tested in {report['elapsed_s']}s. "
        f"Counts: silicon_backed_ok={c['silicon_backed_ok']}, abstained={c['abstained']} (L369), "
        f"reserved={c['reserved']}, ensemble_ready={c['ensemble_skipped_for_smoke']}, errored={c['errored']}. "
        f"Reserved (need additional model loads): vision_language (V-JEPA/VLM), audio_processing (ASR), "
        f"physical_world_sensing + embodied_intelligence (V-JEPA 2-AC + sim adapter). "
        f"Registry saved to scripts/.autoliterature/agent_council_registry.json — future scans "
        f"can dispatch via dispatch(agent, silicon_profile) to pick the right lane. "
        f"L369 calibration: abstention rate is the per-lane × per-agent reliability signal — "
        f"track it, downgrade to next-best lane when success_rate drops below 0.5."
    )
    obs = {"id": new_id, "timestamp": ts, "type": "feature", "project": "cohezion",
           "title": f"E84: 30-agent council registry — {c['silicon_backed_ok']}/{len(AGENTS)} silicon-backed, "
                    f"{c['reserved']} reserved, {c['ensemble_skipped_for_smoke']} ensemble-ready",
           "text": text}
    with VAULT_OBS.open("a") as f:
        f.write(json.dumps(obs) + "\n")

    # autoresearch.jsonl
    last_run = 0
    for line in JSONL.read_text().splitlines():
        try:
            last_run = max(last_run, json.loads(line).get("run", 0))
        except Exception:
            pass
    run = last_run + 1
    entry = {
        "run": run, "metric": float(c["silicon_backed_ok"]) / len(AGENTS),
        "metrics": {
            "agent_count": len(AGENTS),
            "silicon_backed_ok": c["silicon_backed_ok"],
            "abstained_per_L369": c["abstained"],
            "reserved_for_future_models": c["reserved"],
            "ensemble_ready": c["ensemble_skipped_for_smoke"],
            "errored": c["errored"],
            "registry_path": str(REGISTRY_PATH),
            "duration_s": report["elapsed_s"],
            "per_agent_status": [{"agent": r["agent"], "status": r["status"],
                                  "lane": r.get("lane"), "latency_ms": r.get("latency_ms")}
                                 for r in report["results"]],
        },
        "status": "keep",
        "description": f"E84: 30-agent registry — {c['silicon_backed_ok']}/{len(AGENTS)} silicon-backed",
        "timestamp": int(time.time() * 1000), "segment": 99, "confidence": 1.0,
        "asi": {"experiment": "E84", "agents_total": len(AGENTS),
                "silicon_backed_ok": c["silicon_backed_ok"],
                "reserved": c["reserved"]},
    }
    with JSONL.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return new_id, run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true",
                        help="Fire one call per agent (skipping reserved + ensemble)")
    parser.add_argument("--save-only", action="store_true",
                        help="Save registry only (no LLM calls)")
    args = parser.parse_args()

    save_registry()
    print(f"Registry saved: {REGISTRY_PATH}")
    print(f"Agents: {len(AGENTS)}")

    if args.save_only:
        sys.exit(0)

    if args.smoke_test or True:  # smoke test on by default
        print("\nRunning smoke test (1 call per non-reserved/non-ensemble agent)...")
        report = smoke_test()
        c = report["counts"]
        print(f"\n=== smoke summary ({report['elapsed_s']}s) ===")
        print(f"  silicon_backed_ok:  {c['silicon_backed_ok']}")
        print(f"  abstained (L369):   {c['abstained']}")
        print(f"  reserved:           {c['reserved']}")
        print(f"  ensemble_ready:     {c['ensemble_skipped_for_smoke']}")
        print(f"  errored:            {c['errored']}")
        print("\nPer-agent results:")
        for r in report["results"]:
            extra = f" lane={r.get('lane', '-')}"
            if r.get("latency_ms") is not None:
                extra += f" lat={r['latency_ms']:.0f}ms"
            if r.get("response_excerpt"):
                extra += f"  →  {r['response_excerpt'][:60]}"
            elif r.get("reason"):
                extra += f"  ({r['reason']})"
            print(f"  {r['agent']:30s} [{r['status']}]{extra}")

        obs_id, run_id = persist_smoke(report)
        print(f"\nSaved vault obs #{obs_id}, jsonl run #{run_id}")
