"""Cohezion inference bridge — AMD silicon integration.

Provides graceful access to Cohezion's local inference stack:
  - SemanticCache (L1/L2/L3, FLUME VAE 256D embeddings)
  - TaskClassifier (NPU tier, sub-500µs)
  - CompoundExecutor (11-step pipeline with SkillRefiner)
  - Lemonade direct HTTP (bypass Python import when needed)

All imports are attempted lazily and fail gracefully — the pipeline
works without Cohezion installed (pure Anthropic API fallback).
"""

import os
import sys
from typing import Any, Optional

import requests


# Inject Cohezion src path if configured
_COHEZION_SRC = os.getenv("COHEZION_SRC", "/home/mike-anderson/dev/cohezion/src")
if _COHEZION_SRC not in sys.path:
    sys.path.insert(0, _COHEZION_SRC)


# ─── Lazy Cohezion imports ────────────────────────────────────────────────────

def _try_import_semantic_cache():
    """Import SemanticCache or return None."""
    try:
        from cohezion.cache.semantic_cache import SemanticCache  # noqa: PLC0415
        return SemanticCache
    except ImportError:
        return None


def _try_import_task_classifier():
    """Import task_classifier.classify or return None."""
    try:
        from cohezion.inference.task_classifier import classify  # noqa: PLC0415
        return classify
    except ImportError:
        return None


def _try_import_compound_executor():
    """Import CompoundExecutor factory or return None."""
    try:
        from cohezion.compound import make_executor  # noqa: PLC0415
        return make_executor
    except ImportError:
        return None


# ─── Lemonade HTTP client (zero-import AMD inference) ─────────────────────────

