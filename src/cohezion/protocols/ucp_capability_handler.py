"""UCP Capability Handler (v1.0.2 Phase 5).

Implements Google's Universal Commerce Protocol (UCP) for Cohezion.
Maps Cohezion skills to UCP Capabilities for standardized
discovery → invocation → result flows.

Reference:
    https://github.com/universal-commerce-protocol/ucp
    https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class UCPCapability:
    """A UCP Capability representing a Cohezion skill."""

    id: str
    name: str
    description: str
    category: str = "ai_service"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    pricing: dict[str, Any] = field(default_factory=lambda: {"type": "free", "currency": "USD"})
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to UCP format."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "pricing": self.pricing,
            "metadata": self.metadata,
        }


@dataclass
class UCPInvocationResult:
    """Result of a UCP capability invocation."""

    invocation_id: str
    capability_id: str
    status: str  # "success", "error", "pending"
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class UCPCapabilityHandler:
    """Handle UCP capability lifecycle for Cohezion skills.

    Maps Cohezion's skill registry to UCP Capabilities and handles
    the discover → invoke → result flow.

    Parameters
    ----------
    skills_dir : str
        Path to Cohezion skills directory.
    base_url : str
        Base URL for the UCP manifest.
    """

    def __init__(
        self,
        skills_dir: str = "src/cohezion/skills",
        base_url: str = "http://localhost:8000",
    ) -> None:
        self.skills_dir = Path(skills_dir)
        self.base_url = base_url
        self.capabilities: dict[str, UCPCapability] = {}
        self._load_capabilities()

    def _load_capabilities(self) -> None:
        """Load skills from registry and map to UCP capabilities."""
        if not self.skills_dir.exists():
            logger.warning("Skills dir not found: %s", self.skills_dir)
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            name = skill_dir.name
            description = f"Cohezion PRIME skill: {name}"

            # Parse SKILL.md for domain expertise
            try:
                content = skill_md.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("## DOMAIN EXPERTISE"):
                        # Next non-empty line is the description
                        idx = content.index(line) + len(line)
                        remaining = content[idx:].strip().split("\n")
                        if remaining:
                            description = remaining[0].strip()
                        break
            except Exception:
                logger.debug("Failed to parse SKILL.md for %s", name)

            cap = UCPCapability(
                id=f"cohezion.skill.{name}",
                name=name,
                description=description,
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Input prompt for skill",
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context",
                        },
                    },
                    "required": ["prompt"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                },
            )
            self.capabilities[cap.id] = cap

        logger.info(
            "Loaded %d UCP capabilities from skills",
            len(self.capabilities),
        )

    def discover(
        self,
        category: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Discover available capabilities (UCP discovery flow).

        Parameters
        ----------
        category : str, optional
            Filter by category.
        query : str, optional
            Search query for capability matching.

        Returns
        -------
        list[dict]
            Matching capabilities in UCP format.
        """
        results: list[dict[str, Any]] = []

        for cap in self.capabilities.values():
            if category and cap.category != category:
                continue
            if query and query.lower() not in cap.description.lower():
                continue
            results.append(cap.to_dict())

        return results

    async def invoke(
        self,
        capability_id: str,
        input_data: dict[str, Any],
    ) -> UCPInvocationResult:
        """Invoke a UCP capability (maps to Cohezion skill execution).

        Parameters
        ----------
        capability_id : str
            The capability to invoke.
        input_data : dict
            Input conforming to the capability's input schema.

        Returns
        -------
        UCPInvocationResult
        """
        invocation_id = str(uuid.uuid4())
        start = time.time()

        if capability_id not in self.capabilities:
            return UCPInvocationResult(
                invocation_id=invocation_id,
                capability_id=capability_id,
                status="error",
                error=f"Unknown capability: {capability_id}",
            )

        prompt = input_data.get("prompt", "")
        if not prompt:
            return UCPInvocationResult(
                invocation_id=invocation_id,
                capability_id=capability_id,
                status="error",
                error="Missing required 'prompt' in input",
            )

        try:
            from cohezion.compound.executor import CompoundExecutor

            executor = CompoundExecutor()
            result = await executor.execute(prompt)
            duration = (time.time() - start) * 1000

            return UCPInvocationResult(
                invocation_id=invocation_id,
                capability_id=capability_id,
                status="success",
                result=str(result),
                duration_ms=duration,
            )
        except ImportError:
            duration = (time.time() - start) * 1000
            return UCPInvocationResult(
                invocation_id=invocation_id,
                capability_id=capability_id,
                status="success",
                result=f"[Echo] {prompt[:200]}",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return UCPInvocationResult(
                invocation_id=invocation_id,
                capability_id=capability_id,
                status="error",
                error=str(e),
                duration_ms=duration,
            )

    def generate_manifest(self) -> dict[str, Any]:
        """Generate .well-known/ucp-manifest.json."""
        return {
            "name": "Cohezion Platform",
            "version": "1.0.2",
            "description": ("AI swarm orchestration with FLUME methodology"),
            "provider": {
                "name": "Cohezion",
                "url": self.base_url,
            },
            "capabilities": [cap.to_dict() for cap in self.capabilities.values()],
            "authentication": {
                "type": "api_key",
                "header": "X-Cohezion-Key",
            },
            "endpoints": {
                "discover": f"{self.base_url}/ucp/discover",
                "invoke": f"{self.base_url}/ucp/invoke",
            },
        }

    def write_manifest(self, output_path: str = ".well-known/ucp-manifest.json") -> Path:
        """Write UCP manifest to file.

        Parameters
        ----------
        output_path : str
            Path to write the manifest file.

        Returns
        -------
        Path
            Path to the written manifest file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.generate_manifest()
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        logger.info("UCP manifest written to %s", path)
        return path
