"""E77 / autoliterature pillar — closed-loop arXiv + HuggingFace papers scanner.

Adds a fourth pillar (alongside autodata / autoresearch / autoharness) to the
overnight loop: each invocation pulls fresh papers from arXiv (Atom API) and
Hugging Face (daily papers JSON), scores them against the active open-problem
registry, computes deltas vs the seen-papers cache, and persists hits to:

  * autoresearch.jsonl (asi.experiment="E77", with paper_index)
  * ~/vaults/cohezion-vault/memory/observations.jsonl (type="literature")
  * scripts/.autoliterature/seen_paper_ids.json (state cache)

No WebSearch dependency — pure HTTP + stdlib parse. Runnable as a standalone
process, importable as a function from autorun_2h.py's between-cycle hook.

Run:
  uv run python scripts/autoliterature_scanner.py

Recommended cadence: once per autorun_2h cycle (~minutes) is too aggressive —
prefer once per session-start, or every N cycles. The scanner does the right
thing if invoked back-to-back: deltas will be empty, JSONL gets one short row
recording "no new papers".
"""

from __future__ import annotations

import json
import re
import time
import timeit
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path


REPO = Path("/home/mike-anderson/dev/cohezion")
VAULT_OBS = Path("/home/mike-anderson/vaults/cohezion-vault/memory/observations.jsonl")
JSONL = REPO / "autoresearch.jsonl"
STATE_DIR = REPO / "scripts" / ".autoliterature"
STATE_DIR.mkdir(parents=True, exist_ok=True)
SEEN_PATH = STATE_DIR / "seen_paper_ids.json"
SEEN_MODELS_PATH = STATE_DIR / "seen_model_ids.json"

# ── model-scout config: tip-of-the-spear fine-tunable open-weight LLMs ───────
# Fine-tuning budget on Strix Halo (128 GiB unified memory):
#   * ≤ 8B params full FP16 fine-tune (LoRA preferred)
#   * ≤ 32B params with QLoRA (4-bit base + LoRA adapters, ~16-24 GiB peak)
#   * Reject > 70B params (won't fit even quantized)
MODEL_SCOUT_MAX_PARAMS = 35_000_000_000  # 35B param cap for QLoRA on Strix Halo
MODEL_SCOUT_OPEN_LICENSES = {
    "apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause",
    "llama2", "llama3", "llama3.1", "llama3.2", "llama3.3", "llama4",
    "gemma", "gemma-3", "gemma-4",
    "qwen", "qwen-research", "qwen-license",
    "deepseek-license", "deepseek",
    "openrail", "openrail++", "creativeml-openrail-m",
    # Mistral/codestral are non-commercial — NOT included.
}
MODEL_SCOUT_BLOCKED_LIBS = {"diffusers", "tortoise-tts", "tensorflowtts"}  # not LLMs
MODEL_SCOUT_TASK_FILTER = "text-generation"

# ── local inference: multi-lane (NPU + iGPU + CPU) on Lemonade port 13307 ────
# Single server, three hardware paths via the model's `recipe`:
#   flm       → AMD Ryzen AI NPU (fastest, small models only)
#   llamacpp  → Radeon 8060S iGPU via ROCWMMA (best quality, large models)
#   llamacpp  → CPU (Ryzen AI MAX+ 395 16C/32T, fallback when iGPU busy)
# We try lanes in priority order with a short timeout; first to respond wins.
# Track which lane scored each paper for hardware-utilization analytics.
LEMONADE_BASE = "http://localhost:13307/v1"
# Per-lane preferred-and-fallback model lists. The scanner probes them in order
# inside each lane, so when AMD/FastFlowLM ships Gemma-4 NPU into Lemonade
# (FLM v0.9.39 added gemma4-it:e2b — pending Lemonade bundle update per AMD's
# Day-0 Gemma 4 announcement), the scanner switches to it automatically without
# any code change.
LEMONADE_LANES = [
    {"name": "npu",  "model": "gemma3-4b-FLM",
     "preferred_models": ["gemma4-it:e2b", "Gemma-4-E2B-FLM", "gemma3-4b-FLM"],
     "timeout": 12.0, "max_tokens": 180},  # bumped 8→12 for cold-load tolerance
    {"name": "igpu", "model": "Gemma-4-E4B-it-GGUF",
     "preferred_models": ["Gemma-4-E4B-it-GGUF", "Gemma-4-E2B-it-GGUF"],
     "timeout": 20.0, "max_tokens": 180},
    {"name": "cpu",  "model": "Qwen3-0.6B-GGUF",
     "preferred_models": ["Qwen3-0.6B-GGUF", "Gemma-4-E2B-it-GGUF"],
     "timeout": 15.0, "max_tokens": 180},
]
# Round-robin starting offset bumps each call so load spreads across lanes
# (writes back to the seen-cache state file so it persists across invocations)
LANE_ROTATION_PATH = STATE_DIR / "lane_rotation.json"
# Silicon profile: per-lane accumulated characteristics across all runs.
# Lets us answer "which lane is fastest for paper-scoring" empirically rather
# than trusting hardcoded priorities.
SILICON_PROFILE_PATH = STATE_DIR / "silicon_profile.json"