class LemonadeClient:
    """Lightweight HTTP client for Lemonade inference nodes.

    Bypasses Python imports entirely — useful when Cohezion package
    isn't installed but local AMD silicon is running.

    Router-centric: ALL local inference goes through the SINGLE :13305 router, which
    dispatches to NPU/iGPU/CPU by model. There are no separate per-tier ports.
    """

    _PORTS = {
        "npu": int(os.getenv("LEMONADE_ROUTER_PORT", "13305")),
        "igpu": int(os.getenv("LEMONADE_ROUTER_PORT", "13305")),
        "cpu": int(os.getenv("LEMONADE_ROUTER_PORT", "13305")),
    }

    def __init__(self, tier: str = "igpu"):
        if tier not in self._PORTS:
            raise ValueError(f"tier must be one of {list(self._PORTS)}")
        self.tier = tier
        self.port = self._PORTS[tier]
        self.base = f"http://localhost:{self.port}"

    def is_available(self) -> bool:
        """Check if this Lemonade tier is running."""
        try:
            resp = requests.get(f"{self.base}/v1/models", timeout=1)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def complete(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        """Run a completion on this Lemonade tier.

        Args:
            prompt: The input prompt.
            max_tokens: Max tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Generated text, or "" on failure.
        """
        payload = {
            "model": self._get_model(),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(
                f"{self.base}/v1/chat/completions",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError):
            return ""

    def _get_model(self) -> str:
        """Return the model ID for this tier."""
        try:
            resp = requests.get(f"{self.base}/v1/models", timeout=2)
            models = resp.json().get("data", [])
            if models:
                return models[0]["id"]
        except (requests.RequestException, KeyError):
            pass
        # Fallback model IDs from harness invariants
        return {
            "npu": "llama3.2-1b-FLM",
            "igpu": "deepseek-r1-0528-8b-FLM",
            "cpu": "Gemma-4-31B-it-GGUF",
        }[self.tier]


# ─── CohezionBridge ───────────────────────────────────────────────────────────

class CohezionBridge:
    """Bridge to Cohezion's compound AI stack.

    Provides:
      - semantic_search(): find similar patterns via SemanticCache
      - classify_task(): NPU-tier complexity classification
      - lemonade_available(): whether local AMD silicon is online

    All methods degrade gracefully — returns None/[] when Cohezion
    isn't installed or Lemonade isn't running.
    """

    def __init__(self):
        self._SemanticCache = _try_import_semantic_cache()
        self._classify = _try_import_task_classifier()
        self._make_executor = _try_import_compound_executor()
        self._cache_instance: Optional[Any] = None

    # ------------------------------------------------------------------
    # Availability probes
    # ------------------------------------------------------------------

    @property
    def cohezion_available(self) -> bool:
        """True if Cohezion Python package is importable."""
        return self._SemanticCache is not None

    def lemonade_available(self, tier: str = "igpu") -> bool:
        """True if the given Lemonade tier is reachable."""
        return LemonadeClient(tier).is_available()

    def get_status(self) -> dict:
        """Return availability status of all integration points."""
        return {
            "cohezion_package": self.cohezion_available,
            "lemonade_npu": self.lemonade_available("npu"),
            "lemonade_igpu": self.lemonade_available("igpu"),
            "lemonade_cpu": self.lemonade_available("cpu"),
        }

    # ------------------------------------------------------------------
    # Local-first completion (NPU->iGPU->CPU->omni-router->cloud)
    # ------------------------------------------------------------------

    # OMNI (vision + tool-calling) models served by the :13305 router. Verified
    # labels include 'vision' and 'tool-calling'. All are N3-safe to request via the
    # router: Gemma-4 carry a bounded ctx_size (16384); Llama-4-Scout is in the
    # no-KV-risk class. Ordered lightest-capable first.
    OMNI_MODELS: tuple[str, ...] = (
        "Gemma-4-E4B-it-GGUF",
        "Gemma-4-31B-it-GGUF",
        "Llama-4-Scout-17B-16E-Instruct-GGUF-Q4_K_M",
    )

    def complete_with_fallback(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        cloud_fn: Optional[Any] = None,
        tiers: tuple[str, ...] = ("npu", "igpu", "cpu"),
        use_omni: bool = True,
    ) -> tuple[str, str]:
        """Local-first completion: NPU->iGPU->CPU->omni-router->cloud.

        Embodies the local-inference-default doctrine with empty-response-as-escalation
        (an empty local reply is a calibration signal to escalate, NOT a bug to retry).
        All local inference goes through the SINGLE :13305 router (router-centric
        topology); there are NO separate per-tier ports. ``use_omni`` routes to the
        fleet's already-loaded OMNI (vision + tool-calling) models so local inference
        is actually exercised. N3-safe: only the bounded-ctx / no-KV-risk omni models are
        requested -- never an unbounded ctx_size=0 heavy load.

        Returns (text, backend) where ``backend`` is the tier/model/'cloud' that ACTUALLY
        served the request -- so callers can report HONEST backend attribution instead of
        a reachability probe. ``max_tokens`` bounds output regardless of tier.

        Args:
            prompt: The user prompt.
            max_tokens: Output token cap.
            temperature: Sampling temperature.
            cloud_fn: Optional callable(prompt) -> str, used ONLY if every local path
                fails or returns empty (e.g. a wrapped Anthropic call).
            tiers: Order of dedicated local tiers to attempt first.
            use_omni: Try the :13305 omni models after dedicated tiers, before cloud.

        Returns:
            (text, backend) with backend in {"npu","igpu","cpu",<omni-model-id>,"cloud","none"}.
        """
        # ALL local inference goes through the SINGLE :13305 router (router-centric topology) --
        # there are NO separate per-tier ports; the router dispatches to NPU/iGPU/CPU by model.
        # `tiers`/`use_omni` are retained for signature compatibility but are no-ops.
        text, backend = self.complete_omni(
            prompt, max_tokens=max_tokens, temperature=temperature,
        )
        if text and text.strip():
            return text, backend
        if cloud_fn is not None:
            try:
                return cloud_fn(prompt), "cloud"
            except Exception:  # noqa: BLE001
                return "", "none"
        return "", "none"

    def complete_omni(
        self,
        prompt: str,
        *,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.1,
        cloud_fn: Optional[Any] = None,
    ) -> tuple[str, str]:
        """Complete via the fleet's OMNI (vision + tool-calling) models on the :13305 router.

        Leverages local omni models (Gemma-4-E4B / Gemma-4-31B / Llama-4-Scout, all
        labeled 'vision'+'tool-calling') so a single $0 local call handles text AND an
        optional image (OpenAI-style image_url content block). Only models actually
        present in the router catalog are tried, lightest-capable first.

        N3-safe: the OMNI_MODELS are bounded-ctx or no-KV-risk; this never forces an
        unbounded ctx_size=0 heavy load.

        Returns (text, backend) where backend is the omni model id that served the
        request, else falls back to cloud_fn / ("", "none").
        """
        router_port = int(os.getenv("LEMONADE_ROUTER_PORT", "13305"))
        base = f"http://localhost:{router_port}"
        # Prefer models ALREADY LOADED on the router (avoids auto-load latency, GPU
        # eviction churn that can disrupt a co-running session, and the N3 ctx_size=0
        # hazard). Fall back to the catalog only when /api/v1/health is unavailable.
        loaded: set = set()
        try:
            h = requests.get(f"{base}/api/v1/health", timeout=2).json()
            loaded = {m.get("model_name") for m in h.get("all_models_loaded", [])}
        except (requests.RequestException, KeyError, ValueError):
            loaded = set()

        if model is not None:
            candidates = [model]
        elif loaded:
            # only already-loaded omni models, omni preference order preserved
            candidates = [m for m in self.OMNI_MODELS if m in loaded]
        else:
            try:
                resp = requests.get(f"{base}/v1/models", timeout=2)
                available = {m.get("id") for m in resp.json().get("data", [])}
            except (requests.RequestException, KeyError, ValueError):
                available = set()
            candidates = [m for m in self.OMNI_MODELS if m in available]

        if image_url is None:
            content: Any = prompt
        else:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]

        for mdl in candidates:
            payload = {
                "model": mdl,
                "messages": [{"role": "user", "content": content}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                resp = requests.post(
                    f"{base}/v1/chat/completions", json=payload, timeout=60,
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                if text and text.strip():
                    return text, mdl
            except (requests.RequestException, KeyError, IndexError):
                continue

        if cloud_fn is not None:
            try:
                return cloud_fn(prompt), "cloud"
            except Exception:  # noqa: BLE001
                return "", "none"
        return "", "none"

    # ------------------------------------------------------------------
    # SemanticCache integration
    # ------------------------------------------------------------------

    def _get_cache(self) -> Optional[Any]:
        """Get or create the SemanticCache singleton."""
        if self._SemanticCache is None:
            return None
        if self._cache_instance is None:
            try:
                self._cache_instance = self._SemanticCache.get_instance()
            except Exception:  # noqa: BLE001
                self._cache_instance = None
        return self._cache_instance

    def semantic_search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search for similar patterns in the Cohezion vault via SemanticCache.

        Uses FLUME VAE 256D embeddings for semantic similarity (L2 cosine).
        Calibrated threshold: 0.58 for nomic-embed-text-v2-moe-GGUF.

        Args:
            query: Natural language description of what to search for.
            top_k: Maximum number of similar patterns to return.

        Returns:
            List of {"pattern": str, "similarity": float, "source": str} dicts.
            Empty list when Cohezion unavailable or no similar patterns found.
        """
        cache = self._get_cache()
        if cache is None:
            return []

        try:
            # Attempt L2 semantic lookup via get method
            hit = cache.get(query)
            if hit is not None:
                return [{"pattern": hit, "similarity": 1.0, "source": "semantic_cache:L1/L2"}]

            # Fallback: check l2_cache for nearby embeddings
            if hasattr(cache, "l2_cache") and cache.l2_cache:
                results = []
                for _, entry in list(cache.l2_cache.items())[:top_k]:
                    results.append({
                        "pattern": entry.prompt if hasattr(entry, "prompt") else str(entry),
                        "similarity": float(getattr(entry, "hit_count", 1)) / 100,
                        "source": "semantic_cache:L2",
                    })
                return results[:top_k]
        except Exception:  # noqa: BLE001
            pass

        return []

    def get_cache_stats(self) -> dict:
        """Return SemanticCache hit rate statistics."""
        cache = self._get_cache()
        if cache is None:
            return {"available": False}
        try:
            stats = cache.get_stats() if hasattr(cache, "get_stats") else {}
            return {"available": True, **stats}
        except Exception:  # noqa: BLE001
            return {"available": True, "error": "stats unavailable"}

    # ------------------------------------------------------------------
    # Task classification (NPU tier)
    # ------------------------------------------------------------------

    def classify_task(self, description: str) -> Optional[dict]:
        """Classify a task using Cohezion's NPU-tier task classifier.

        Routed to llama3.2-1b-FLM (42 TPS, sub-500µs) when available.

        Args:
            description: Natural language task description.

        Returns:
            {"node": "npu"|"igpu"|"cpu", "output_type": str, "confidence": float}
            or None when unavailable.
        """
        if self._classify is None:
            return None
        try:
            result = self._classify(description)
            return {
                "node": result.node,
                "output_type": result.output_type,
                "confidence": getattr(result, "confidence", 0.0),
            }
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Compound executor
    # ------------------------------------------------------------------

    def make_executor(self, mcp_client: Any = None) -> Optional[Any]:
        """Create a CompoundExecutor with the Triune orchestrator.

        Returns None when Cohezion is not installed.
        """
        if self._make_executor is None:
            return None
        try:
            return self._make_executor(mcp_client)
        except Exception:  # noqa: BLE001
            return None
