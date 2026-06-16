"""Agentic consumer: DATA_PRODUCT_QUALITY_ALERT → SkillOpt corpus augmentation.

When a DataMesh quality alert fires (e.g. a data product's execution traces fall
below the quality threshold), this consumer reacts by calling the SiriuS-style
SurrealTraceAugmentor to generate improved synthetic traces — closing the loop:

    execution traces → quality score drop
        → DATA_PRODUCT_QUALITY_ALERT published to EventBus
            → CorpusQualityConsumer handles
                → SurrealTraceAugmentor.augment_batch()
                    → improved synthetic traces written back to SurrealDB
                        → SkillOpt training corpus quality improves

Expected payload keys in DATA_PRODUCT_QUALITY_ALERT events:
    skill_filter (str, optional): canonical skill name to target
    max_score (float, optional): quality threshold; defaults to 0.5
    limit (int, optional): max traces to augment; defaults to 20
    improved_score (float, optional): score assigned to augmented traces; defaults to 0.8
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.core.event_bus import Event, EventBus, EventType


logger = logging.getLogger(__name__)


class CorpusQualityConsumer:
    """Subscribes to DATA_PRODUCT_QUALITY_ALERT and triggers trace augmentation.

    This is an AGENT in the event-driven data mesh sense: it reacts to a domain
    event and produces a new data product (augmented traces) as its output.

    Parameters
    ----------
    tts_announce:
        When True, speak a brief summary via Lemonade kokoro-v1 TTS after each
        successful augmentation batch.  Non-fatal — if TTS is unavailable the
        consumer continues normally.
    """

    SUBSCRIBED_TYPES: list[EventType] = [EventType.DATA_PRODUCT_QUALITY_ALERT]

    def __init__(self, tts_announce: bool = False) -> None:
        self._augmentor: Any | None = None
        self._tts_announce: bool = tts_announce
        self._mm_client: Any | None = None  # LemonadeMultimodalClient | None

    def _get_augmentor(self) -> Any | None:
        """Lazy-initialize augmentor — avoids connecting to SurrealDB at import time."""
        if self._augmentor is None:
            try:
                from cohezion.skillopt.trace_augmentor import make_augmentor

                self._augmentor = make_augmentor()
            except Exception as exc:
                logger.debug("CorpusQualityConsumer: augmentor unavailable: %s", exc)
        return self._augmentor

    def _get_multimodal_client(self) -> Any | None:
        """Lazy-initialize Lemonade multimodal client (TTS/STT/embed)."""
        if self._mm_client is None:
            try:
                from cohezion.data_mesh.lemonade_multimodal import make_multimodal_client

                self._mm_client = make_multimodal_client()
            except Exception as exc:
                logger.debug("CorpusQualityConsumer: multimodal client unavailable: %s", exc)
        return self._mm_client

    def subscribe(self, bus: EventBus) -> None:
        """Register this consumer as a handler on the given EventBus."""
        for event_type in self.SUBSCRIBED_TYPES:
            bus._handlers[event_type].append(self._handle)

    async def _handle(self, event: Event) -> None:
        """Dispatch incoming events to the appropriate handler."""
        if event.type == EventType.DATA_PRODUCT_QUALITY_ALERT:
            await self._handle_quality_alert(event)

    async def _handle_quality_alert(self, event: Event) -> None:
        """React to a quality alert by augmenting low-scoring execution traces.

        Reads augmentation parameters from the event payload so each alert can
        target a specific skill or quality threshold.
        """
        payload = event.payload
        skill_filter: str | None = payload.get("skill_filter")
        max_score: float = float(payload.get("max_score", 0.5))
        limit: int = int(payload.get("limit", 20))
        improved_score: float = float(payload.get("improved_score", 0.8))

        augmentor = self._get_augmentor()
        if augmentor is None:
            logger.debug(
                "CorpusQualityConsumer: SurrealDB unavailable, skipping augmentation for '%s'",
                skill_filter or "all skills",
            )
            return

        logger.info(
            "CorpusQualityConsumer: augmenting corpus for skill=%r max_score=%.2f limit=%d",
            skill_filter,
            max_score,
            limit,
        )
        try:
            results = augmentor.augment_batch(
                max_score=max_score,
                limit=limit,
                skill_filter=skill_filter,
                improved_score=improved_score,
            )
            logger.info(
                "CorpusQualityConsumer: produced %d augmented traces for skill=%r",
                len(results),
                skill_filter,
            )
        except Exception as exc:
            logger.warning("CorpusQualityConsumer: augment_batch failed: %s", exc)
            return

        if self._tts_announce and results:
            try:
                client = self._get_multimodal_client()
                if client is not None:
                    message = (
                        f"Corpus augmented: {len(results)} traces improved"
                        f" for {skill_filter or 'all skills'}"
                    )
                    client.speak(message)
            except Exception as exc:
                logger.debug("CorpusQualityConsumer: TTS announce failed: %s", exc)


def make_corpus_quality_consumer() -> CorpusQualityConsumer:
    """Factory for CorpusQualityConsumer (always succeeds — connection is lazy)."""
    return CorpusQualityConsumer()
