"""OOM guardrails for Lemonade model loading with smart routing and hot-swap support.

Three protection layers:
1. Memory gate — blocks loads when available_ram < model_footprint + RAM_LOAD_BUFFER_GB
2. Smart routing — selects the largest model that fits given current RAM state
3. Safe load — enforces ctx_size bound via Lemonade API before any heavy load

Hard-won context (harness N3):
- ctx_size=0 on a heavy LLM (≥26B) fills KV cache to full trained context (~256K tokens)
  and hangs the system — this is an OOM that systemd-oomd cannot recover from.
- Strix Halo: 122GB LPDDR5X UMA shared by iGPU (RDNA 3.5) and CPU (AVX-512). Up to 6 LLMs
  CAN be co-loaded simultaneously (max_models: llm=6 per /api/v1/health). get_active_uma_gb()
  accounts for all currently loaded UMA footprints — NOT a single-model eviction model.
- NPU (XDNA2 SRAM) is separate from UMA — FLM models do NOT compete for RAM.
- N/A ctx_size = non-LLM model (image/audio/TTS) — different memory model, not guarded here.
"""

from __future__ import annotations

import logging
import pathlib
import time
from enum import Enum
from typing import NamedTuple

import httpx


logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

LEMONADE_BASE = "http://localhost:13305"
SAFE_CTX_LIMIT = 16384  # hard cap applied before any heavy model load
RAM_LOAD_BUFFER_GB = 8.0  # keep at least this much RAM free after loading
MAX_CTX_SIZE_LIGHT = 32768  # models <5GB can safely use larger context

# Approximate weight footprints (GB, Q4_K_M quantization where applicable).
# Source: ~/.cohezion/storage_manifest.json + model spec sheets.
# Footprint = weight bytes loaded into UMA; KV cache adds ~(ctx/4096) × 0.5 GB per 10B params.
MODEL_FOOTPRINT_GB: dict[str, float] = {
    # ── Non-LLM (image / audio / TTS) — different memory model ──────────────
    "Flux-2-Klein-9B-GGUF": 19.0,  # diffusion weights, no KV cache
    "SD-Turbo": 5.2,  # diffusion weights
    "RealESRGAN-x4plus": 0.07,
    "RealESRGAN-x4plus-anime": 0.07,
    "Whisper-Large-v3-Turbo": 1.62,  # encoder+decoder, no KV cache
    "kokoro-v1": 0.35,  # TTS
    # ── Embeddings (no generative KV cache) ──────────────────────────────────
    "nomic-embed-text-v2-moe-GGUF": 0.51,
    "Qwen3-Embedding-0.6B-GGUF": 0.64,
    # ── Small LLMs (safe at any reasonable ctx) ──────────────────────────────
    "Qwen3-0.6B-GGUF": 0.38,
    "Bonsai-1.7B-gguf": 1.05,
    "Bonsai-4B-gguf": 2.40,
    "Gemma-4-E2B-it-GGUF": 4.09,
    # ── Medium LLMs (need ctx guard at high load) ────────────────────────────
    "Bonsai-8B-gguf": 5.25,
    "DeepSeek-Qwen3-8B-GGUF": 5.25,
    "Gemma-4-E4B-it-GGUF": 5.97,
    # ── Heavy LLMs (require available_ram > footprint + RAM_LOAD_BUFFER_GB) ──
    "Qwen3.6-27B-GGUF": 16.0,
    "Gemma-4-26B-A4B-it-GGUF": 18.1,
    "Gemma-4-31B-it-GGUF": 19.5,
    "Qwen3.5-35B-A3B-GGUF": 23.1,
    "Nemotron-3-Nano-30B-A3B-GGUF": 22.8,
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": 18.6,
    "Qwen3.6-35B-A3B-GGUF": 23.3,
    "Qwen3.6-35B-A3B-MTP-GGUF": 23.3,  # MTP variant, same weights
}

HEAVY_THRESHOLD_GB = 5.0  # models above this need memory gate
# Footprint assumed for a model absent from MODEL_FOOTPRINT_GB. Deliberately above
# HEAVY_THRESHOLD_GB so an unrecognised name is gated rather than waved through.
UNKNOWN_ASSUMED_GB = 8.0