# ── open-problem registry ─────────────────────────────────────────────────────
# Each entry: keywords (lowercased) + the experiment IDs it would unblock.
# Maintained from E72-E76 findings — extend as new problems emerge.
OPEN_PROBLEMS = {
    "open_loop_drivers": {
        "keywords": ["self-improving", "recursive self-improvement", "autoresearch",
                     "agentic research", "automated experimentation", "agent loop"],
        "unblocks": ["E72", "E74"],
    },
    "stuck_optimizer": {
        "keywords": ["prompt optimization", "reflective prompt", "gepa", "dspy",
                     "evolutionary prompt", "trace optimizer"],
        "unblocks": ["E74"],
    },
    "voting_aggregation": {
        "keywords": ["multi-agent voting", "weighted voting", "majority voting",
                     "council", "ensemble", "dawid-skene", "calibrated confidence"],
        "unblocks": ["E69"],
    },
    "world_model_jepa": {
        "keywords": ["jepa", "v-jepa", "world model", "latent action",
                     "self-supervised video", "action-conditioned"],
        "unblocks": ["E11", "E46"],
    },
    "early_stopping": {
        "keywords": ["early stopping", "convergence detection", "majority then stopping",
                     "adaptive termination", "coefficient of variation"],
        "unblocks": ["E70", "E71"],
    },
    "scoring_calibration": {
        "keywords": ["proper scoring rule", "brier score", "log-loss",
                     "calibration", "overconfidence", "abstention"],
        "unblocks": ["E69", "metacognitive-calibration"],
    },
    "graph_provenance": {
        "keywords": ["graphrag", "knowledge graph", "provenance graph",
                     "graph-of-thought", "neuro-symbolic"],
        "unblocks": ["E72-graph-edges-empty"],
    },
}


# ── arXiv Atom API ────────────────────────────────────────────────────────────
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_CATEGORIES = "cs.LG+OR+cs.AI+OR+cs.CL+OR+cs.MA"


def fetch_arxiv(query: str, max_results: int = 25, timeout: float = 10.0) -> list[dict]:
    """Hit arXiv export API for a single query, return parsed papers."""
    # arXiv search_query DSL: "all:keywords" picks up title + abstract + authors
    qs = urllib.parse.urlencode({
        "search_query": f"all:({query}) AND (cat:cs.LG OR cat:cs.AI OR cat:cs.CL OR cat:cs.MA)",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    })
    url = f"http://export.arxiv.org/api/query?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            xml_bytes = r.read()
    except Exception as exc:
        print(f"  [arxiv] fetch failed for '{query[:40]}': {exc}", flush=True)
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        print(f"  [arxiv] XML parse failed: {exc}", flush=True)
        return []

    out = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        eid = entry.findtext("atom:id", "", ARXIV_NS)
        # eid example: http://arxiv.org/abs/2510.01499v1 → arxiv_id = 2510.01499
        m = re.search(r"abs/([\d.]+)v?\d*", eid)
        arxiv_id = m.group(1) if m else eid
        title = (entry.findtext("atom:title", "", ARXIV_NS) or "").strip()
        title = re.sub(r"\s+", " ", title)
        summary = (entry.findtext("atom:summary", "", ARXIV_NS) or "").strip()[:600]
        published = entry.findtext("atom:published", "", ARXIV_NS) or ""
        out.append({
            "source": "arxiv",
            "id": f"arxiv:{arxiv_id}",
            "title": title,
            "summary": summary,
            "published": published,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        })
    return out


