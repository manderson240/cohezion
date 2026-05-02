"""Entire.io checkpoint commit parsing and metadata extraction."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CommitData:
    """Structured data extracted from entire.io checkpoint commit."""

    commit_hash: str
    timestamp: datetime
    agent_id: str
    outcomes: list[str]
    metrics: dict[str, float]
    team_status: str
    next_actions: list[str]


class ParsingError(Exception):
    """Raised when commit metadata cannot be parsed."""

    pass


class EntireOps:
    """Extract and transform entire.io checkpoint metadata from git commits."""

    def __init__(self, vault_path: str):
        """Initialize EntireOps with vault path."""
        self.vault_path = Path(vault_path)

    def parse_commit_metadata(
        self,
        commit_hash: str,
        commit_author: str,
        commit_date: str,
        commit_body: str,
    ) -> CommitData:
        """Extract structured data from entire.io checkpoint commit.

        Args:
            commit_hash: Full commit hash
            commit_author: Git author name/email
            commit_date: ISO format commit date
            commit_body: Full commit message body

        Returns:
            CommitData with parsed metadata

        Raises:
            ParsingError: If required fields cannot be parsed
        """
        try:
            # 1. Parse timestamp
            timestamp = self._parse_timestamp(commit_date)

            # 2. Extract agent_id from author
            agent_id = self._extract_agent_id(commit_author)

            # 3. Parse commit body sections
            outcomes = self._extract_outcomes(commit_body)
            metrics = self._extract_metrics(commit_body)
            team_status = self._extract_team_status(commit_body)
            next_actions = self._extract_next_actions(commit_body)

            return CommitData(
                commit_hash=commit_hash,
                timestamp=timestamp,
                agent_id=agent_id,
                outcomes=outcomes,
                metrics=metrics,
                team_status=team_status,
                next_actions=next_actions,
            )
        except (ValueError, KeyError, AttributeError) as e:
            raise ParsingError(f"Failed to parse commit {commit_hash}: {e}") from e

    def _parse_timestamp(self, commit_date: str) -> datetime:
        """Parse ISO format git commit date."""
        # Git CommitDate is typically ISO 8601 format
        # Example: "2026-02-11T16:30:00+00:00"
        try:
            # Try ISO format first
            return datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
        except ValueError:
            # Try alternate format
            try:
                return datetime.fromisoformat(commit_date)
            except ValueError as e:
                raise ValueError(f"Cannot parse date: {commit_date}") from e

    def _extract_agent_id(self, commit_author: str) -> str:
        """Extract agent ID from git author field.

        Examples:
            "data-graph-specialist <data@example.com>" -> "data-graph-specialist"
            "Claude Code Agent <code@example.com>" -> fallback to "claude-code"
        """
        # Try to extract from name part (before angle bracket)
        match = re.match(r"^([^<]+)", commit_author)
        if match:
            name = match.group(1).strip()
            # Convert to lowercase and handle special cases
            name = name.lower().replace(" ", "-")
            return name if name else "unknown"
        return "unknown"

    def _extract_outcomes(self, commit_body: str) -> list[str]:
        """Extract outcome bullets from 'Session Summary' or 'Outcomes' section.

        Looks for sections like:
            Session Summary (2026-02-10):
            ✅ Completed semantic linking via Claude Sonnet (78%→90% coverage)
            ✅ SurrealDB sync: 33 new links imported

        Returns:
            List of outcome strings (emoji removed, whitespace trimmed)
        """
        outcomes = []

        # Look for "Session Summary" or "Outcomes" section - more flexible match
        summary_match = re.search(
            r"(?:Session Summary|Outcomes|Accomplishments)[^:\n]*:?\s*\n((?:(?!^[A-Z][^:\n]*:|^##).+(?:\n|$))*)",
            commit_body,
            re.IGNORECASE | re.MULTILINE,
        )

        if summary_match:
            section = summary_match.group(1)
            # Extract bullet points
            lines = section.split("\n")
            for line in lines:
                line = line.strip()
                if line and len(line) > 2:  # Skip very short lines
                    # Remove common bullet markers and emoji at start
                    # Use simple approach: split on first non-marker character
                    cleaned = line.lstrip("- *•✅❌⚠️ ")  # noqa: B005
                    if cleaned and cleaned not in ["###", "##"]:
                        outcomes.append(cleaned)

        return outcomes

    def _extract_metrics(self, commit_body: str) -> dict[str, float]:
        """Extract numeric metrics from 'Metrics:' section.

        Looks for patterns like:
            Vault Metrics:
            - Papers: 87% (73/84)
            - Decisions: 88% (15/17)

        Returns:
            Dict with normalized keys and float values
        """
        metrics = {}

        # Look for "Metrics" or "Vault Metrics" section
        # Match everything until we hit a line that starts with capital letter followed by colon (new section)
        # Handle both lines with and without trailing newline
        metrics_match = re.search(
            r"(?:Vault\s+)?Metrics[^:\n]*:?\s*\n((?:(?!^[A-Z][^:\n]*:|^##).+(?:\n|$))*)",
            commit_body,
            re.IGNORECASE | re.MULTILINE,
        )

        if metrics_match:
            section = metrics_match.group(1)
            # Look for lines like "- Papers: 87% (73/84)"
            pattern = r"-\s*([^:]+):\s*(\d+(?:\.\d+)?)\s*%\s*\((\d+)/(\d+)\)"
            matches = re.findall(pattern, section)

            for name, percent, current, total in matches:
                base_key = name.strip().lower().replace(" ", "_").replace("-", "_")
                percent_val = float(percent) / 100.0
                current_val = float(current)
                total_val = float(total)

                metrics[f"{base_key}_coverage"] = percent_val
                metrics[f"{base_key}_current"] = current_val
                metrics[f"{base_key}_total"] = total_val

        return metrics

    def _extract_team_status(self, commit_body: str) -> str:
        """Extract team/overall status from commit body.

        Looks for lines like:
            Team: Ready for Phase 2
            Status: All systems operational
        """
        # Look for "Team:" or "Status:" line
        match = re.search(r"(?:Team|Status)[:\s]+([^\n]+)", commit_body, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "No status recorded"

    def _extract_next_actions(self, commit_body: str) -> list[str]:
        """Extract next action items from commit body.

        Looks for:
            Next Actions:
            - Action 1
            - Action 2
        """
        actions = []

        # Look for "Next" or "Next Actions" section - more flexible match
        next_match = re.search(
            r"(?:Next Actions?|Next Steps)[^:\n]*:?\s*\n((?:(?!^[A-Z][^:\n]*:|^##).+(?:\n|$))*)",
            commit_body,
            re.IGNORECASE | re.MULTILINE,
        )

        if next_match:
            section = next_match.group(1)
            lines = section.split("\n")
            for line in lines:
                line = line.strip()
                if line and len(line) > 2:
                    # Remove leading bullet markers (-, *, •, ✓, etc)
                    cleaned = line.lstrip("- *•✓✔ ")  # noqa: B005
                    if cleaned and not cleaned.startswith("#"):
                        actions.append(cleaned)

        return actions