# ──────────────────────────────────────────────────────────────────────────────
# Compute tier classification (verified against /api/v1/health 2026-07-01)
# ──────────────────────────────────────────────────────────────────────────────


class ComputeTier(Enum):
    NPU = "npu"  # XDNA2 SRAM — separate from UMA, FLM recipe models only
    IGPU = "igpu"  # RDNA 3.5 vulkan — UMA shared with CPU (all GGUF LLMs)
    CPU = "cpu"  # AVX-512 — UMA shared with iGPU (kokoro TTS)
    SPECIALIZED = "spec"  # sd-cpp/whispercpp — iGPU device, no KV cache


# On Strix Halo, IGPU + CPU + SPECIALIZED all draw from the 122GB LPDDR5X UMA pool.
# NPU (XDNA2 SRAM ~2GB) is completely separate — FLM loads never compete for UMA.
UMA_TIERS: frozenset[ComputeTier] = frozenset(
    {ComputeTier.IGPU, ComputeTier.CPU, ComputeTier.SPECIALIZED}
)

# Static tier per model — derived from /api/v1/health device/recipe_options fields.
# All llamacpp+vulkan models land on iGPU even when catalog shows llamacpp_backend=N/A.
MODEL_TIER: dict[str, ComputeTier] = {
    # NPU — FLM recipe (XDNA2 SRAM, NOT in MODEL_FOOTPRINT_GB)
    "llama3.2-1b-FLM": ComputeTier.NPU,
    "deepseek-r1-0528-8b-FLM": ComputeTier.NPU,
    "gemma3-4b-FLM": ComputeTier.NPU,
    # iGPU — all GGUF LLMs (device: gpu, llamacpp_backend: vulkan)
    "Qwen3-0.6B-GGUF": ComputeTier.IGPU,
    "Qwen3-Embedding-0.6B-GGUF": ComputeTier.IGPU,
    "Bonsai-1.7B-gguf": ComputeTier.IGPU,
    "Bonsai-4B-gguf": ComputeTier.IGPU,
    "Gemma-4-E2B-it-GGUF": ComputeTier.IGPU,
    "Bonsai-8B-gguf": ComputeTier.IGPU,
    "DeepSeek-Qwen3-8B-GGUF": ComputeTier.IGPU,
    "Gemma-4-E4B-it-GGUF": ComputeTier.IGPU,
    "nomic-embed-text-v2-moe-GGUF": ComputeTier.IGPU,
    "Qwen3.6-27B-GGUF": ComputeTier.IGPU,
    "Gemma-4-26B-A4B-it-GGUF": ComputeTier.IGPU,
    "Gemma-4-31B-it-GGUF": ComputeTier.IGPU,
    "Qwen3.5-35B-A3B-GGUF": ComputeTier.IGPU,
    "Nemotron-3-Nano-30B-A3B-GGUF": ComputeTier.IGPU,
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": ComputeTier.IGPU,
    "Qwen3.6-35B-A3B-GGUF": ComputeTier.IGPU,
    "Qwen3.6-35B-A3B-MTP-GGUF": ComputeTier.IGPU,
    # CPU — kokoro TTS (device: cpu per /api/v1/health)
    "kokoro-v1": ComputeTier.CPU,
    # SPECIALIZED — image gen / transcription (iGPU device but sd-cpp/whispercpp recipe)
    "Flux-2-Klein-9B-GGUF": ComputeTier.SPECIALIZED,
    "SD-Turbo": ComputeTier.SPECIALIZED,
    "RealESRGAN-x4plus": ComputeTier.SPECIALIZED,
    "RealESRGAN-x4plus-anime": ComputeTier.SPECIALIZED,
    "Whisper-Large-v3-Turbo": ComputeTier.SPECIALIZED,
}

# ──────────────────────────────────────────────────────────────────────────────
# Task → model routing table
# Each entry: (preferred, fallback) — fallback is always a smaller model.
# Routing respects memory state: if preferred doesn't fit, fallback is used.
# ──────────────────────────────────────────────────────────────────────────────