# ── Hugging Face trending models (fine-tuning candidates) ────────────────────
def fetch_hf_models(limit: int = 60, timeout: float = 12.0) -> list[dict]:
    """Pull trending text-generation models from HF API.

    Returns dicts with: id, downloads, likes, library, license, params_estimate, tags, url.
    Only models that pass the open-license + size filter are returned.
    """
    qs = urllib.parse.urlencode({
        "filter": MODEL_SCOUT_TASK_FILTER,
        "sort": "trendingScore", "direction": "-1",
        "limit": limit,
        "full": "true",  # get tags + library_name
    })
    url = f"https://huggingface.co/api/models?{qs}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except Exception as exc:
        print(f"  [hf-models] fetch failed: {exc}", flush=True)
        return []

    out = []
    for entry in data:
        mid = entry.get("modelId") or entry.get("id") or ""
        if not mid:
            continue
        tags = entry.get("tags") or []
        library = entry.get("library_name") or ""
        # Extract license from tags (license:apache-2.0 style) or license field
        license_str = ""
        for t in tags:
            if t.startswith("license:"):
                license_str = t.split(":", 1)[1].strip().lower()
                break
        if not license_str:
            license_str = (entry.get("license") or "").lower()
        # Param estimate: from safetensors.total or model name suffix (heuristic)
        sf = entry.get("safetensors") or {}
        params = sf.get("total", 0) or 0
        if params == 0:
            # crude guess from name (e.g. -7B-, -32B-Instruct, -1.5B)
            m = re.search(r"[-_](\d+(?:\.\d+)?)([Bb])(?=[-_]|$)", mid)
            if m:
                params = int(float(m.group(1)) * 1_000_000_000)
        out.append({
            "id": f"hfmodel:{mid}",
            "model_id": mid,
            "url": f"https://huggingface.co/{mid}",
            "downloads": entry.get("downloads", 0),
            "likes": entry.get("likes", 0),
            "library": library,
            "license": license_str,
            "params_estimate": params,
            "tags": tags[:20],
            "pipeline_tag": entry.get("pipeline_tag", ""),
        })
    return out


def filter_finetunable(models: list[dict]) -> list[dict]:
    """Apply the local-finetunability filter: open license + size cap + LLM lib."""
    keep = []
    for m in models:
        if m.get("library") in MODEL_SCOUT_BLOCKED_LIBS:
            continue
        # License filter — accept exact match, family match, or prefix match
        lic = m.get("license", "")
        ok_license = False
        for okl in MODEL_SCOUT_OPEN_LICENSES:
            if lic == okl or lic.startswith(okl):
                ok_license = True; break
        if not ok_license:
            # Some popular open-weights tag as "other" but README is permissive — keep but flag
            if "other" in lic or lic == "":
                m["license_uncertain"] = True
            else:
                continue
        # Size cap
        params = m.get("params_estimate", 0)
        if params > MODEL_SCOUT_MAX_PARAMS:
            continue
        keep.append(m)
    return keep


def load_seen_models() -> set[str]:
    if SEEN_MODELS_PATH.exists():
        try:
            return set(json.loads(SEEN_MODELS_PATH.read_text()).get("ids", []))
        except Exception:
            return set()
    return set()


def save_seen_models(seen: set[str]) -> None:
    SEEN_MODELS_PATH.write_text(json.dumps({
        "ids": sorted(seen),
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(seen),
    }))


# ── Hugging Face daily papers ─────────────────────────────────────────────────
def fetch_hf_daily(timeout: float = 10.0) -> list[dict]:
    """Hit HF daily papers JSON endpoint."""
    url = "https://huggingface.co/api/daily_papers"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except Exception as exc:
        print(f"  [hf] fetch failed: {exc}", flush=True)
        return []

    out = []
    for entry in data:
        paper = entry.get("paper") or {}
        pid = paper.get("id") or ""
        title = (paper.get("title") or "").strip()
        summary = (paper.get("summary") or "").strip()[:600]
        published = entry.get("publishedAt") or paper.get("publishedAt") or ""
        if not pid:
            continue
        out.append({
            "source": "hf_daily",
            "id": f"hf:{pid}",
            "title": title,
            "summary": summary,
            "published": published,
            "url": f"https://huggingface.co/papers/{pid}",
        })
    return out


# ── scoring: map paper text → open problems ───────────────────────────────────
def score_paper(paper: dict) -> tuple[list[str], int]:
    """Return (matching_problem_keys, total_keyword_hits)."""
    text = f"{paper.get('title','')} {paper.get('summary','')}".lower()
    matches: list[str] = []
    total_hits = 0
    for problem_key, problem in OPEN_PROBLEMS.items():
        hits = sum(1 for kw in problem["keywords"] if kw in text)
        if hits > 0:
            matches.append(problem_key)
            total_hits += hits
    return matches, total_hits


# ── multi-lane Lemonade scoring ───────────────────────────────────────────────
def _load_lane_rotation_offset() -> int:
    if LANE_ROTATION_PATH.exists():
        try:
            return int(json.loads(LANE_ROTATION_PATH.read_text()).get("offset", 0))
        except Exception:
            return 0
    return 0


def _save_lane_rotation_offset(offset: int) -> None:
    LANE_ROTATION_PATH.write_text(json.dumps({
        "offset": offset % len(LEMONADE_LANES),
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }))


