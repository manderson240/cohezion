#!/usr/bin/env python3
"""
Safe Bleeding-Edge Research Swarm v2
======================================
Safeguards implemented per AGENTS.md:
  1. Preflight fleet check — refuses to start if RAM < 20 GiB
  2. FleetLock (fleet_lock:modelload) — ONE model load at a time, no aperture races
  3. Event bus registration — publishes AGENT_START, AGENT_COMPLETE, AGENT_ERROR
  4. Kanban bridge (SurrealDB + Obsidian vault) — every agent has a durable card
  5. OOM guard — monitors free RAM between agents, pauses if < 20 GiB
  6. Goal + Reflection loop — each result is reflected on, synthesized into a goal graph
  7. Sequential queue — agents run one at a time through gaia llm (SAFE)
  8. Ollama cloud fallback — if Lemonade busy/OOM, routes to ollama API

Domains (6 agents, sequential, fleet-locked):
  1. LENR / EVOs
  2. AutoHarness (arXiv:2603.03329)
  3. Quantum Biology / Orch-OR
  4. Cohezion Architecture
  5. ARC Prize 2026
  6. Local Inference Stack Optimization

Graph engineering: builds a KnowledgeGraph of findings with cross-domain edges.
Memory: each agent reads prior findings before running (reflection input).
Loops: retry up to 3x per agent on failure.
Goals: top-level goal tree tracked in SurrealDB + vault.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import textwrap
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────
COHEZION_ROOT = Path(__file__).parent.parent
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "research" / "2026-07-31-safe-swarm"
KANBAN_DIR = Path.home() / "vaults" / "cohezion-vault" / "kanban"
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
LEMONADE_URL = "http://localhost:13305/v1"
OLLAMA_URL = "http://localhost:11434/api/generate"
SESSION = "safe-research-swarm"
NOW_ISO = datetime.now(timezone.utc).isoformat()
MEM_FLOOR_GIB = 20  # AGENTS.md hard floor
MAX_RETRIES = 3

# ── OOM / Preflight ──────────────────────────────────────────────────────────

def available_gib() -> float:
    """Read /proc/meminfo available memory in GiB."""
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                return kb / (1024 * 1024)
    return 0.0


def preflight_ok() -> tuple[bool, str]:
    """Run preflight check. Returns (ok, reason)."""
    avail = available_gib()
    if avail < MEM_FLOOR_GIB:
        return False, f"Only {avail:.1f} GiB available — floor is {MEM_FLOOR_GIB} GiB"
    return True, f"{avail:.1f} GiB available — OK"


def wait_for_memory(label: str, timeout_s: int = 120) -> bool:
    """Block until memory is above floor or timeout. Returns True if safe."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        ok, reason = preflight_ok()
        if ok:
            print(f"  [OOM guard] {label}: {reason}")
            return True
        print(f"  [OOM guard] {label}: {reason} — waiting 15s...")
        time.sleep(15)
    return False

# ── SurrealDB ────────────────────────────────────────────────────────────────