_TASK_ROUTING: dict[str, tuple[str, str]] = {
    # Classification and routing — tiny, always warm
    "short_categorical": ("Bonsai-1.7B-gguf", "Qwen3-0.6B-GGUF"),
    "short_answer": ("Bonsai-4B-gguf", "Bonsai-1.7B-gguf"),
    # Code generation — Qwen3-Coder is purpose-built; fall to Gemma-4-E4B
    "code": ("Qwen3-Coder-30B-A3B-Instruct-GGUF", "Gemma-4-E4B-it-GGUF"),
    # Reasoning / planning — DeepSeek excels at chain-of-thought
    "reasoning": ("DeepSeek-Qwen3-8B-GGUF", "Bonsai-8B-gguf"),
    # QA judging — Bonsai is non-thinking, reliable content extraction
    "qa_judge": ("Bonsai-8B-gguf", "Bonsai-4B-gguf"),
    # General generation
    "medium_generation": ("Gemma-4-E4B-it-GGUF", "Bonsai-8B-gguf"),
    "long_generation": ("Qwen3.6-35B-A3B-GGUF", "Gemma-4-E4B-it-GGUF"),
    # Vision tasks (all three have mmproj)
    "vision": ("Gemma-4-26B-A4B-it-GGUF", "Gemma-4-E4B-it-GGUF"),
    # Embedding
    "embed": ("nomic-embed-text-v2-moe-GGUF", "Qwen3-Embedding-0.6B-GGUF"),
    # Audio
    "transcribe": ("Whisper-Large-v3-Turbo", "Whisper-Large-v3-Turbo"),
    "tts": ("kokoro-v1", "kokoro-v1"),
    # Image generation
    "image_gen": ("Flux-2-Klein-9B-GGUF", "SD-Turbo"),
    # Skill refinement / self-improvement — heavy reasoning with long context
    "skill_refine": ("Qwen3.6-35B-A3B-GGUF", "DeepSeek-Qwen3-8B-GGUF"),
}


# ──────────────────────────────────────────────────────────────────────────────
# Memory utilities
# ──────────────────────────────────────────────────────────────────────────────


class MemorySnapshot(NamedTuple):
    total_gb: float
    available_gb: float
    used_gb: float

    @classmethod
    def capture(cls) -> MemorySnapshot:
        """Read current RAM state from /proc/meminfo."""
        info: dict[str, int] = {}
        try:
            for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.split()[0])  # kB
        except Exception:
            return cls(total_gb=128.0, available_gb=20.0, used_gb=108.0)

        total = info.get("MemTotal", 0) / (1024**2)
        available = info.get("MemAvailable", 0) / (1024**2)
        return cls(total_gb=total, available_gb=available, used_gb=total - available)


def get_available_ram_gb() -> float:
    """Return MemAvailable in GB from /proc/meminfo."""
    return MemorySnapshot.capture().available_gb


# ──────────────────────────────────────────────────────────────────────────────
# ctx_size validation
# ──────────────────────────────────────────────────────────────────────────────


def _get_recipe_ctx(model_name: str, timeout_s: float = 2.0) -> int | None:
    """Query Lemonade for a model's recipe_options.ctx_size. Returns None on error."""
    try:
        url = f"{LEMONADE_BASE}/api/v1/models/{model_name}"
        resp = httpx.get(url, timeout=timeout_s)
        if resp.status_code == 200:
            recipe = resp.json().get("recipe_options") or {}
            ctx = recipe.get("ctx_size")
            if ctx is not None and ctx != "N/A":
                return int(ctx)
    except Exception:
        pass
    return None


def audit_heavy_models(timeout_s: float = 2.0) -> dict[str, int | None]:
    """Audit all heavy (≥5GB) models for their recipe_options.ctx_size.

    Returns a dict of {model_name: ctx_size_or_None}. A ctx_size of 0 or None on
    a heavy LLM is an OOM hazard (N3).
    """
    results: dict[str, int | None] = {}
    for name, gb in MODEL_FOOTPRINT_GB.items():
        if gb >= HEAVY_THRESHOLD_GB:
            ctx = _get_recipe_ctx(name, timeout_s=timeout_s)
            results[name] = ctx
            if ctx == 0:
                logger.error(
                    "OOM HAZARD: %s (%.1f GB) has ctx_size=0 — will OOM on load. "
                    "Run: curl -X POST http://localhost:13305/api/v1/load "
                    '-d \'{"model_name": "%s", "ctx_size": %d, "save_options": true}\'',
                    name,
                    gb,
                    name,
                    SAFE_CTX_LIMIT,
                )
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Memory gate
# ──────────────────────────────────────────────────────────────────────────────