def _post_chat(model: str, prompt: str, timeout: float, max_tokens: int) -> tuple[str | None, dict]:
    """Single OpenAI-compatible completion against Lemonade.

    Returns (content_or_none, telemetry_dict). Telemetry includes:
      latency_ms, ok (bool), error_class, response_tokens (best-effort),
      tokens_per_sec (best-effort).
    """
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{LEMONADE_BASE}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    t0 = timeit.default_timer()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        latency_ms = (timeit.default_timer() - t0) * 1000.0
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        # Token estimate from response (Lemonade returns usage if available)
        usage = data.get("usage") or {}
        out_tokens = usage.get("completion_tokens") or len((content or "").split())
        tps = (out_tokens / (latency_ms / 1000.0)) if latency_ms > 0 else 0.0
        return content, {
            "latency_ms": round(latency_ms, 1),
            "ok": True,
            "error_class": None,
            "response_tokens": out_tokens,
            "tokens_per_sec": round(tps, 2),
        }
    except urllib.error.HTTPError as e:
        return None, {
            "latency_ms": round((timeit.default_timer() - t0) * 1000.0, 1),
            "ok": False, "error_class": f"http_{e.code}",
            "response_tokens": 0, "tokens_per_sec": 0.0,
        }
    except urllib.error.URLError as e:
        return None, {
            "latency_ms": round((timeit.default_timer() - t0) * 1000.0, 1),
            "ok": False, "error_class": f"url_{type(e.reason).__name__}",
            "response_tokens": 0, "tokens_per_sec": 0.0,
        }
    except TimeoutError:
        return None, {
            "latency_ms": round((timeit.default_timer() - t0) * 1000.0, 1),
            "ok": False, "error_class": "timeout",
            "response_tokens": 0, "tokens_per_sec": 0.0,
        }
    except Exception as e:
        return None, {
            "latency_ms": round((timeit.default_timer() - t0) * 1000.0, 1),
            "ok": False, "error_class": f"other_{type(e).__name__}",
            "response_tokens": 0, "tokens_per_sec": 0.0,
        }


# ── silicon profile (per-lane EWMA stats) ────────────────────────────────────
def _load_silicon_profile() -> dict:
    if SILICON_PROFILE_PATH.exists():
        try:
            return json.loads(SILICON_PROFILE_PATH.read_text())
        except Exception:
            pass
    return {"lanes": {}, "runs": 0}


