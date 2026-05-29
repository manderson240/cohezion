"""Gemini CLI as a TieredOrchestrator tier.

Gemini CLI brings Google's web grounding, search, and reasoning to the
Cohezion tapestry. Best for tasks requiring current information, web search,
or Google Workspace integration.

Persistence + experiential learning:
    Every tier result is stored in SurrealDB via AutoDQA, creating a
    bi-temporal history of which tier performs best for each task type.
    The experiential learning hook fires after each cascade, feeding
    Feynman weight calibration for future routing decisions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC

from cohezion.inference.orchestrator import OrchestrationResult


logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 60.0


@dataclass
class GeminiCliTier:
    """Wraps Gemini CLI (`gemini -p`) as a TieredOrchestrator tier.

    Best for: web search, document analysis, Google services grounding.

    Persistence: results auto-persisted to SurrealDB via AutoDQA when
    persist=True. Builds experiential routing history over time.
    """

    label: str = "gemini-cli"
    model: str = "gemini-2.5-flash"
    timeout_s: float = _DEFAULT_TIMEOUT_S
    persist: bool = True  # persist result to SurrealDB via AutoDQA

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        start = time.perf_counter()
        text = ""
        error: str | None = None

        cmd = ["gemini", "-p", prompt, "-m", self.model]

        try:
            loop = asyncio.get_running_loop()

            def _invoke() -> tuple[str, str]:
                import subprocess

                try:
                    proc = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=self.timeout_s
                    )
                    if proc.returncode != 0:
                        return "", f"exit {proc.returncode}: {proc.stderr[:300]}"
                    return proc.stdout.strip(), ""
                except subprocess.TimeoutExpired:
                    return "", f"Timeout after {self.timeout_s:.0f}s"
                except FileNotFoundError:
                    return (
                        "",
                        "gemini CLI not found — install via npm: npm install -g @google/generative-ai-cli",
                    )

            text, err = await loop.run_in_executor(None, _invoke)
            if err:
                error = err
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("GeminiCliTier error: %s", error)

        latency_ms = (time.perf_counter() - start) * 1000

        result = OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,  # Gemini CLI uses free quota tier by default
            latency_ms=latency_ms,
            ttft_ms=None,
            error=error,
        )

        # Persist result for experiential learning
        if self.persist and text:
            _persist_tier_experience(self.label, prompt[:200], text[:200], latency_ms)

        return result


@dataclass
class GeminiADKTier:
    """Google Agent Developer Kit as a TieredOrchestrator tier.

    Uses google-adk for structured reasoning with function calling.
    Experiential: all results stored in SurrealDB for routing calibration.
    """

    label: str = "gemini-adk"
    model_name: str = "gemini-2.5-flash-lite"
    persist: bool = True

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        start = time.perf_counter()
        text = ""
        error: str | None = None

        try:
            from google.adk.agents import Agent
            from google.adk.models.lite_llm import LiteLlm

            loop = asyncio.get_running_loop()

            def _invoke() -> str:
                agent = Agent(model=LiteLlm(model=self.model_name), name=self.label)
                from google.adk.runners import Runner
                from google.adk.sessions import InMemorySessionService

                runner = Runner(
                    agent=agent,
                    session_service=InMemorySessionService(),
                    app_name=self.label,
                )
                import uuid

                session_id = str(uuid.uuid4())[:8]
                from google.genai import types

                response = runner.run(
                    user_id="cohezion",
                    session_id=session_id,
                    new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
                )
                parts = []
                for event in response:
                    if hasattr(event, "content") and event.content:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                parts.append(part.text)
                return "\n".join(parts)

            text = await loop.run_in_executor(None, _invoke)
        except ImportError:
            error = "google-adk not installed: uv pip install google-adk"
            logger.warning("GeminiADKTier: %s", error)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("GeminiADKTier error: %s", error)

        latency_ms = (time.perf_counter() - start) * 1000
        result = OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,
            latency_ms=latency_ms,
            ttft_ms=None,
            error=error,
        )

        if self.persist and text:
            _persist_tier_experience(self.label, prompt[:200], text[:200], latency_ms)

        return result


def _persist_tier_experience(tier: str, prompt: str, output: str, latency_ms: float) -> None:
    """Store tier result in SurrealDB for experiential routing calibration.

    This builds the BI-TEMPORAL history used to calibrate Feynman weights:
    - Which tier produced the best output for this task type?
    - Over time, the routing skill (LOCAL_INFERENCE_ROUTING.md) can be
      refined by SkillRefiner using this SurrealDB history.
    """
    try:
        from datetime import datetime

        from cohezion.core.persistence.surreal_client import SurrealClient
        from cohezion.inference.security_spec import sanitize_for_surreal

        client = SurrealClient()
        client.create(
            "tier_experience",
            {
                "tier": tier,
                "prompt_snippet": sanitize_for_surreal(prompt, max_len=200),
                "output_snippet": sanitize_for_surreal(output, max_len=200),
                "latency_ms": latency_ms,
                "valid_from": datetime.now(UTC).isoformat(),
                "valid_to": None,
            },
        )
    except Exception as exc:
        logger.debug("tier_experience persist failed (non-blocking): %s", exc)
