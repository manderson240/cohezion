"""Pre-warm Local Model Harness for Lemonade iGPU Swarms.

Pre-warms a target model on the Lemonade OmniRouter (:13305) with a real chat-completion
probe before it is trusted for serving, to prevent LRU eviction / cold-load stalls during
long inference runs.

Wiring-gap fix (2026-08-13): ``prewarm_model()`` used to ``time.sleep(0.1)`` and
unconditionally report success — it never touched the router, so a model that fails to
load (advertised in the catalog but its backend won't start; see the overnight
autoresearch loop, branch autoresearch/local-inference-20260813, Run 1) would still be
reported "pre-warmed successfully". It now makes one real, untimed chat-completion call
and only reports success when the router actually answers. Run 8 vs Run 9 of that loop
showed this exact probe eliminates run-start timeout clusters entirely (queueing behind
a model load/swap) — first zero-timeout run of the night once warm-up was added.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
import uuid
from collections.abc import Coroutine
from typing import Any

from cohezion.core.event_bus import EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.gaia_adapter import build_gaia_llm_tier
from cohezion.inference.lemonade_health import is_lemonade_alive


logger = logging.getLogger(__name__)

_PREWARM_PROMPT = "Reply with the single word: ready"


def _run_blocking(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run a coroutine from sync code, safe in BOTH calling contexts.

    ``asyncio.run()`` raises RuntimeError when a loop is already running (e.g. a
    sync prewarm call from an async startup hook) — cloud-review finding,
    2026-08-14. In that case run the coroutine on a fresh loop in a worker thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class PrewarmLocalModelHarness:
    """Harness for pre-warming and verifying local silicon inference models."""

    def __init__(
        self,
        target_model: str = "Qwen3-Coder-30B",
        lemonade_port: int = 13305,
    ) -> None:
        self.target_model = target_model
        self.lemonade_port = lemonade_port
        self._bus = EventBus()

    def prewarm_model(self) -> bool:
        """Send a real chat-completion probe to the target model; True only on a genuine response."""
        t0 = time.monotonic()
        logger.info(
            "Pre-warming local model %s on port %d...", self.target_model, self.lemonade_port
        )

        if not _run_blocking(is_lemonade_alive(port=self.lemonade_port)):
            logger.warning(
                "Pre-warm SKIPPED: OmniRouter :%d unreachable — %s not pre-warmed",
                self.lemonade_port,
                self.target_model,
            )
            return False

        tier = build_gaia_llm_tier(
            model_id=self.target_model,
            base_url=f"http://localhost:{self.lemonade_port}/api/v1",
            max_tokens=16,
            silent=True,
        )
        result = _run_blocking(tier.run(_PREWARM_PROMPT))
        duration_ms = (time.monotonic() - t0) * 1000.0

        if result.error or not result.text.strip():
            logger.warning(
                "Pre-warm FAILED for %s after %.2f ms: %s",
                self.target_model,
                duration_ms,
                result.error or "empty response",
            )
            persist_item(
                {
                    "id": f"prewarm_{self.target_model}_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                    "title": f"[Fleet Prewarm] {self.target_model} FAILED to pre-warm on port {self.lemonade_port}",
                    "status": "failed",
                    "priority": "high",
                    "source": "prewarm_harness",
                    "category": "inference_optimization",
                    "notes": f"{result.error or 'empty response'} after {duration_ms:.2f} ms",
                }
            )
            return False

        logger.info(
            "Local model %s pre-warmed successfully in %.2f ms", self.target_model, duration_ms
        )
        persist_item(
            {
                "id": f"prewarm_{self.target_model}_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                "title": f"[Fleet Prewarm] {self.target_model} pre-warmed on port {self.lemonade_port}",
                "status": "completed",
                "priority": "medium",
                "source": "prewarm_harness",
                "category": "inference_optimization",
                "notes": f"Pre-warmed in {duration_ms:.2f} ms | Prevents LRU eviction",
            }
        )

        return True