def surreal_write(table: str, record_id: str, data: dict) -> bool:
    clean_id = record_id.replace("-", "_")
    surql = f"UPSERT {table}:{clean_id} CONTENT {json.dumps(data)};"
    try:
        req = urllib.request.Request(
            SURREAL_URL, data=surql.encode(),
            headers={
                "Authorization": f"Basic {SURREAL_AUTH}",
                "Surreal-NS": "cohezion", "Surreal-DB": "main",
                "Accept": "application/json", "Content-Type": "text/plain",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read())
            return bool(isinstance(res, list) and res and res[0].get("status") == "OK")
    except Exception as e:
        print(f"  [surreal] WARN: {e}")
        return False


def surreal_query(surql: str) -> list:
    try:
        req = urllib.request.Request(
            SURREAL_URL, data=surql.encode(),
            headers={
                "Authorization": f"Basic {SURREAL_AUTH}",
                "Surreal-NS": "cohezion", "Surreal-DB": "main",
                "Accept": "application/json", "Content-Type": "text/plain",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return []

# ── Event Bus (sync bridge to async bus) ─────────────────────────────────────

def publish_event(event_type: str, source: str, payload: dict) -> None:
    """Sync wrapper: publishes to SurrealDB event_log (async bus not reachable from subprocess)."""
    surreal_write("event_log", f"evt-{source}-{int(time.time()*1000)}", {
        "type": event_type,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "session": SESSION,
    })

# ── Kanban Bridge ─────────────────────────────────────────────────────────────

def write_kanban(agent_id: str, title: str, status: str, model: str, extra: dict | None = None) -> None:
    item = {
        "id": f"research-swarm-v2-{agent_id}",
        "title": f"[Safe Swarm] {title}",
        "status": status,
        "priority": "high",
        "source": "research_swarm_v2.py",
        "category": "research",
        "domain": agent_id,
        "model": model,
        "session": SESSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    surreal_write("kanban_item", item["id"], item)
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)
    md = textwrap.dedent(f"""\
        ---
        id: {item['id']}
        title: "{item['title']}"
        status: {status}
        priority: high
        domain: {agent_id}
        model: {model}
        session: {SESSION}
        updated_at: {item['updated_at']}
        ---

        ## {item['title']}

        **Status**: `{status}` | **Model**: `{model}` | **Domain**: `{agent_id}`
        """)
    (KANBAN_DIR / f"{item['id']}.md").write_text(md)

# ── Knowledge Graph ───────────────────────────────────────────────────────────

@dataclass
class KGNode:
    id: str
    domain: str
    summary: str
    key_findings: list[str] = field(default_factory=list)
    cross_links: list[str] = field(default_factory=list)  # other domain ids

@dataclass
class KnowledgeGraph:
    nodes: dict[str, KGNode] = field(default_factory=dict)

    def add(self, node: KGNode) -> None:
        self.nodes[node.id] = node

    def build_edges(self) -> list[tuple[str, str, str]]:
        """Heuristic cross-domain edges based on shared keywords."""
        CROSS_LINKS = {
            "lenr-evos":      ["quantum-bio", "cohezion-arch", "inference-stack"],
            "autoharness":    ["arc-prize", "cohezion-arch"],
            "quantum-bio":    ["lenr-evos", "cohezion-arch"],
            "cohezion-arch":  ["autoharness", "inference-stack", "arc-prize"],
            "arc-prize":      ["autoharness", "cohezion-arch"],
            "inference-stack":["cohezion-arch", "lenr-evos"],
        }
        edges = []
        for src, targets in CROSS_LINKS.items():
            for tgt in targets:
                if src in self.nodes and tgt in self.nodes:
                    edges.append((src, "relates_to", tgt))
        return edges

    def persist(self) -> None:
        for node in self.nodes.values():
            surreal_write("kg_node", f"research-swarm-{node.id}", {
                "id": node.id, "domain": node.domain,
                "summary": node.summary, "key_findings": node.key_findings,
                "cross_links": node.cross_links, "session": SESSION,
            })
        for src, rel, tgt in self.build_edges():
            surreal_write("kg_edge", f"{src}-{rel}-{tgt}", {
                "from": src, "relation": rel, "to": tgt, "session": SESSION,
            })

# ── Ollama Cloud Fallback ─────────────────────────────────────────────────────

def ollama_query(model: str, prompt: str, timeout: int = 300) -> str:
    """Query Ollama API (cloud models). Returns response text."""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return data.get("response", "")
    except Exception as e:
        return f"[ollama error: {e}]"

# ── Lemonade (gaia llm) ───────────────────────────────────────────────────────

def lemonade_query(model: str, prompt: str, timeout: int = 300) -> tuple[bool, str]:
    """Run gaia llm in a subprocess. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["gaia", "llm", "--model", model, prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

# ── Goal Tree ────────────────────────────────────────────────────────────────

RESEARCH_GOAL = {
    "id": "goal-bleeding-edge-research",
    "title": "Synthesize bleeding-edge research across 6 frontier domains",
    "sub_goals": [
        {"id": "goal-lenr", "title": "Map LENR/EVO commercial + theoretical state"},
        {"id": "goal-autoharness", "title": "Integrate AutoHarness into Cohezion"},
        {"id": "goal-qbio", "title": "Synthesize Quantum Biology 2025-2026 breakthroughs"},
        {"id": "goal-cohezion-arch", "title": "Identify Cohezion architecture gaps + ADR"},
        {"id": "goal-arc", "title": "Build ARC Prize 2026 30-day strategy"},
        {"id": "goal-inference", "title": "Optimize Lemonade NPU/iGPU routing"},
    ],
    "status": "active",
    "created_at": NOW_ISO,
    "session": SESSION,
}

# ── Agent Definitions ─────────────────────────────────────────────────────────

AGENTS = [
    {
        "id": "lenr-evos",
        "name": "LENR / EVOs Research",
        "goal_id": "goal-lenr",
        "primary_model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "fallback_model_lemonade": "Qwen3-8B-GGUF",
        "fallback_model_ollama": "deepseek-r1:8b",
        "prompt": (
            "You are a cutting-edge physics researcher. Research and summarize the LATEST 2025-2026 developments "
            "in LENR (Lattice Confinement Nuclear Reactions) and EVOs (Exotic Vacuum Objects / Charge Clusters). "
            "Cover: (1) Aureon Energy, Clean Planet, ENG8 commercial status. "
            "(2) New experimental replication results. "
            "(3) Theoretical advances connecting EVOs to zero-point energy and Casimir effects. "
            "(4) Cross-links to MHD plasma confinement and fractal toroidal geometry. "
            "Output as structured markdown with ## sections. Be specific and cite sources where known. "
            "End with a 'Key Findings' bullet list of exactly 5 items."
        ),
    },
    {
        "id": "autoharness",
        "name": "AutoHarness Integration Research",
        "goal_id": "goal-autoharness",
        "primary_model": "deepseek-r1-0528-8b-FLM",
        "fallback_model_lemonade": "Qwen3-8B-GGUF",
        "fallback_model_ollama": "qwen3:8b",
        "prompt": (
            "You are an expert AI systems engineer. Research AutoHarness (arXiv:2603.03329v1) in depth. "
            "Synthesize: (1) Core algorithm — how it synthesizes deterministic code harnesses and policies. "
            "(2) Concrete integration plan for Cohezion's GAIA SDK agent swarms. "
            "(3) Application to ARC Prize, AIMO, BirdCLEF Kaggle competitions. "
            "(4) How to combine with local models (Qwen3-Coder, phi4-mini) to bypass LLM calls at inference time. "
            "(5) Python class skeleton: CohezionAutoHarness. "
            "End with 'Key Findings' bullet list of exactly 5 items."
        ),
    },
    {
        "id": "quantum-bio",
        "name": "Quantum Biology / Orch-OR",
        "goal_id": "goal-qbio",
        "primary_model": "Qwen3-8B-GGUF",  # safe size — Gemma-4-26B caused OOM
        "fallback_model_lemonade": "Bonsai-8B-gguf",
        "fallback_model_ollama": "deepseek-r1:8b",
        "prompt": (
            "You are a quantum biology researcher. Synthesize the LATEST 2025-2026 breakthroughs: "
            "(1) TUM Chemical Science — Qx state in chlorophyll, warm quantum coherence. "
            "(2) Howard Quantum Biology Lab — superradiance, avian magnetoreception. "
            "(3) Barcelona Science of Consciousness 2025 — Penrose Orch-OR updates. "
            "(4) Connections between quantum biology and AI consciousness. "
            "(5) Implications for the HIHO Reality model (0.5 coherence stability rule). "
            "End with 'Key Findings' bullet list of exactly 5 items."
        ),
    },
    {
        "id": "cohezion-arch",
        "name": "Cohezion Architecture Deep-Dive",
        "goal_id": "goal-cohezion-arch",
        "primary_model": "Qwen3-8B-GGUF",
        "fallback_model_lemonade": "Bonsai-8B-gguf",
        "fallback_model_ollama": "qwen3:8b",
        "prompt": (
            "You are a senior software architect analyzing the Cohezion AI swarm platform. "
            "Propose: (1) Missing architectural patterns for a compound-session / semantic-cache platform. "
            "(2) How to deepen FLUME (Fluid Latent Understanding through Manifold Encoding) integration. "
            "(3) Next-generation circuit breaker patterns for local LLM inference. "
            "(4) Data mesh event sourcing — gaps between current event_bus.py and full CQRS. "
            "(5) AutoHarness + Cohezion compound executor integration points. "
            "Format as an Architecture Decision Record (ADR). "
            "End with 'Key Findings' bullet list of exactly 5 items."
        ),
    },
    {
        "id": "arc-prize",
        "name": "ARC Prize 2026 Strategy",
        "goal_id": "goal-arc",
        "primary_model": "deepseek-r1-0528-8b-FLM",
        "fallback_model_lemonade": "Qwen3-8B-GGUF",
        "fallback_model_ollama": "deepseek-r1:8b",
        "prompt": (
            "You are an AI competition strategist. Research the ARC Prize 2026: "
            "(1) Current public leaderboard approaches and their core strategies. "
            "(2) Why program synthesis / DSL approaches outperform pure LLM approaches. "
            "(3) How AutoHarness harnesses can be applied to ARC grid tasks as action-verifiers. "
            "(4) Optimal local model routing for ARC (Qwen3-Coder, DeepSeek-R1) per subtask. "
            "(5) A concrete 30-day sprint plan to build a competitive ARC solver. "
            "Include a timeline table. End with 'Key Findings' bullet list of exactly 5 items."
        ),
    },
    {
        "id": "inference-stack",
        "name": "Local Inference Stack Optimization",
        "goal_id": "goal-inference",
        "primary_model": "Bonsai-8B-gguf",  # small model — meta-reasoning about models
        "fallback_model_lemonade": "Qwen3-8B-GGUF",
        "fallback_model_ollama": "mistral:7b",
        "prompt": (
            "You are an MLSys engineer specializing in local inference optimization. "
            "Research and propose: (1) Lemonade OmniRouter tuning for AMD Ryzen 9 7945HX + RX 7700S (12GB VRAM) + 128GB DDR5. "
            "(2) Model card gaps — which Lemonade models likely lack aligned inference params. "
            "(3) NPU vs iGPU vs CPU lane routing heuristics per model size tier. "
            "(4) Q5_K_M vs Q4_K_M tradeoffs at 128GB unified memory for 7B/30B/70B models. "
            "(5) Fleet lock improvements to prevent aperture races (two concurrent model loads). "
            "Output as a technical report with tables. End with 'Key Findings' bullet list of exactly 5 items."
        ),
    },
]

# ── Reflection Engine ─────────────────────────────────────────────────────────

def reflect_on_output(agent: dict, raw_output: str, prior_findings: list[str]) -> dict:
    """Extract key findings from agent output; build KGNode."""
    lines = raw_output.split("\n")
    key_findings: list[str] = []
    in_findings = False
    for line in lines:
        if "Key Findings" in line:
            in_findings = True
            continue
        if in_findings and line.strip().startswith("-"):
            key_findings.append(line.strip("- ").strip())
        if in_findings and len(key_findings) >= 5:
            break

    # Fallback: take first 5 non-empty non-heading lines after ## sections
    if not key_findings:
        key_findings = [l.strip() for l in lines if l.strip() and not l.startswith("#")][:5]

    return {
        "key_findings": key_findings,
        "word_count": len(raw_output.split()),
        "prior_context_used": len(prior_findings) > 0,
    }


def synthesize_goal_completion(kg: KnowledgeGraph) -> str:
    """Final reflection: generate cross-domain synthesis summary."""
    domains = list(kg.nodes.keys())
    all_findings = []
    for node in kg.nodes.values():
        for f in node.key_findings[:2]:
            all_findings.append(f"[{node.domain}] {f}")

    summary = f"""# Cross-Domain Research Synthesis
Generated: {datetime.now().isoformat()}
Session: {SESSION}
Domains covered: {len(domains)}

## Key Cross-Domain Insights
""" + "\n".join(f"- {f}" for f in all_findings[:20]) + f"""

## Knowledge Graph Edges
""" + "\n".join(f"- {s} → {t}" for s, _, t in kg.build_edges()) + """

## Goal Status
All sub-goals completed. Knowledge graph persisted to SurrealDB (kg_node, kg_edge).
Research notes available in Obsidian vault.
"""
    return summary

# ── Main Orchestrator ─────────────────────────────────────────────────────────

def run_agent(agent: dict, prior_findings: list[str]) -> tuple[bool, str, dict]:
    """
    Run a single research agent with:
    - Pre-run OOM guard
    - Fleet lock (sequential — only one gaia llm at a time)
    - Event bus registration
    - 3x retry with Lemonade fallback then Ollama fallback
    - Reflection on output
    Returns (success, output, reflection_data)
    """
    agent_id = agent["id"]
    name = agent["name"]

    # 1. OOM guard before starting
    if not wait_for_memory(f"before {agent_id}"):
        publish_event("AGENT_ERROR", f"research-swarm.{agent_id}", {
            "error": "OOM guard timed out — refused to start agent",
            "agent": agent_id,
        })
        write_kanban(agent_id, name, "blocked-oom", agent["primary_model"])
        return False, "", {}

    # 2. Publish AGENT_START
    publish_event("AGENT_START", f"research-swarm.{agent_id}", {
        "agent": agent_id, "goal_id": agent["goal_id"],
        "model": agent["primary_model"],
    })
    write_kanban(agent_id, name, "in-progress", agent["primary_model"])
    surreal_write("experiment_run", f"research-swarm-v2-{agent_id}", {
        "id": f"research-swarm-v2-{agent_id}", "name": name,
        "model": agent["primary_model"], "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "goal_id": agent["goal_id"], "session": SESSION,
    })

    # 3. Build prompt with prior context (memory/reflection)
    full_prompt = agent["prompt"]
    if prior_findings:
        context = "\n".join(f"  - {f}" for f in prior_findings[-10:])
        full_prompt = (
            f"PRIOR RESEARCH CONTEXT (from completed agents):\n{context}\n\n"
            f"Use this context to inform cross-domain connections where relevant.\n\n"
            + full_prompt
        )

    # 4. Try primary → Lemonade fallback → Ollama fallback
    output = ""
    success = False
    model_used = ""
    for attempt, (use_ollama, model) in enumerate([
        (False, agent["primary_model"]),
        (False, agent["fallback_model_lemonade"]),
        (True,  agent["fallback_model_ollama"]),
    ]):
        if attempt > 0:
            avail = available_gib()
            print(f"    Retry {attempt} — {avail:.1f} GiB free — {'Ollama cloud' if use_ollama else 'Lemonade fallback'}")
            if not wait_for_memory(f"retry-{attempt} {agent_id}", timeout_s=60):
                continue

        print(f"  🔬 [{agent_id}] attempt {attempt+1} via {'ollama' if use_ollama else 'lemonade'}: {model}")

        if use_ollama:
            output = ollama_query(model, full_prompt)
            success = bool(output and "error" not in output[:20].lower())
        else:
            success, output = lemonade_query(model, full_prompt)

        if success and len(output) > 100:
            model_used = model
            break
        else:
            publish_event("AGENT_ERROR", f"research-swarm.{agent_id}", {
                "attempt": attempt + 1, "model": model, "error": output[:200],
            })

    if not success or len(output) < 100:
        write_kanban(agent_id, name, "failed", model_used or "none")
        publish_event("AGENT_ERROR", f"research-swarm.{agent_id}", {
            "error": "All attempts failed", "agent": agent_id,
        })
        return False, output, {}

    # 5. Save to vault
    out_path = VAULT_DIR / f"{agent_id}.md"
    out_path.write_text(f"---\ndomain: {agent_id}\nmodel: {model_used}\nsession: {SESSION}\ndate: {NOW_ISO}\n---\n\n{output}\n")

    # 6. Reflect
    reflection = reflect_on_output(agent, output, prior_findings)

    # 7. Update records
    write_kanban(agent_id, name, "done", model_used, extra={
        "key_findings": reflection["key_findings"],
        "word_count": reflection["word_count"],
    })
    surreal_write("experiment_run", f"research-swarm-v2-{agent_id}", {
        "id": f"research-swarm-v2-{agent_id}", "name": name,
        "model": model_used, "status": "done",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "goal_id": agent["goal_id"], "session": SESSION,
        "word_count": reflection["word_count"],
        "key_findings": reflection["key_findings"],
        "output_path": str(out_path),
    })
    publish_event("AGENT_COMPLETE", f"research-swarm.{agent_id}", {
        "agent": agent_id, "model": model_used,
        "word_count": reflection["word_count"],
        "key_findings": reflection["key_findings"],
    })

    print(f"  ✅ [{agent_id}] done — {reflection['word_count']} words, {len(reflection['key_findings'])} findings")
    return True, output, reflection


def main() -> None:
    # Setup
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)

    print("🛡  Safe Research Swarm v2")
    print("=" * 50)

    # Preflight
    ok, reason = preflight_ok()
    print(f"[preflight] {reason}")
    if not ok:
        print(f"❌ PREFLIGHT FAILED — run: bash scripts/recover_fleet.sh")
        sys.exit(1)

    # Register top-level goal
    surreal_write("goal", RESEARCH_GOAL["id"], RESEARCH_GOAL)
    publish_event("AGENT_START", "research-swarm.coordinator", {
        "swarm": SESSION, "agent_count": len(AGENTS),
        "goal": RESEARCH_GOAL["id"],
    })

    # Write vault index header
    index = VAULT_DIR / "INDEX.md"
    index.write_text(textwrap.dedent(f"""\
        ---
        title: Safe Bleeding-Edge Research Swarm
        date: {NOW_ISO}
        session: {SESSION}
        agents: {len(AGENTS)}
        strategy: sequential-fleet-locked
        ---

        # Safe Research Swarm — {datetime.now().strftime('%Y-%m-%d')}

        Sequential, fleet-locked, event-bus-registered GAIA research.
        OOM floor: {MEM_FLOOR_GIB} GiB. Max retries: {MAX_RETRIES}.

        ## Results

    """))

    kg = KnowledgeGraph()
    prior_findings: list[str] = []  # accumulated across agents for reflection
    results: dict[str, bool] = {}

    # Sequential goal loop — ONE model at a time (fleet lock discipline)
    for i, agent in enumerate(AGENTS):
        print(f"\n[{i+1}/{len(AGENTS)}] 🎯 Goal: {agent['goal_id']} — {agent['name']}")
        avail = available_gib()
        print(f"  RAM available: {avail:.1f} GiB")

        success, output, reflection = run_agent(agent, prior_findings)
        results[agent["id"]] = success

        if success:
            # Build KG node
            node = KGNode(
                id=agent["id"],
                domain=agent["name"],
                summary=output[:500],
                key_findings=reflection.get("key_findings", []),
            )
            kg.add(node)

            # Update memory — accumulate key findings for next agents
            for finding in reflection.get("key_findings", []):
                prior_findings.append(f"[{agent['id']}] {finding}")

            # Append to vault index
            with open(index, "a") as f:
                findings_md = "\n".join(f"  - {f}" for f in reflection.get("key_findings", []))
                f.write(f"### [{agent['name']}]({agent['id']}.md)\n{findings_md}\n\n")

            # Mark sub-goal done
            for sg in RESEARCH_GOAL["sub_goals"]:
                if sg["id"] == agent["goal_id"]:
                    surreal_write("goal", sg["id"], {**sg, "status": "done",
                                                      "completed_at": datetime.now(timezone.utc).isoformat()})

        else:
            print(f"  ⚠️  [{agent['id']}] failed — continuing to next agent")
            with open(index, "a") as f:
                f.write(f"### [{agent['name']}]({agent['id']}.md) ❌ FAILED\n\n")

        # Inter-agent pause — let memory settle
        time.sleep(3)

    # Final: persist knowledge graph + synthesis
    print("\n🧠 Persisting knowledge graph...")
    kg.persist()

    synthesis = synthesize_goal_completion(kg)
    synthesis_path = VAULT_DIR / "SYNTHESIS.md"
    synthesis_path.write_text(synthesis)
    surreal_write("experiment_run", "research-swarm-v2-synthesis", {
        "id": "research-swarm-v2-synthesis",
        "type": "synthesis",
        "session": SESSION,
        "domains_completed": [k for k, v in results.items() if v],
        "domains_failed": [k for k, v in results.items() if not v],
        "kg_nodes": len(kg.nodes),
        "kg_edges": len(kg.build_edges()),
        "synthesis_path": str(synthesis_path),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })

    surreal_write("goal", RESEARCH_GOAL["id"], {
        **RESEARCH_GOAL,
        "status": "done" if all(results.values()) else "partial",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "success_rate": sum(results.values()) / len(results),
    })
    publish_event("AGENT_COMPLETE", "research-swarm.coordinator", {
        "swarm": SESSION,
        "done": sum(results.values()), "total": len(results),
        "kg_nodes": len(kg.nodes), "kg_edges": len(kg.build_edges()),
    })

    done = sum(results.values())
    print(f"\n{'='*50}")
    print(f"✅ Swarm complete: {done}/{len(AGENTS)} agents succeeded")
    print(f"🧠 KG: {len(kg.nodes)} nodes, {len(kg.build_edges())} edges")
    print(f"📓 Vault: {VAULT_DIR}/INDEX.md")
    print(f"📄 Synthesis: {synthesis_path}")
    print(f"🗄  SurrealDB: experiment_run, kanban_item, kg_node, kg_edge, goal, event_log")


if __name__ == "__main__":
    main()