def _save_silicon_profile(profile: dict) -> None:
    profile["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    SILICON_PROFILE_PATH.write_text(json.dumps(profile, indent=2))


def _update_silicon_profile(profile: dict, lane_name: str, telemetry: dict) -> None:
    """Exponentially-weighted moving average over per-lane latency / tps / failure."""
    ALPHA = 0.3  # weight on the new observation; older runs decay
    lanes = profile.setdefault("lanes", {})
    lane = lanes.setdefault(lane_name, {
        "calls": 0, "ok_count": 0, "fail_count": 0,
        "ewma_latency_ms": telemetry["latency_ms"],
        "ewma_tokens_per_sec": telemetry["tokens_per_sec"],
        "last_error": None,
    })
    lane["calls"] += 1
    if telemetry["ok"]:
        lane["ok_count"] += 1
        lane["ewma_latency_ms"] = round(
            ALPHA * telemetry["latency_ms"] + (1 - ALPHA) * lane["ewma_latency_ms"], 1
        )
        if telemetry["tokens_per_sec"] > 0:
            lane["ewma_tokens_per_sec"] = round(
                ALPHA * telemetry["tokens_per_sec"] + (1 - ALPHA) * lane["ewma_tokens_per_sec"], 2
            )
    else:
        lane["fail_count"] += 1
        lane["last_error"] = telemetry["error_class"]
    lane["success_rate"] = round(lane["ok_count"] / max(1, lane["calls"]), 3)


def pick_sticky_lane(profile: dict) -> dict | None:
    """Probe lanes in rotation order; return the first that answers a tiny health
    check. Sticky for the rest of the scan to avoid slot churn (OOM safety).
    Updates `profile` with probe telemetry."""
    offset = _load_lane_rotation_offset()
    order = LEMONADE_LANES[offset:] + LEMONADE_LANES[:offset]
    for lane in order:
        probe, telemetry = _post_chat(lane["model"], "OK?", timeout=6.0, max_tokens=2)
        _update_silicon_profile(profile, lane["name"], telemetry)
        if probe and probe.strip():
            _save_lane_rotation_offset(offset + 1)
            print(f"[autoliterature] sticky lane = {lane['name']} ({lane['model']}) "
                  f"probe_latency={telemetry['latency_ms']:.0f}ms", flush=True)
            return lane
        print(f"  [probe] lane '{lane['name']}' didn't respond — error={telemetry['error_class']} "
              f"latency={telemetry['latency_ms']:.0f}ms — trying next", flush=True)
        time.sleep(1.5)
    print("[autoliterature] no Lemonade lane responsive — keyword-only mode", flush=True)
    return None


def ensemble_score_paper(paper: dict, problem_keys: list[str], profile: dict) -> dict:
    """Silicon-as-council ensemble: fire ALL 3 lanes (NPU + iGPU + CPU) in parallel,
    aggregate verdicts with confidence weighting derived from silicon_profile.

    Safety: each lane uses a distinct model on a distinct hardware path (flm vs
    llamacpp-big vs llamacpp-tiny), so no slot contention. Memory pressure is
    bounded by 180-token outputs. We cap parallelism at 3 (one per lane) and
    only run this for the top-K papers, not all of them.
    """
    problems_text = "; ".join(f"{k}: {OPEN_PROBLEMS[k]['unblocks']}" for k in problem_keys)
    prompt = (
        f'You are an autoresearch reviewer. Given a paper and a list of open problems, '
        f'output ONLY JSON: {{"relevant": true|false, "best_problem": "<key>", "rationale": "<one short sentence>"}}.\n\n'
        f'Paper title: {paper.get("title","")[:240]}\n'
        f'Abstract: {paper.get("summary","")[:600]}\n\n'
        f'Open problems with their unblocked experiment IDs:\n{problems_text}\n\n'
        f'Pick the single best matching problem key (or null), and judge true relevance.'
    )

    def _one_lane(lane: dict) -> tuple[dict, dict]:
        txt, telem = _post_chat(lane["model"], prompt, timeout=lane["timeout"], max_tokens=lane["max_tokens"])
        verdict: dict = {"lane": lane["name"], "model": lane["model"],
                         "latency_ms": telem["latency_ms"],
                         "tokens_per_sec": telem["tokens_per_sec"],
                         "ok": telem["ok"], "error_class": telem["error_class"]}
        if txt:
            m = re.search(r"\{.*\}", txt, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    verdict.update({"relevant": parsed.get("relevant"),
                                    "best_problem": parsed.get("best_problem"),
                                    "rationale": parsed.get("rationale", "")[:160]})
                except Exception:
                    verdict["raw"] = txt[:200]
            else:
                verdict["raw"] = txt[:200]
        return verdict, telem

    lane_verdicts: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(LEMONADE_LANES)) as pool:
        futures = {pool.submit(_one_lane, lane): lane for lane in LEMONADE_LANES}
        for fut in as_completed(futures):
            try:
                verdict, telem = fut.result(timeout=30.0)
                _update_silicon_profile(profile, verdict["lane"], telem)
                lane_verdicts.append(verdict)
            except Exception as exc:
                lane_name = futures[fut]["name"]
                lane_verdicts.append({"lane": lane_name, "ok": False,
                                      "error_class": f"future_{type(exc).__name__}"})

    # Aggregate — confidence-weighted majority vote (Beyond Majority Voting / OW)
    # Weight = success_rate from silicon_profile (default 0.5 if untested)
    yes_weight = 0.0; no_weight = 0.0
    problem_votes: dict[str, float] = {}
    voters_ok = 0
    for v in lane_verdicts:
        if not v.get("ok"):
            continue
        voters_ok += 1
        lane_stats = profile.get("lanes", {}).get(v["lane"], {})
        weight = lane_stats.get("success_rate", 0.5) or 0.5
        if v.get("relevant") is True:
            yes_weight += weight
        elif v.get("relevant") is False:
            no_weight += weight
        bp = v.get("best_problem")
        if bp:
            problem_votes[bp] = problem_votes.get(bp, 0.0) + weight

    consensus = "relevant" if yes_weight > no_weight else (
        "irrelevant" if no_weight > yes_weight else "tie"
    )
    best_problem = max(problem_votes.items(), key=lambda kv: kv[1])[0] if problem_votes else None
    # Disagreement = how split was the vote (0 = unanimous, 1 = perfectly split)
    total = yes_weight + no_weight
    disagreement = (1.0 - abs(yes_weight - no_weight) / total) if total > 0 else 0.0

    return {
        "ensemble": True,
        "consensus": consensus,
        "best_problem": best_problem,
        "disagreement": round(disagreement, 3),
        "yes_weight": round(yes_weight, 3),
        "no_weight": round(no_weight, 3),
        "voters_ok": voters_ok,
        "voters_total": len(LEMONADE_LANES),
        "per_lane_verdicts": lane_verdicts,
    }


def llm_score_paper(lane: dict, paper: dict, problem_keys: list[str], profile: dict) -> dict:
    """GEPA-style reflective score with telemetry capture."""
    problems_text = "; ".join(f"{k}: {OPEN_PROBLEMS[k]['unblocks']}" for k in problem_keys)
    prompt = (
        f'You are an autoresearch reviewer. Given a paper and a list of open problems, '
        f'output ONLY JSON: {{"relevant": true|false, "best_problem": "<key>", "rationale": "<one short sentence>"}}.\n\n'
        f'Paper title: {paper.get("title","")[:240]}\n'
        f'Abstract: {paper.get("summary","")[:600]}\n\n'
        f'Open problems with their unblocked experiment IDs:\n{problems_text}\n\n'
        f'Pick the single best matching problem key (or null), and judge true relevance.'
    )
    txt, telemetry = _post_chat(lane["model"], prompt, timeout=lane["timeout"], max_tokens=lane["max_tokens"])
    _update_silicon_profile(profile, lane["name"], telemetry)
    if not txt:
        return {"lane": lane["name"], "raw": None, "relevant": None,
                "latency_ms": telemetry["latency_ms"], "error": telemetry["error_class"]}
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return {"lane": lane["name"], "raw": txt[:200], "relevant": None,
                "latency_ms": telemetry["latency_ms"]}
    try:
        parsed = json.loads(m.group(0))
        parsed.update({"lane": lane["name"], "raw": txt[:200],
                       "latency_ms": telemetry["latency_ms"],
                       "tokens_per_sec": telemetry["tokens_per_sec"]})
        return parsed
    except Exception:
        return {"lane": lane["name"], "raw": txt[:200], "relevant": None,
                "latency_ms": telemetry["latency_ms"]}


# ── seen-papers cache ─────────────────────────────────────────────────────────
def load_seen() -> set[str]:
    if SEEN_PATH.exists():
        try:
            return set(json.loads(SEEN_PATH.read_text()).get("ids", []))
        except Exception:
            return set()
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(json.dumps({
        "ids": sorted(seen),
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(seen),
    }))


# ── persistence helpers ───────────────────────────────────────────────────────
def append_vault_observation(title: str, text: str, obs_type: str = "literature") -> int:
    """Append to vault, return new id."""
    if not VAULT_OBS.exists():
        VAULT_OBS.parent.mkdir(parents=True, exist_ok=True)
        VAULT_OBS.touch()
    last_id = 0
    for line in VAULT_OBS.read_text().splitlines():
        try:
            last_id = max(last_id, json.loads(line).get("id", 0))
        except Exception:
            pass
    new_id = last_id + 1
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    obs = {"id": new_id, "timestamp": ts, "type": obs_type,
           "project": "cohezion", "title": title, "text": text}
    with VAULT_OBS.open("a") as f:
        f.write(json.dumps(obs) + "\n")
    return new_id


def append_jsonl(metric: float, metrics: dict, status: str, description: str, **asi) -> int:
    last_run = 0
    for line in JSONL.read_text().splitlines():
        try:
            last_run = max(last_run, json.loads(line).get("run", 0))
        except Exception:
            pass
    run = last_run + 1
    entry = {
        "run": run, "metric": metric, "metrics": metrics, "status": status,
        "description": description, "timestamp": int(time.time() * 1000),
        "segment": 99, "confidence": 1.0,
        "asi": {"experiment": "E77", **asi},
    }
    with JSONL.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return run


# ── the scan ──────────────────────────────────────────────────────────────────
def run_scan(queries: list[str] | None = None, max_per_query: int = 20) -> dict:
    """Execute one scan iteration. Returns a summary dict."""
    if queries is None:
        # Tied to active open problems — adjusted as findings accumulate
        queries = [
            "recursive self improvement LLM agent",
            "reflective prompt optimization GEPA DSPy",
            "multi-agent voting weighted aggregation calibrated",
            "JEPA latent action world model",
            "automated experimentation agent loop benchmark",
            "early stopping convergence multi-agent ensemble",
        ]

    t0 = timeit.default_timer()
    seen = load_seen()
    print(f"[autoliterature] {len(seen)} paper IDs already seen (cache)", flush=True)

    pulled: list[dict] = []
    for q in queries:
        rows = fetch_arxiv(q, max_results=max_per_query)
        pulled.extend(rows)
        time.sleep(0.5)  # polite pacing for arXiv (request 1/3s)

    # Hugging Face daily papers — single endpoint
    pulled.extend(fetch_hf_daily())

    # Dedupe within this batch by id
    by_id: dict[str, dict] = {}
    for p in pulled:
        if p["id"] not in by_id:
            by_id[p["id"]] = p

    # New = batch_id - seen_id
    new_papers = [p for pid, p in by_id.items() if pid not in seen]

    # Cheap keyword pass on every new paper
    scored: list[dict] = []
    for p in new_papers:
        problems, hits = score_paper(p)
        if hits == 0:
            continue  # off-topic — discard
        unblocks: set[str] = set()
        for prob_key in problems:
            unblocks.update(OPEN_PROBLEMS[prob_key]["unblocks"])
        scored.append({
            **p,
            "matched_problems": problems,
            "keyword_hits": hits,
            "unblocks_experiments": sorted(unblocks),
        })

    scored.sort(key=lambda x: -x["keyword_hits"])

    # Two-tier scoring strategy:
    #   1. ENSEMBLE — top-K=3 highest-keyword papers get scored by ALL 3 lanes
    #      in parallel (silicon-as-council), aggregated with confidence-weighted vote.
    #   2. STICKY  — papers 4..LLM_REFLECT_TOP_K get a single sticky-lane verdict
    #      (cheaper; rotation spreads load across runs).
    # Total LLM budget per scan: 3 lanes * 3 papers + 5 papers = 14 calls max.
    # OOM safety: ensemble triplets fire on distinct hardware paths (flm vs
    # llamacpp-big vs llamacpp-tiny), no slot contention; sticky pass uses one
    # lane only. 1.5s pacing maintained.
    ENSEMBLE_TOP_K = 3
    LLM_REFLECT_TOP_K = 8
    profile = _load_silicon_profile()
    profile["runs"] = profile.get("runs", 0) + 1

    lane_hits: dict[str, int] = {}
    ensemble_verdicts_count = 0
    consensus_breakdown = {"relevant": 0, "irrelevant": 0, "tie": 0}

    # Tier 1: ensemble for top-K
    if scored:
        for paper in scored[:ENSEMBLE_TOP_K]:
            verdict = ensemble_score_paper(paper, paper["matched_problems"], profile)
            paper["llm_verdict"] = verdict
            ensemble_verdicts_count += 1
            consensus_breakdown[verdict["consensus"]] = (
                consensus_breakdown.get(verdict["consensus"], 0) + 1
            )
            for v in verdict.get("per_lane_verdicts", []):
                if v.get("ok"):
                    lane_hits[v["lane"]] = lane_hits.get(v["lane"], 0) + 1
            time.sleep(1.5)  # slow-and-steady between ensemble fires

    # Tier 2: sticky-lane for the rest
    lane = pick_sticky_lane(profile) if len(scored) > ENSEMBLE_TOP_K else None
    if lane is not None:
        for paper in scored[ENSEMBLE_TOP_K:LLM_REFLECT_TOP_K]:
            verdict = llm_score_paper(lane, paper, paper["matched_problems"], profile)
            paper["llm_verdict"] = verdict
            lane_hits[verdict.get("lane", "?")] = lane_hits.get(verdict.get("lane", "?"), 0) + 1
            time.sleep(1.5)
    _save_silicon_profile(profile)

    # Print silicon profile (so the operator sees lane health each run)
    print(f"\n[silicon] profile after {profile['runs']} runs:", flush=True)
    for lane_name in ("npu", "igpu", "cpu"):
        s = profile.get("lanes", {}).get(lane_name)
        if s:
            print(f"  {lane_name:5s}: calls={s['calls']:3d} ok={s['ok_count']:3d} "
                  f"fail={s['fail_count']:3d} success={s['success_rate']*100:3.0f}% "
                  f"ewma_lat={s['ewma_latency_ms']:6.0f}ms ewma_tps={s['ewma_tokens_per_sec']:5.1f} "
                  f"last_err={s['last_error']}", flush=True)
        else:
            print(f"  {lane_name:5s}: not yet tested", flush=True)

    # Update seen cache with everything we pulled (so off-topic papers don't keep showing up)
    seen.update(by_id.keys())
    save_seen(seen)

    elapsed = timeit.default_timer() - t0

    print(f"[autoliterature] pulled={len(pulled)} unique={len(by_id)} new={len(new_papers)} "
          f"on_topic={len(scored)} elapsed={elapsed:.1f}s", flush=True)

    if scored:
        print(f"\n  Top {min(5, len(scored))} on-topic papers:")
        for p in scored[:5]:
            print(f"    [{p['keyword_hits']} hits, unblocks={','.join(p['unblocks_experiments'])}]")
            print(f"      {p['title'][:90]}")
            print(f"      {p['url']}  ({p['source']})")

    # ── second leg: HF model scout — tip-of-the-spear fine-tuning candidates ─
    print("\n[autoliterature] model scout: pulling HF trending text-gen models...", flush=True)
    seen_models = load_seen_models()
    pulled_models = fetch_hf_models(limit=60)
    finetunable = filter_finetunable(pulled_models)
    new_models = [m for m in finetunable if m["id"] not in seen_models]
    print(f"[autoliterature] scout: pulled={len(pulled_models)} finetunable={len(finetunable)} "
          f"new={len(new_models)} (seen_cache={len(seen_models)})", flush=True)

    # Update seen-models cache with everything we pulled (so off-license models don't keep showing up)
    seen_models.update(m["id"] for m in pulled_models)
    save_seen_models(seen_models)

    if new_models:
        print(f"\n  Top {min(5, len(new_models))} fine-tuning candidates:")
        # Sort by likes * sqrt(downloads + 1) — heuristic for "interesting AND adopted"
        import math as _math
        new_models.sort(
            key=lambda m: -(m.get("likes", 0) * _math.sqrt(m.get("downloads", 0) + 1))
        )
        for m in new_models[:5]:
            params_b = m["params_estimate"] / 1e9 if m["params_estimate"] else 0.0
            uncertain = " [license:?]" if m.get("license_uncertain") else ""
            print(f"    {m['model_id']} ({params_b:.1f}B, lic={m['license']}{uncertain}, "
                  f"likes={m['likes']}, dl={m['downloads']})")

    summary = {
        "queries_run": len(queries) + 1,  # +1 for HF daily
        "papers_pulled": len(pulled),
        "unique_in_batch": len(by_id),
        "new_papers": len(new_papers),
        "on_topic_count": len(scored),
        "off_topic_count": len(new_papers) - len(scored),
        "ensemble_verdicts": ensemble_verdicts_count,
        "ensemble_consensus_breakdown": consensus_breakdown,
        "scored_top10": [
            {"id": p["id"], "title": p["title"][:120], "url": p["url"],
             "matched_problems": p["matched_problems"], "keyword_hits": p["keyword_hits"],
             "unblocks_experiments": p["unblocks_experiments"],
             "llm_verdict": p.get("llm_verdict")}
            for p in scored[:10]
        ],
        # Model scout
        "models_pulled": len(pulled_models),
        "models_finetunable": len(finetunable),
        "new_finetunable_models": len(new_models),
        "top_finetuning_candidates": [
            {"model_id": m["model_id"], "params_b": round(m["params_estimate"]/1e9, 2),
             "license": m["license"], "likes": m["likes"], "downloads": m["downloads"],
             "url": m["url"], "library": m["library"]}
            for m in new_models[:8]
        ],
        "models_seen_cache_size": len(seen_models),
        # Hardware council
        "elapsed_s": round(elapsed, 2),
        "seen_cache_size": len(seen),
        "llm_lane_used": (lane or {}).get("name"),
        "llm_lane_model": (lane or {}).get("model"),
        "llm_lane_call_count": sum(lane_hits.values()) if lane_hits else 0,
        "llm_lane_hits": lane_hits,
        "silicon_profile": profile.get("lanes", {}),
        "silicon_runs": profile.get("runs", 0),
    }

    # Persist
    status = "keep" if len(scored) > 0 else "discard"
    description = (f"E77 autoliterature: pulled={len(pulled)} unique={len(by_id)} "
                   f"new={len(new_papers)} on_topic={len(scored)}")
    run = append_jsonl(metric=float(len(scored)), metrics=summary,
                       status=status, description=description,
                       on_topic=len(scored), new_papers=len(new_papers))
    summary["jsonl_run"] = run

    if scored:
        # Compose vault observation summarizing the top hits
        text_parts = [
            f"E77 autoliterature scan: {len(scored)} on-topic new papers across "
            f"{len(queries)+1} queries (elapsed {elapsed:.1f}s).",
            "Top hits:",
        ]
        for p in scored[:5]:
            text_parts.append(
                f"  - {p['title'][:120]} ({p['url']}, {p['source']}, "
                f"keyword_hits={p['keyword_hits']}, unblocks={','.join(p['unblocks_experiments'])})"
            )
        text_parts.append(
            f"Cache: {len(seen)} paper IDs total; off-topic this run: "
            f"{len(new_papers) - len(scored)}; "
            f"open-problem registry: {sorted(OPEN_PROBLEMS.keys())}"
        )
        obs_id = append_vault_observation(
            title=f"E77 scan: {len(scored)} on-topic new papers (top: {scored[0]['title'][:60]})",
            text="\n".join(text_parts),
        )
        summary["vault_obs_id"] = obs_id
    else:
        # Even discard runs get a vault marker so we have a heartbeat
        obs_id = append_vault_observation(
            title=f"E77 scan: 0 on-topic papers ({len(new_papers)} new total)",
            text=f"E77 autoliterature scan ran {len(queries)+1} queries, found "
                 f"{len(new_papers)} new papers total but none matched the open-problem "
                 f"keyword registry. Cache size now {len(seen)}.",
        )
        summary["vault_obs_id"] = obs_id

    return summary


if __name__ == "__main__":
    summary = run_scan()
    print(f"\n[autoliterature] DONE — vault obs #{summary.get('vault_obs_id')}, "
          f"jsonl run #{summary.get('jsonl_run')}", flush=True)
