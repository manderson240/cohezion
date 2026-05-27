# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Code Review Swarm - Orchestrates specialized scouts for codebase analysis.
Enforces Phase-based scanning (Static First -> Selective LLM) and Safe Mode batching.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from cohezion.core.persistence.repositories.pattern_repository import (
    CodeAntiPattern,
    CodePattern,
    PatternRepository,
)
from cohezion.swarm.agents.anti_pattern_scout import AntiPatternScout
from cohezion.swarm.agents.architecture_scout import ArchitectureScout
from cohezion.swarm.agents.base_scout import BaseScout, Finding
from cohezion.swarm.agents.pattern_scout import PatternScout
from cohezion.swarm.agents.quality_scout import QualityScout


logger = logging.getLogger(__name__)


@dataclass
class SwarmReport:
    total_files: int
    scanned_files: int
    findings: list[Finding] = field(default_factory=list)
    high_complexity_files: list[str] = field(default_factory=list)


class CodeReviewSwarm:
    """
    Orchestrator for the Code Review Swarm.
    """

    def __init__(
        self,
        repository: PatternRepository,
        target_dir: str = "src/cohezion",
        batch_size: int = 5,
        complexity_threshold: int = 15,
    ) -> None:
        self.repository = repository
        self.target_dir = Path(target_dir)
        self.batch_size = batch_size
        self.complexity_threshold = complexity_threshold

        # Initialize scouts
        self.static_scout = QualityScout()
        self.llm_scouts: list[BaseScout] = [ArchitectureScout(), PatternScout(), AntiPatternScout()]

    async def run_full_scan(self) -> SwarmReport:
        """
        Executes the two-phase scan:
        1. Static scan of all files to identify 'High Interest' targets.
        2. Throttled LLM scan of high-interest files.
        """
        all_files = list(self.target_dir.rglob("*.py"))
        report = SwarmReport(total_files=len(all_files), scanned_files=0)

        logger.info(f"🚀 Starting Static Scan of {len(all_files)} files...")

        # Phase 1: Static Scan (Zero Tokens)
        for i in range(0, len(all_files), self.batch_size):
            batch = all_files[i : i + self.batch_size]
            for file_path in batch:
                findings = await self.static_scout.scan_file(file_path)
                report.findings.extend(findings)

                # Check for high complexity
                ast_sum = self.static_scout._parse_python_ast(file_path)
                if ast_sum and ast_sum.complexity_score >= self.complexity_threshold:
                    report.high_complexity_files.append(str(file_path))

                report.scanned_files += 1

            logger.info(f"Static Phase: Scanned {report.scanned_files}/{len(all_files)} files...")
            await asyncio.sleep(1.0)  # Breath between batches

        logger.info(
            f"✅ Static Phase Complete. Found {len(report.high_complexity_files)} high-complexity files."
        )

        # Phase 2: Selective LLM Scan
        if report.high_complexity_files:
            logger.info(
                f"🧠 Starting Semantic Phase on {len(report.high_complexity_files)} files..."
            )
            for file_path_str in report.high_complexity_files:
                file_path = Path(file_path_str)
                for scout in self.llm_scouts:
                    findings = await scout.scan_file(file_path)
                    report.findings.extend(findings)

                    # Persist findings immediately to repository buffer
                    for f in findings:
                        await self._persist_finding(f)

                logger.info(f"Semantic Phase: Completed {file_path_str}")

        return report

    async def _persist_finding(self, finding: Finding) -> None:
        """Helper to convert Finding to Repository format and store."""
        if finding.type == "pattern":
            pattern = CodePattern(
                name=finding.name,
                category=finding.category,
                description=finding.description,
                file_paths=[finding.file_path],
                code_example=finding.code_snippet,
                confidence=finding.confidence,
                metadata=finding.metadata,
            )
            await self.repository.store_pattern(pattern)
        else:
            anti_pattern = CodeAntiPattern(
                name=finding.name,
                category=finding.category,
                description=finding.description,
                file_paths=[finding.file_path],
                severity=finding.severity or "medium",
                risk_level=5,  # Default
                remediation=finding.remediation or "Analyze and refactor.",
                code_example=finding.code_snippet,
                confidence=finding.confidence,
                metadata=finding.metadata,
            )
            await self.repository.store_anti_pattern(anti_pattern)
