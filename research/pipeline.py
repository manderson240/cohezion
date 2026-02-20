"""Core pipeline orchestrator for research discovery workflow."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    """A single research finding from any source."""

    title: str
    url: str
    source: str  # Source type: web_search, github_recent, hackernews, etc.
    snippet: str
    category: str  # Focus area: compound_engineering, token_efficiency, etc.
    raw_score: float = 0.0


@dataclass
class ResearchReport:
    """Complete report from a research pipeline run."""

    findings: List[Finding]
    scores: Dict[str, Any]  # Scoring metadata
    metadata: Dict[str, Any]  # Run metadata (sources scanned, timing, etc.)
    timestamp: datetime


class Pipeline:
    """
    Main research pipeline orchestrator.

    Coordinates three stages:
    1. Harvest - Parallel searches across multiple sources
    2. Score - Hybrid keyword + LLM relevance scoring
    3. Publish - Generate vault notes (inbox + digest)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize pipeline with configuration.

        Args:
            config: Configuration dict with source definitions, scoring params, etc.
        """
        self.config = config
        logger.info("Pipeline initialized with config: %s", config)

    async def harvest(self, config: Dict[str, Any]) -> List[Finding]:
        """
        Harvest stage - gather findings from all sources in parallel.

        Args:
            config: Configuration for sources

        Returns:
            List of Finding objects from all sources
        """
        logger.info("Starting harvest stage")
        # Placeholder - will be implemented in Task 2
        return []

    async def score(
        self, findings: List[Finding], config: Dict[str, Any]
    ) -> tuple[List[Finding], Dict[str, Any]]:
        """
        Score stage - evaluate relevance of findings.

        Args:
            findings: Raw findings from harvest
            config: Scoring configuration

        Returns:
            Tuple of (scored findings, scoring metadata)
        """
        logger.info("Starting score stage with %d findings", len(findings))
        # Placeholder - will be implemented in Task 3
        return findings, {}

    async def publish(
        self,
        findings: List[Finding],
        scores: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Publish stage - generate vault notes.

        Args:
            findings: Scored findings
            scores: Scoring metadata
            config: Publishing configuration

        Returns:
            Publishing metadata (files created, counts, etc.)
        """
        logger.info("Starting publish stage with %d findings", len(findings))
        # Placeholder - will be implemented in Task 4
        return {"published": len(findings)}

    async def run(self) -> ResearchReport:
        """
        Execute complete pipeline: harvest → score → publish.

        Handles partial failures - if one source fails, others continue.

        Returns:
            ResearchReport with all findings and metadata
        """
        logger.info("Starting pipeline run")
        start_time = datetime.now()

        try:
            # Stage 1: Harvest findings from all sources
            findings = await self.harvest(self.config)
            logger.info("Harvest complete: %d findings", len(findings))

            # Stage 2: Score findings for relevance
            scored_findings, scores = await self.score(findings, self.config)
            logger.info("Score complete: %d scored findings", len(scored_findings))

            # Stage 3: Publish to vault
            publish_metadata = await self.publish(scored_findings, scores, self.config)
            logger.info("Publish complete: %s", publish_metadata)

            # Build final report
            report = ResearchReport(
                findings=scored_findings,
                scores=scores,
                metadata=publish_metadata,
                timestamp=start_time,
            )

            logger.info("Pipeline run complete")
            return report

        except Exception as e:
            logger.error("Pipeline run failed: %s", e, exc_info=True)
            # Return empty report on total failure
            return ResearchReport(
                findings=[],
                scores={},
                metadata={"error": str(e)},
                timestamp=start_time,
            )
