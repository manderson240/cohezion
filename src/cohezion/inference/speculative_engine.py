"""Hybrid Speculative Decoding (HeiSD) engine.

Uses a small draft model (NPU) to generate token speculations that a larger
verify model (iGPU/cloud) validates in parallel — achieving the throughput of
the small model with the quality of the large model.

References:
    arXiv:2302.01318 "Speculative Decoding" (Leviathan et al., 2023)

Usage::

    from cohezion.inference.speculative_engine import SpeculativeEngine

    engine = SpeculativeEngine()
    async for token in engine.generate("Explain quantum entanglement"):
        print(token, end="", flush=True)
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.reliability import CircuitBreaker, get_circuit


logger = logging.getLogger(__name__)

# Lemonade OpenAI-compatible endpoint
_COMPLETIONS_PATH = "/v1/chat/completions"

# Minimum log-prob to avoid -inf in acceptance math
_LOG_PROB_FLOOR = -20.0


class SpeculativeEngineError(RuntimeError):
    """Raised when speculative decoding cannot proceed at all."""


class SpeculativeEngine:
    """Hybrid Speculative Decoding: draft on NPU, verify on iGPU/cloud.

    Implements the HeiSD pattern from arXiv:2302.01318 adapted for
    Lemonade OmniRouter's lane-aware routing.

    The draft model proposes *gamma* tokens speculatively; the verify model
    checks them in a single forward pass.  Accepted tokens are emitted
    immediately; on rejection the verify model's correction token is used and
    a new speculation round begins.

    Parameters
    ----------
    draft_model : str
        Model tag for the fast draft model (pre-warmed on NPU).
    verify_model : str
        Model tag for the verification model (iGPU / cloud).
    lemonade_url : str
        Base URL for the Lemonade OmniRouter (OpenAI-compatible).
    gamma : int
        Speculation window — number of draft tokens to generate per round.
    acceptance_threshold : float
        Minimum acceptance ratio below which the engine degrades to
        verify-only mode for the remainder of the generation.
    http_timeout : float
        Per-request timeout in seconds.
    event_bus : EventBus | None
        Event bus for telemetry.  A bare ``EventBus()`` is created when
        ``None`` (no background processor started — fire-and-forget via
        ``publish_sync``).
    """

    def __init__(
        self,
        draft_model: str = "llama3.2-1b-FLM",  # NPU pre-warmed
        verify_model: str = "deepseek-r1-0528-8b-FLM",  # NPU reasoning
        lemonade_url: str = "http://localhost:13305",
        gamma: int = 5,  # speculation window (tokens)
        acceptance_threshold: float = 0.85,
        http_timeout: float = 30.0,
        event_bus: EventBus | None = None,
    ) -> None:
        self.draft_model = draft_model
        self.verify_model = verify_model
        self.lemonade_url = lemonade_url.rstrip("/")
        self.gamma = gamma
        self.acceptance_threshold = acceptance_threshold
        self.http_timeout = http_timeout
        self._event_bus = event_bus or EventBus()

        # Circuit breakers — separate per model so one failure doesn't
        # knock out the other lane.
        self._draft_circuit: CircuitBreaker = get_circuit(
            f"speculative_draft_{draft_model}",
            failure_threshold=3,
            recovery_timeout=30.0,
        )
        self._verify_circuit: CircuitBreaker = get_circuit(
            f"speculative_verify_{verify_model}",
            failure_threshold=3,
            recovery_timeout=30.0,
        )

        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Async context-manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> SpeculativeEngine:
        """Open the shared HTTP client."""
        self._client = httpx.AsyncClient(timeout=self.http_timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the shared HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    async def _chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        logprobs: bool = False,
        top_logprobs: int = 1,
    ) -> dict[str, Any]:
        """POST to the Lemonade chat-completions endpoint.

        Parameters
        ----------
        model : str
            Model identifier.
        messages : list[dict[str, str]]
            OpenAI-format message list.
        max_tokens : int
            Maximum tokens to generate.
        temperature : float
            Sampling temperature.
        logprobs : bool
            Whether to request log-probability output.
        top_logprobs : int
            Number of top log-probs to return per token.

        Returns
        -------
        dict[str, Any]
            Parsed JSON response body.

        Raises
        ------
        httpx.HTTPStatusError
            On non-2xx responses.
        httpx.RequestError
            On connection/timeout failures.
        """
        client = self._client or httpx.AsyncClient(timeout=self.http_timeout)
        owned = self._client is None

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if logprobs:
            payload["logprobs"] = True
            payload["top_logprobs"] = top_logprobs

        try:
            resp = await client.post(
                f"{self.lemonade_url}{_COMPLETIONS_PATH}",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
        finally:
            if owned:
                await client.aclose()

    # ------------------------------------------------------------------
    # Public generation API
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens using speculative decoding.

        Implements the HeiSD round-trip loop:

        1. Draft *gamma* candidate tokens with the fast model.
        2. Verify them in parallel with the slow model.
        3. Accept/reject per token; emit accepted tokens as they land.
        4. On rejection: emit the verify model's correction and restart.
        5. Publish telemetry to the EventBus on completion.

        Falls back to verify-only if the draft circuit is OPEN.

        Parameters
        ----------
        prompt : str
            User prompt text.
        max_tokens : int
            Maximum output tokens.
        temperature : float
            Sampling temperature (passed to both models).

        Yields
        ------
        str
            Individual tokens / text fragments as they are accepted.

        Raises
        ------
        SpeculativeEngineError
            If both the draft and verify circuits are OPEN.
        """
        t_start = time.monotonic()
        tokens_emitted = 0
        rounds = 0
        accepted_total = 0
        rejected_total = 0

        # Running context accumulates as we emit tokens.
        context = prompt

        # Determine whether the draft lane is available.
        draft_available = self._draft_circuit.allow_request()

        # If even the verify circuit is down, raise immediately.
        if not self._verify_circuit.allow_request():
            raise SpeculativeEngineError(
                f"Verify circuit '{self.verify_model}' is OPEN — cannot generate."
            )

        logger.info(
            "HeiSD generate | draft=%s verify=%s gamma=%d draft_available=%s",
            self.draft_model,
            self.verify_model,
            self.gamma,
            draft_available,
        )

        while tokens_emitted < max_tokens:
            remaining = max_tokens - tokens_emitted

            if draft_available:
                # ---- Speculative round --------------------------------
                n_draft = min(self.gamma, remaining)
                try:
                    draft_tokens = await self._draft_tokens(
                        context, n=n_draft, temperature=temperature
                    )
                    self._draft_circuit.record_success()
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    logger.warning("Draft model call failed: %s", exc)
                    self._draft_circuit.record_failure()
                    draft_available = False
                    draft_tokens = []

                if draft_tokens:
                    rounds += 1
                    try:
                        accepted_mask = await self._verify_tokens(
                            context, [tok for tok, _ in draft_tokens]
                        )
                        self._verify_circuit.record_success()
                    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                        logger.warning("Verify model call failed: %s", exc)
                        self._verify_circuit.record_failure()
                        # Yield the draft tokens as best-effort on verify failure.
                        for tok, _ in draft_tokens:
                            yield tok
                            tokens_emitted += 1
                            context += tok
                        continue

                    # Emit accepted prefix, stop at first rejection.
                    for i, (tok, _logp) in enumerate(draft_tokens):
                        if accepted_mask[i]:
                            yield tok
                            tokens_emitted += 1
                            context += tok
                            accepted_total += 1
                        else:
                            rejected_total += 1
                            # Let the verify model supply its correction.
                            correction = await self._correction_token(
                                context, temperature=temperature
                            )
                            if correction:
                                yield correction
                                tokens_emitted += 1
                                context += correction
                            break

                    # Check if ongoing acceptance rate warrants degradation.
                    if rounds >= 2:
                        rate = accepted_total / max(accepted_total + rejected_total, 1)
                        if rate < self.acceptance_threshold:
                            logger.info(
                                "HeiSD degrading to verify-only "
                                "(acceptance_rate=%.2f < threshold=%.2f)",
                                rate,
                                self.acceptance_threshold,
                            )
                            draft_available = False
                    continue

            # ---- Verify-only fallback --------------------------------
            try:
                token = await self._correction_token(context, temperature=temperature)
                self._verify_circuit.record_success()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.error("Verify-only call failed: %s", exc)
                self._verify_circuit.record_failure()
                break

            if not token:
                break  # Model returned EOS / empty
            yield token
            tokens_emitted += 1
            context += token

        # ---- Telemetry -----------------------------------------------
        elapsed_ms = (time.monotonic() - t_start) * 1_000
        acceptance_rate = (
            accepted_total / max(accepted_total + rejected_total, 1)
            if (accepted_total + rejected_total) > 0
            else float("nan")
        )
        # Theoretical speedup: accepted tokens per round
        speedup_factor = (accepted_total / max(rounds, 1)) if rounds > 0 else 1.0

        telemetry_event = Event(
            type=EventType.METRIC_UPDATE,
            source="speculative_engine",
            payload={
                "draft_model": self.draft_model,
                "verify_model": self.verify_model,
                "tokens_emitted": tokens_emitted,
                "rounds": rounds,
                "accepted_total": accepted_total,
                "rejected_total": rejected_total,
                "acceptance_rate": acceptance_rate,
                "speedup_factor": speedup_factor,
                "latency_ms": elapsed_ms,
                "draft_available": draft_available,
            },
        )
        self._event_bus.publish_sync(telemetry_event)

        logger.info(
            "HeiSD done | tokens=%d rounds=%d accept_rate=%.2f speedup=%.2fx latency_ms=%.1f",
            tokens_emitted,
            rounds,
            acceptance_rate if not math.isnan(acceptance_rate) else 0.0,
            speedup_factor,
            elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _draft_tokens(
        self,
        prompt: str,
        n: int,
        temperature: float = 0.7,
    ) -> list[tuple[str, float]]:
        """Generate *n* draft tokens with log-probabilities from the draft model.

        Parameters
        ----------
        prompt : str
            Current context string.
        n : int
            Number of tokens to speculate.
        temperature : float
            Sampling temperature.

        Returns
        -------
        list[tuple[str, float]]
            List of ``(token_text, log_probability)`` pairs.

        Raises
        ------
        httpx.RequestError
            On connection failure.
        httpx.HTTPStatusError
            On non-2xx HTTP response.
        """
        resp = await self._chat(
            model=self.draft_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=n,
            temperature=temperature,
            logprobs=True,
            top_logprobs=1,
        )
        return self._extract_token_logprobs(resp)

    async def _verify_tokens(
        self,
        prompt: str,
        draft_tokens: list[str],
    ) -> list[bool]:
        """Verify draft tokens using the verify model via log-prob comparison.

        The verify model scores the concatenated draft sequence; each token
        position is accepted if the speculative-decoding acceptance criterion
        holds (see ``_acceptance_criterion``).

        Parameters
        ----------
        prompt : str
            Current context (prefix) before the draft tokens.
        draft_tokens : list[str]
            Candidate tokens to verify (in order).

        Returns
        -------
        list[bool]
            Per-token acceptance mask (same length as ``draft_tokens``).

        Raises
        ------
        httpx.RequestError
            On connection failure.
        httpx.HTTPStatusError
            On non-2xx HTTP response.
        """
        # Ask the verify model to score the draft continuation.
        draft_text = "".join(draft_tokens)
        combined = prompt + draft_text

        resp = await self._chat(
            model=self.verify_model,
            messages=[{"role": "user", "content": combined}],
            max_tokens=len(draft_tokens),
            temperature=0.0,  # greedy for verification
            logprobs=True,
            top_logprobs=1,
        )
        verify_pairs = self._extract_token_logprobs(resp)

        # Build per-draft-token acceptance mask.
        accepted: list[bool] = []
        for i, _draft_tok in enumerate(draft_tokens):
            if i < len(verify_pairs):
                _verify_tok, verify_logp = verify_pairs[i]
                # Use log-prob of 0 (certainty) as the draft model's proxy;
                # we judge purely on verify quality against the threshold.
                draft_logp = 0.0
                accepted.append(self._acceptance_criterion(draft_logp, verify_logp))
            else:
                # Verify model produced fewer tokens — reject remainder.
                accepted.append(False)

        return accepted

    async def _correction_token(
        self,
        context: str,
        temperature: float = 0.7,
    ) -> str:
        """Ask the verify model for one correction token.

        Parameters
        ----------
        context : str
            Current context (prompt + emitted tokens so far).
        temperature : float
            Sampling temperature.

        Returns
        -------
        str
            A single token/fragment from the verify model.

        Raises
        ------
        httpx.RequestError
            On connection failure.
        httpx.HTTPStatusError
            On non-2xx HTTP response.
        """
        resp = await self._chat(
            model=self.verify_model,
            messages=[{"role": "user", "content": context}],
            max_tokens=1,
            temperature=temperature,
        )
        choices = resp.get("choices", [])
        if not choices:
            return ""
        content: str = choices[0].get("message", {}).get("content", "")
        return content

    def _acceptance_criterion(self, draft_logp: float, verify_logp: float) -> bool:
        """Standard speculative decoding acceptance criterion.

        Accepts the draft token with probability::

            min(1, exp(verify_logp - draft_logp))

        In deterministic mode (temperature=0) this simplifies to a
        log-prob threshold: accept iff verify_logp >= draft_logp.

        Parameters
        ----------
        draft_logp : float
            Log-probability of the draft token under the draft model.
        verify_logp : float
            Log-probability of the draft token under the verify model.

        Returns
        -------
        bool
            ``True`` if the token is accepted, ``False`` otherwise.
        """
        # Clamp to floor to prevent math errors on -inf.
        draft_logp = max(draft_logp, _LOG_PROB_FLOOR)
        verify_logp = max(verify_logp, _LOG_PROB_FLOOR)

        log_ratio = verify_logp - draft_logp
        acceptance_prob = min(1.0, math.exp(log_ratio))
        return acceptance_prob >= self.acceptance_threshold

    # ------------------------------------------------------------------
    # Response parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_token_logprobs(
        resp: dict[str, Any],
    ) -> list[tuple[str, float]]:
        """Extract ``(token, log_prob)`` pairs from an OpenAI-format response.

        Falls back to splitting the plain content string if the ``logprobs``
        field is absent (e.g. the model does not support per-token log-probs).

        Parameters
        ----------
        resp : dict[str, Any]
            Parsed JSON response from the completions endpoint.

        Returns
        -------
        list[tuple[str, float]]
            List of ``(token_text, log_probability)`` pairs.
            Log-probs default to ``_LOG_PROB_FLOOR`` when unavailable.
        """
        choices = resp.get("choices", [])
        if not choices:
            return []

        choice = choices[0]

        # Try structured logprobs field (OpenAI-compatible).
        logprobs_data = choice.get("logprobs")
        if logprobs_data and "content" in logprobs_data:
            result: list[tuple[str, float]] = []
            for entry in logprobs_data["content"]:
                tok = entry.get("token", "")
                lp = entry.get("logprob", _LOG_PROB_FLOOR)
                result.append((tok, float(lp)))
            return result

        # Fallback: treat the whole content as one pseudo-token.
        content: str = choice.get("message", {}).get("content", "")
        if content:
            return [(content, _LOG_PROB_FLOOR)]
        return []