class OOMRisk(NamedTuple):
    safe: bool
    model: str
    available_gb: float
    footprint_gb: float
    reason: str


def _is_model_loaded(model_name: str, timeout_s: float = 2.0) -> bool:
    """True if the router reports model_name already resident. A loaded model needs no new
    memory to reuse, so the UMA budget check does not apply. Matches on the id or the
    checkpoint substring, since /api/v1/health reports checkpoints (e.g.
    'unsloth/gemma-4-26B-A4B-it-GGUF:UD-Q4_K_M') while callers pass the short id
    ('Gemma-4-26B-A4B-it-GGUF'). Fail-CLOSED (False) on any error — an unreachable router
    means fall through to the real budget check, never a false clearance.
    """
    try:
        with httpx.Client(timeout=timeout_s) as c:
            r = c.get(f"{LEMONADE_BASE}/api/v1/health")
            r.raise_for_status()
            key = model_name.lower()
            for m in r.json().get("all_models_loaded", []):
                ck = str(m.get("checkpoint", "")).lower()
                if key in ck or ck.split(":")[0].split("/")[-1] == key:
                    return True
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return False
    return False


def _catalog_size_gb(model_name: str, timeout_s: float = 2.0) -> float | None:
    """Ask the router for a model's real size instead of guessing.

    UNKNOWN_ASSUMED_GB is a floor, not a measurement. Observed 2026-07-19:
    LMX-Omni-52B-Halo is 44.77GB and the 8GB assumption cleared it with 46GB free --
    a load that would have left ~1GB and reproduced the hard freeze. The catalog carries
    `size` for every entry, including the ones absent from MODEL_FOOTPRINT_GB, so the
    honest default is to LOOK IT UP and only fall back to the assumption when the router
    is unreachable.
    """
    try:
        with httpx.Client(timeout=timeout_s) as c:
            r = c.get(f"{LEMONADE_BASE}/api/v1/models", params={"show_all": "true"})
            r.raise_for_status()
            for m in r.json().get("data", []):
                if m.get("id") == model_name:
                    size = m.get("size")
                    return float(size) if size is not None else None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
    return None


