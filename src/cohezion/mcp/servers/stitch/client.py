"""Google Stitch MCP Client for UI generation with sovereignty enforcement.

This client integrates with Google Stitch (https://stitch.withgoogle.com) via
the Stitch MCP Server for design-to-code workflows with constitutional compliance.

Key Features:
- Design Agent: AI-native canvas for UI generation from natural language
- Design DNA: Extract design system metadata as DESIGN.md (agent-friendly format)
- Agent Skills: Pre-built workflows (design-critique, voice-canvas, design-to-code)
- Dark Pattern Detection: Constitutional compliance for UI designs
- Sovereignty Enforcement: Deceptive UI blocking, accessibility requirements

Usage:
    from cohezion.mcp.servers.stitch.client import StitchMCPClient

    client = StitchMCPClient()
    design = await client.generate_design("Create a pricing page")

    # Check for dark patterns
    dark_patterns = await client.check_dark_patterns(design.project_id)

    # Export Design DNA
    design_dna = await client.export_design_dna(design.project_id)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import aiohttp

from cohezion.mcp.shared.client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class StitchDesign:
    """Result from Stitch design generation."""

    project_id: str
    screens: list[dict[str, Any]]
    design_dna: dict[str, Any]
    accessibility_score: float
    dark_patterns: list[str]
    requires_human_review: bool


@dataclass
class DarkPattern:
    """Dark pattern detection result."""

    pattern_type: str  # e.g., "hidden_costs", "forced_action", "misdirection"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    location: str  # Which screen/component


class StitchMCPClient:
    """Client for Google Stitch MCP Server with sovereignty enforcement.

    Integrates with Stitch for UI generation while enforcing constitutional
    compliance (no deceptive UI, accessibility requirements, dark pattern detection).
    """

    def __init__(
        self,
        stitch_api_url: str | None = None,
        stitch_api_key: str | None = None,
        local_mcp_url: str | None = None,
    ):
        """Initialize Stitch MCP client.

        Args:
            stitch_api_url: Google Stitch API URL (default: from env STITCH_API_URL)
            stitch_api_key: Stitch API key (default: from env STITCH_API_KEY)
            local_mcp_url: Local MCP server URL (default: http://localhost:8370)
        """
        self.stitch_api_url = stitch_api_url or os.getenv("STITCH_API_URL", "https://stitch-mcp.withgoogle.com")
        self.stitch_api_key = stitch_api_key or os.getenv("STITCH_API_KEY", "")
        self.local_mcp_url = local_mcp_url or "http://localhost:8370"

        # MCP client for local Stitch MCP server
        self.mcp_client = MCPClient(base_url=self.local_mcp_url)

        # Direct Stitch API session (for cloud API calls)
        self._stitch_session: aiohttp.ClientSession | None = None

    async def _get_stitch_session(self) -> aiohttp.ClientSession:
        """Get or create Stitch API session."""
        if self._stitch_session is None or self._stitch_session.closed:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.stitch_api_key}",
            }
            self._stitch_session = aiohttp.ClientSession(headers=headers)
        return self._stitch_session

    async def generate_design(self, prompt: str, sovereignty_context: dict[str, Any] | None = None) -> StitchDesign:
        """Generate UI design from natural language prompt.

        Args:
            prompt: Natural language description of UI to generate
            sovereignty_context: Optional sovereignty metadata (agent_id, ethical_constraints)

        Returns:
            StitchDesign with project_id, screens, design_dna

        Raises:
            ValueError: If prompt contains deceptive patterns
        """
        # Check prompt for deceptive patterns (constitutional compliance)
        deceptive_check = self._check_prompt_for_deception(prompt)
        if deceptive_check["is_deceptive"]:
            raise ValueError(f"Deceptive UI pattern detected in prompt: {deceptive_check['reason']}")

        # Call local MCP server tool
        result = await self.mcp_client.call_tool(
            tool_name="stitch_generate_design",
            params={
                "prompt": prompt,
                "sovereignty_context": sovereignty_context or {},
            },
        )

        if "error" in result:
            raise RuntimeError(f"Stitch MCP error: {result['error']}")

        # Extract result
        project_id = result["result"]["project_id"]
        screens = result["result"]["screens"]

        # Get Design DNA
        design_dna = await self.get_design_dna(project_id)

        # Check for dark patterns
        dark_patterns = await self.check_dark_patterns(project_id)

        # Accessibility score (from Design DNA)
        accessibility_score = design_dna.get("accessibility_score", 0.0)

        # Determine if human review required
        requires_review = (
            len(dark_patterns) > 0
            or accessibility_score < 0.7
            or sovereignty_context.get("human_review_required", False)
        )

        return StitchDesign(
            project_id=project_id,
            screens=screens,
            design_dna=design_dna,
            accessibility_score=accessibility_score,
            dark_patterns=[p["pattern_type"] for p in dark_patterns],
            requires_human_review=requires_review,
        )

    async def get_design_dna(self, project_id: str) -> dict[str, Any]:
        """Get Design DNA (design system metadata) for a project.

        Args:
            project_id: Stitch project ID

        Returns:
            Design DNA dictionary with colors, typography, spacing, components
        """
        result = await self.mcp_client.call_tool(
            tool_name="stitch_get_design_dna",
            params={"project_id": project_id},
        )

        if "error" in result:
            raise RuntimeError(f"Failed to get Design DNA: {result['error']}")

        return result["result"]["design_dna"]

    async def export_design_md(self, project_id: str) -> str:
        """Export design as DESIGN.md (agent-friendly markdown format).

        Args:
            project_id: Stitch project ID

        Returns:
            DESIGN.md markdown content
        """
        result = await self.mcp_client.call_tool(
            tool_name="stitch_export_design_md",
            params={"project_id": project_id},
        )

        if "error" in result:
            raise RuntimeError(f"Failed to export DESIGN.md: {result['error']}")

        return result["result"]["design_md"]

    async def check_dark_patterns(self, project_id: str) -> list[dict[str, Any]]:
        """Check design for dark patterns (deceptive UI).

        Dark patterns detected:
        - Hidden costs (surprise fees at checkout)
        - Forced action (can't proceed without accepting)
        - Misdirection (confusing buttons, misleading labels)
        - Obstruction (hard to cancel, hidden unsubscribe)
        - Sneaking (adding items to cart without consent)

        Args:
            project_id: Stitch project ID

        Returns:
            List of detected dark patterns with severity
        """
        result = await self.mcp_client.call_tool(
            tool_name="stitch_check_dark_patterns",
            params={"project_id": project_id},
        )

        if "error" in result:
            logger.warning(f"Dark pattern check failed: {result['error']}")
            return []

        return result["result"]["dark_patterns"]

    async def execute_agent_skill(
        self,
        skill_name: str,
        input_data: dict[str, Any],
        sovereignty_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a Stitch Agent Skill.

        Available skills:
        - design-critique: Real-time design feedback
        - voice-canvas: Voice-controlled design updates
        - design-to-code: Convert Stitch → HTML/React
        - multi-version-reasoning: Explore design alternatives
        - export-design-dna: Extract design system metadata

        Args:
            skill_name: Agent skill name
            input_data: Skill input parameters
            sovereignty_context: Sovereignty metadata (agent_id, constraints)

        Returns:
            Skill execution result
        """
        result = await self.mcp_client.call_tool(
            tool_name="stitch_execute_skill",
            params={
                "skill_name": skill_name,
                "input_data": input_data,
                "sovereignty_context": sovereignty_context or {},
            },
        )

        if "error" in result:
            raise RuntimeError(f"Stitch skill '{skill_name}' failed: {result['error']}")

        return result["result"]

    def _check_prompt_for_deception(self, prompt: str) -> dict[str, Any]:
        """Check prompt for deceptive UI patterns (constitutional compliance).

        Args:
            prompt: UI generation prompt

        Returns:
            Dict with is_deceptive (bool) and reason (str)
        """
        prompt_lower = prompt.lower()

        # Deceptive keywords
        deceptive_patterns = {
            "hide cancel": "Hiding cancel/unsubscribe buttons is deceptive",
            "mislead": "Misleading users violates honesty principle",
            "trick user": "Tricking users is deceptive",
            "confuse": "Intentionally confusing UI is deceptive",
            "dark pattern": "Explicit dark pattern request",
            "hidden fee": "Hidden costs violate transparency",
            "forced consent": "Forced consent without choice is coercive",
            "fake countdown": "Fake urgency/scarcity is manipulative",
            "bait and switch": "Bait-and-switch is deceptive",
        }

        for pattern, reason in deceptive_patterns.items():
            if pattern in prompt_lower:
                return {"is_deceptive": True, "reason": reason}

        # No deceptive patterns detected
        return {"is_deceptive": False, "reason": ""}

    async def close(self) -> None:
        """Close client sessions."""
        await self.mcp_client.close()
        if self._stitch_session and not self._stitch_session.closed:
            await self._stitch_session.close()
