"""Typed data products for Cohezion's Data Mesh.

Every piece of data shared between agents is a Data Product — a first-class
entity with schema, ownership, quality guarantees, and discoverability.

References:
  - Dehghani (2022): Data Mesh, O'Reilly — "data as a product" principle
  - InfoWorld (2026): Enterprise-Grade MCP Registry — tool metadata as data products
  - Percival (1946): The Knower — awareness of what data exists and its provenance
  - Smith/Peret (RS2): Field fabric — data topology connecting agent domains

Each MCP server in Cohezion (17+ servers) exposes data products:
  - bmad server → workflow artifacts, agent manifests
  - skills server → skill definitions, refinement metrics
  - journey server → agent journey checkpoints, trajectory data
  - memory server → vault entries, compiled knowledge
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DataProductStatus(str, Enum):
    """Lifecycle status of a data product."""

    DRAFT = "draft"  # Being defined, not yet available
    ACTIVE = "active"  # Published and serving consumers
    DEPRECATED = "deprecated"  # Still available but scheduled for removal
    ARCHIVED = "archived"  # No longer available


class DataQualityTier(str, Enum):
    """Quality tier determining SLA expectations."""

    BRONZE = "bronze"  # Best-effort, no SLA (experimental data)
    SILVER = "silver"  # Defined schema, >95% availability
    GOLD = "gold"  # Full schema + lineage + <100ms latency


@dataclass(frozen=True)
class DataProductSchema:
    """Schema definition for a data product's output.

    Uses JSON Schema format for interoperability with A2UI catalogs
    and AG-UI event types.
    """

    fields: dict[str, str]  # field_name -> type description
    version: str = "1.0.0"
    json_schema_ref: str | None = None  # Optional JSON Schema $ref


@dataclass
class DataProduct:
    """A first-class data entity in Cohezion's Data Mesh.

    Every tool output, vault entry, and agent artifact is a data product
    with explicit ownership, schema, and quality guarantees.

    This maps to the Field fabric in Smith's 4-fabric model:
    data products form the topological connections between agent domains,
    and gauge invariance (governance) ensures consistency across domains.
    """

    # Identity
    product_id: str
    name: str
    description: str

    # Ownership (Data Mesh principle 1: domain ownership)
    owner_domain: str  # MCP server name (e.g., "bmad", "skills", "journey")
    owner_agent: str | None = None  # Specific agent if applicable

    # Schema (Data Mesh principle 2: data as product)
    schema: DataProductSchema = field(default_factory=lambda: DataProductSchema(fields={}))
    output_format: str = "json"  # json, sse, binary

    # Quality (Data Mesh principle 3+4: self-serve + governance)
    quality_tier: DataQualityTier = DataQualityTier.BRONZE
    status: DataProductStatus = DataProductStatus.DRAFT

    # SLA
    max_latency_ms: int = 5000  # Maximum response time
    availability_target: float = 0.95  # Target uptime fraction

    # Observability
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    access_count: int = 0
    error_count: int = 0

    # Lineage
    source_products: list[str] = field(default_factory=list)  # product_ids this derives from
    mcp_tool_name: str | None = None  # MCP tool that produces this product

    def record_access(self, success: bool = True) -> None:
        """Record a data product access event."""
        self.last_accessed = time.time()
        self.access_count += 1
        if not success:
            self.error_count += 1

    @property
    def error_rate(self) -> float:
        """Current error rate as a fraction."""
        return self.error_count / self.access_count if self.access_count > 0 else 0.0

    @property
    def meets_sla(self) -> bool:
        """Whether this product meets its quality tier SLA."""
        if self.quality_tier == DataQualityTier.BRONZE:
            return True  # No SLA for bronze
        availability = 1.0 - self.error_rate
        return availability >= self.availability_target

    def to_registry_entry(self) -> dict[str, Any]:
        """Serialize for the MCP registry catalog."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "owner_domain": self.owner_domain,
            "quality_tier": self.quality_tier.value,
            "status": self.status.value,
            "schema_version": self.schema.version,
            "output_format": self.output_format,
            "mcp_tool": self.mcp_tool_name,
            "max_latency_ms": self.max_latency_ms,
            "access_count": self.access_count,
            "error_rate": round(self.error_rate, 4),
            "meets_sla": self.meets_sla,
        }


# --- Pre-defined data products for Cohezion's 17+ MCP servers ---

COHEZION_DATA_PRODUCTS = {
    "bmad-workflow": DataProduct(
        product_id="bmad-workflow",
        name="BMAD Workflow Artifacts",
        description="Agile workflow outputs: specs, stories, sprint plans",
        owner_domain="bmad",
        schema=DataProductSchema(fields={"workflow_id": "str", "status": "str", "artifacts": "list"}),
        quality_tier=DataQualityTier.SILVER,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name="bmad_execute_workflow",
    ),
    "skill-definition": DataProduct(
        product_id="skill-definition",
        name="PRIME Skill Definitions",
        description="Skill markdown + metadata from the skill registry",
        owner_domain="skills",
        schema=DataProductSchema(fields={"skill_name": "str", "content": "str", "metrics": "dict"}),
        quality_tier=DataQualityTier.GOLD,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name="skill_get_definition",
    ),
    "journey-checkpoint": DataProduct(
        product_id="journey-checkpoint",
        name="Agent Journey Checkpoints",
        description="12D state snapshots from JourneyTracker",
        owner_domain="journey",
        schema=DataProductSchema(fields={"agent_id": "str", "state_12d": "list[float]", "coherence": "float"}),
        quality_tier=DataQualityTier.GOLD,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name="journey_save_checkpoint",
    ),
    "vault-entry": DataProduct(
        product_id="vault-entry",
        name="Vault Knowledge Entries",
        description="Decisions, patterns, experiments from the knowledge vault",
        owner_domain="memory",
        schema=DataProductSchema(fields={"entry_id": "str", "category": "str", "content": "str"}),
        quality_tier=DataQualityTier.GOLD,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name="vault_find_relevant_context",
    ),
    "agui-event-stream": DataProduct(
        product_id="agui-event-stream",
        name="AG-UI Event Stream",
        description="Typed SSE events for Genesis cosmogony",
        owner_domain="api",
        schema=DataProductSchema(fields={"type": "AGUIEventType", "timestamp": "str", "payload": "dict"}),
        output_format="sse",
        quality_tier=DataQualityTier.SILVER,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name=None,  # Direct HTTP endpoint, not MCP tool
    ),
    "observer-consistency": DataProduct(
        product_id="observer-consistency",
        name="OPH Observer Consistency Scores",
        description="Overlap consistency between agent observer patches on S²",
        owner_domain="physics",
        schema=DataProductSchema(fields={"agent_a": "str", "agent_b": "str", "consistency": "float", "coherent": "bool"}),
        quality_tier=DataQualityTier.SILVER,
        status=DataProductStatus.ACTIVE,
        mcp_tool_name=None,
    ),
}