def check_oom_risk(model_name: str, available_gb: float | None = None) -> OOMRisk:
    """Check whether loading model_name is safe given current or supplied RAM state.

    Uses /proc/meminfo MemAvailable which already reflects all currently loaded models.
    For a topology-aware view of committed UMA, call get_active_uma_gb().
    NPU (FLM) models are always UMA-safe — they use XDNA2 SRAM, not the UMA pool.
    """
    # An ABSENT model must not read as a 0GB model. The previous `.get(name, 0.0)` made
    # every unrecognised name fall under HEAVY_THRESHOLD_GB and return
    # "small model — no gate needed" — a fail-open that looks like a positive clearance.
    # Observed 2026-07-18: the table holds 23 models and ZERO FLM/NPU entries, so every
    # NPU model auto-passed. That reading was reported as "the guard confirms UMA-safe"
    # when the guard had simply never heard of them, and ~14GB was consumed anyway.
    # Unknown now means "assume heavy until measured": still allowed when there is ample
    # headroom, but it must clear the same budget check as a known heavy model.
    known = model_name in MODEL_FOOTPRINT_GB
    avail = available_gb if available_gb is not None else get_available_ram_gb()

    # A model that is ALREADY LOADED needs zero new memory to reuse — its weights are
    # already resident and counted in MemAvailable. Blocking it because
    # footprint+buffer > avail is wrong: the load already happened. Observed 2026-07-19:
    # 6 models pinned RAM at 25.8GB, and Gemma-4-26B (resident, 18.1GB) failed the
    # 26.1GB gate, so EVERY task reusing it aborted — a whole task queue deadlocked on
    # 0.3GB for a model that required no load at all. Check what is actually loaded first.
    if available_gb is None and _is_model_loaded(model_name):
        return OOMRisk(True, model_name, avail, 0.0, "already loaded — reuse needs no memory")

    # NPU models are absent from MODEL_FOOTPRINT_GB BY DESIGN (see MODEL_TIER: "XDNA2 SRAM,
    # NOT in MODEL_FOOTPRINT_GB") — they do not draw on the UMA pool, so a UMA budget check
    # does not apply to them. Recognise them explicitly rather than letting them fall
    # through the unknown-model path below, which would over-gate them.
    if MODEL_TIER.get(model_name) is ComputeTier.NPU:
        return OOMRisk(True, model_name, avail, 0.0, "NPU (XDNA2 SRAM) — outside the UMA pool")

    # An ABSENT, UNTIERED model must not read as a 0GB model. The previous
    # `.get(name, 0.0)` made every unrecognised name fall under HEAVY_THRESHOLD_GB and
    # return "small model — no gate needed" — a fail-open that looks like a clearance.
    # A newly-pulled 30B model would have sailed through it. Unknown now means "assume
    # heavy until measured": allowed with ample headroom, gated otherwise.
    if known:
        footprint = MODEL_FOOTPRINT_GB[model_name]
    else:
        looked_up = _catalog_size_gb(model_name)
        footprint = looked_up if looked_up is not None else UNKNOWN_ASSUMED_GB
    required = footprint + RAM_LOAD_BUFFER_GB

    if known and footprint < HEAVY_THRESHOLD_GB:
        return OOMRisk(True, model_name, avail, footprint, "small model — no gate needed")

    if not known and avail >= required:
        return OOMRisk(
            True,
            model_name,
            avail,
            footprint,
            f"unknown model — assumed {UNKNOWN_ASSUMED_GB:.0f}GB, within budget "
            f"(add it to MODEL_FOOTPRINT_GB or MODEL_TIER to gate it accurately)",
        )

    if avail >= required:
        return OOMRisk(True, model_name, avail, footprint, "within memory budget")

    return OOMRisk(
        safe=False,
        model=model_name,
        available_gb=avail,
        footprint_gb=footprint,
        reason=(
            f"insufficient RAM: need {required:.1f}GB "
            f"({footprint:.1f}GB model + {RAM_LOAD_BUFFER_GB:.0f}GB buffer), "
            f"have {avail:.1f}GB"
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Smart routing
# ──────────────────────────────────────────────────────────────────────────────


def safe_model_for_task(task_type: str, available_gb: float | None = None) -> str:
    """Return the safest model ID for task_type that fits in current RAM.

    Tries the preferred model first; falls back to the smaller alternative if
    the preferred model would risk OOM.  Falls back to Bonsai-4B-gguf as a
    last-resort safe model if neither routing entry fits.
    """
    avail = available_gb if available_gb is not None else get_available_ram_gb()
    preferred, fallback = _TASK_ROUTING.get(task_type, ("Bonsai-8B-gguf", "Bonsai-4B-gguf"))

    risk = check_oom_risk(preferred, available_gb=avail)
    if risk.safe:
        return preferred

    risk_fb = check_oom_risk(fallback, available_gb=avail)
    if risk_fb.safe:
        logger.warning(
            "OOM gate: %s blocked (%.1f GB needed, %.1f GB available). "
            "Routing task '%s' to fallback %s.",
            preferred,
            risk.footprint_gb + RAM_LOAD_BUFFER_GB,
            avail,
            task_type,
            fallback,
        )
        return fallback

    # Both blocked — use the always-safe tiny model
    logger.error(
        "OOM gate: both %s and %s blocked for task '%s'. "
        "System RAM critically low (%.1f GB). Using Bonsai-4B-gguf.",
        preferred,
        fallback,
        task_type,
        avail,
    )
    return "Bonsai-4B-gguf"


# ──────────────────────────────────────────────────────────────────────────────
# Safe load (with ctx_size enforcement)
# ──────────────────────────────────────────────────────────────────────────────


def safe_load(
    model_name: str,
    ctx_size: int = SAFE_CTX_LIMIT,
    timeout_s: float = 30.0,
) -> bool:
    """Load model via Lemonade API with explicit ctx_size bound.

    Always sets save_options=True so the bound persists across daemon restarts
    (the regression guard for the N3 regression: harness entry says Qwen3.6-35B
    reverted to ctx_size=0 after a lemond restart — `save_options` re-persists on load).

    Returns True on success, False if blocked by OOM gate or API error.
    """
    risk = check_oom_risk(model_name)
    if not risk.safe:
        logger.error("safe_load blocked: %s", risk.reason)
        return False

    # Clamp ctx to SAFE_CTX_LIMIT for heavy models
    footprint = MODEL_FOOTPRINT_GB.get(model_name, 0.0)
    effective_ctx = ctx_size if footprint < HEAVY_THRESHOLD_GB else min(ctx_size, SAFE_CTX_LIMIT)

    try:
        resp = httpx.post(
            f"{LEMONADE_BASE}/api/v1/load",
            json={"model_name": model_name, "ctx_size": effective_ctx, "save_options": True},
            timeout=timeout_s,
        )
        if resp.status_code == 200:
            logger.info("safe_load OK: %s (ctx=%d)", model_name, effective_ctx)
            return True
        logger.warning(
            "safe_load API error %d for %s: %s", resp.status_code, model_name, resp.text[:200]
        )
        return False
    except Exception as exc:
        logger.warning("safe_load exception for %s: %s", model_name, exc)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Hot swap (pre-fetch)
# ──────────────────────────────────────────────────────────────────────────────

_prefetch_in_flight: dict[str, float] = {}  # model_name → start_time


def prefetch_for_next_task(
    next_task_type: str,
    ctx_size: int = SAFE_CTX_LIMIT,
    cooldown_s: float = 60.0,
) -> bool:
    """Pre-load the model for next_task_type while the current task is running.

    Hot swap contract:
    - The OmniRouter (max_loaded_models=1) will evict the current model when the
      prefetch load arrives. Pre-fetching is safe ONLY if the current task is nearly done
      (within the last ~10% of estimated duration) to avoid evicting the model mid-task.
    - This function is a hint, not a guarantee. It is safe to call frequently —
      the cooldown_s parameter prevents redundant rapid reloads.
    - Caller is responsible for ensuring the current task is not sensitive to mid-flight eviction.

    Returns True if a prefetch was initiated, False if skipped (cooldown / OOM gate).
    """
    model = safe_model_for_task(next_task_type)
    now = time.monotonic()

    last = _prefetch_in_flight.get(model, 0.0)
    if now - last < cooldown_s:
        return False  # within cooldown window, skip

    risk = check_oom_risk(model)
    if not risk.safe:
        logger.debug("prefetch skipped (OOM gate): %s", risk.reason)
        return False

    footprint = MODEL_FOOTPRINT_GB.get(model, 0.0)
    effective_ctx = ctx_size if footprint < HEAVY_THRESHOLD_GB else min(ctx_size, SAFE_CTX_LIMIT)

    try:
        httpx.post(
            f"{LEMONADE_BASE}/api/v1/load",
            json={"model_name": model, "ctx_size": effective_ctx, "save_options": True},
            timeout=5.0,  # fire-and-forget; the server handles async loading
        )
        _prefetch_in_flight[model] = now
        logger.debug("prefetch initiated: %s (ctx=%d)", model, effective_ctx)
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Startup audit (call once at module import or service start)
# ──────────────────────────────────────────────────────────────────────────────


def run_startup_audit(log_clean: bool = False) -> list[str]:
    """Audit heavy models for ctx_size=0 hazards. Returns list of hazardous model names.

    Should be called at process start (e.g., from _get_orchestrator() on first use).
    Low cost: only queries the /api/v1/models/<id> endpoint per heavy model.
    """
    snap = MemorySnapshot.capture()
    logger.info(
        "OOM guard startup: %.1f GB total, %.1f GB available, %.1f GB used",
        snap.total_gb,
        snap.available_gb,
        snap.used_gb,
    )

    # Warn if any heavy model won't fit given current RAM
    tight: list[str] = []
    for name, gb in sorted(MODEL_FOOTPRINT_GB.items(), key=lambda x: -x[1]):
        if gb >= HEAVY_THRESHOLD_GB:
            risk = check_oom_risk(name, available_gb=snap.available_gb)
            if not risk.safe:
                tight.append(name)
                logger.warning("OOM risk at startup: %s — %s", name, risk.reason)

    hazardous = [n for n, ctx in audit_heavy_models().items() if ctx == 0]

    if not hazardous and not tight and log_clean:
        logger.info("OOM guard: all heavy models have bounded ctx_size. RAM OK.")

    return hazardous


# ──────────────────────────────────────────────────────────────────────────────
# Live topology (multi-tenant, tier-aware)
# ──────────────────────────────────────────────────────────────────────────────


class BackendEntry(NamedTuple):
    """One running backend in the OmniRouter."""

    model_name: str
    tier: ComputeTier
    footprint_gb: float
    backend_url: str
    device: str


def get_live_topology(timeout_s: float = 2.0) -> list[BackendEntry]:
    """Return all currently loaded backends from /api/v1/health with tier classification.

    The OmniRouter supports up to 6 simultaneous backends per type (max_models: llm=6,
    image=6, etc.) — NOT max_loaded_models=1. Call this to understand the real multi-model
    state before making load decisions.

    Returns an empty list when the OmniRouter is unreachable.
    """
    try:
        resp = httpx.get(f"{LEMONADE_BASE}/api/v1/health", timeout=timeout_s)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    entries: list[BackendEntry] = []
    for m in resp.json().get("all_models_loaded", []):
        name = m.get("model_name", "")
        tier = MODEL_TIER.get(name, ComputeTier.IGPU)  # default iGPU (all GGUF are vulkan)
        footprint = MODEL_FOOTPRINT_GB.get(name, 0.0)
        entries.append(
            BackendEntry(
                model_name=name,
                tier=tier,
                footprint_gb=footprint,
                backend_url=m.get("backend_url", ""),
                device=m.get("device", ""),
            )
        )
    return entries


def tier_for_model(model_name: str) -> ComputeTier:
    """Return the compute tier for a model. Defaults to IGPU for unknown GGUF names."""
    return MODEL_TIER.get(model_name, ComputeTier.IGPU)


def get_active_uma_gb(timeout_s: float = 2.0) -> float:
    """Return GB of UMA committed to currently loaded models (iGPU + CPU + SPECIALIZED).

    NPU (FLM) models use XDNA2 SRAM and are excluded — they don't compete for UMA.
    Complement to /proc/meminfo MemAvailable: this shows WHERE the committed memory is,
    while MemAvailable shows how much the OS has left.
    """
    total = 0.0
    for entry in get_live_topology(timeout_s=timeout_s):
        if entry.tier in UMA_TIERS:
            total += entry.footprint_gb
    return total


def models_on_tier(
    tier: ComputeTier,
    topology: list[BackendEntry] | None = None,
) -> list[str]:
    """Return model names currently running on a specific compute tier."""
    topo = topology if topology is not None else get_live_topology()
    return [e.model_name for e in topo if e.tier == tier]


def topology_summary(timeout_s: float = 2.0) -> dict[str, object]:
    """Return a human-readable topology summary for logging / dashboards."""
    snap = MemorySnapshot.capture()
    topo = get_live_topology(timeout_s=timeout_s)
    active_uma = sum(e.footprint_gb for e in topo if e.tier in UMA_TIERS)
    by_tier: dict[str, list[str]] = {}
    for e in topo:
        by_tier.setdefault(e.tier.value, []).append(f"{e.model_name}({e.footprint_gb:.1f}GB)")
    return {
        "ram_total_gb": round(snap.total_gb, 1),
        "ram_available_gb": round(snap.available_gb, 1),
        "uma_committed_gb": round(active_uma, 1),
        "backends_loaded": len(topo),
        "by_tier": by_tier,
    }