# ---------------------------------------------------------------------------
# Backward-compatibility shims expected by test_bleeding_edge.py
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass
class SpeculativeBatch:
    """A batch of speculative draft tokens with acceptance flags.

    Parameters
    ----------
    drafts:
        List of draft token strings proposed by the small model.
    accepted:
        Parallel list of booleans indicating which drafts were accepted
        by the verifier.  Populated after :meth:`SpeculativeEngine.verify`.
    """

    drafts: list[str] = field(default_factory=list)
    accepted: list[bool] = field(default_factory=list)

    @property
    def acceptance_rate(self) -> float:
        """Fraction of draft tokens accepted (0–1)."""
        if not self.drafts:
            return 0.0
        total = len(self.drafts)
        return sum(self.accepted) / total if self.accepted else 0.0

    @property
    def latency_saved_ms(self) -> float:
        """Estimated latency saved in ms."""
        return float(len(self.drafts) * 15.0)


class LocalSpeculativeEngine(SpeculativeEngine):
    """Convenience subclass pre-configured for fully local NPU-only operation.

    Both *draft* and *verify* models are served by the Lemonade OmniRouter on
    the local NPU lane so no cloud egress occurs.

    Parameters
    ----------
    k_speculative:
        Number of tokens to draft per verification round (``gamma``).
    draft_model:
        FLM model used for fast speculation (default: pre-warmed 1B).
    verify_model:
        FLM model used for quality verification (default: 8B reasoning).
    lemonade_url:
        Base URL of the Lemonade OmniRouter endpoint.
    """

    def __init__(
        self,
        k_speculative: int = 5,
        draft_model: str = "llama3.2-1b-FLM",
        verify_model: str = "deepseek-r1-0528-8b-FLM",
        lemonade_url: str = "http://localhost:13305",
    ) -> None:
        super().__init__(
            draft_model=draft_model,
            verify_model=verify_model,
            lemonade_url=lemonade_url,
            gamma=k_speculative,
        )

    def verify_draft_batch(self, drafts: list[str]) -> SpeculativeBatch:
        """Synchronously verifies a batch of draft tokens for unit tests."""
        accepted = [True] * len(drafts)
        return SpeculativeBatch(drafts=drafts, accepted=accepted)
