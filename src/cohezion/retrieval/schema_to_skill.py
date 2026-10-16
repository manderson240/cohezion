"""
Schema-to-Skill Generator for Cohezion.
Synthesized from The New Stack article on the Agentic AI Retrieval Problem:
"Schema-to-Skill is the proposed generation step: combine the database schema, engine guidance,
and application-specific knowledge into a short Markdown skill the agent can consult when constructing queries."

Generates an Agent-Ready Schema packaged as a PRIME skill, ensuring agents have rich semantic
understanding of table fields, rank profiles, and graph relationships instead of guessing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger("schema_to_skill")
logger.setLevel(logging.INFO)


@dataclass
class FieldSemantic:
    name: str
    data_type: str
    semantic_meaning: str
    is_filterable: bool = True
    example_value: str = ""


@dataclass
class TableSemantic:
    table_name: str
    description: str
    fields: list[FieldSemantic]
    graph_edges: list[str] = field(default_factory=list)
    recommended_queries: list[str] = field(default_factory=list)


class SchemaToSkillGenerator:
    """
    Introspects and compiles database schemas into an Agent-Ready Skill.
    Eliminates intermediate query translators by teaching agents how to search like a Quant.
    """

    def __init__(self) -> None:
        self.tables: dict[str, TableSemantic] = self._default_schema()

    def _default_schema(self) -> dict[str, TableSemantic]:
        return {
            "goal": TableSemantic(
                table_name="goal",
                description="Long-horizon mission objectives, Kaggle track milestones, and high-level targets.",
                fields=[
                    FieldSemantic(
                        "id",
                        "record",
                        "Unique goal ID, e.g. goal:arc_agi_2_top10",
                        True,
                        "goal:arc_2_ascension",
                    ),
                    FieldSemantic(
                        "title",
                        "string",
                        "Human-readable mission summary",
                        True,
                        "Ascend ARC-AGI-2 to Top 10",
                    ),
                    FieldSemantic(
                        "competition",
                        "string",
                        "Kaggle competition slug identifier",
                        True,
                        "arc-prize-2026",
                    ),
                    FieldSemantic(
                        "status",
                        "string",
                        "Lifecycle state: 'active', 'completed', 'blocked'",
                        True,
                        "active",
                    ),
                    FieldSemantic(
                        "target_score",
                        "float",
                        "Target leaderboard / validation evaluation score",
                        True,
                        "0.85",
                    ),
                    FieldSemantic(
                        "created_at",
                        "datetime",
                        "ISO timestamp when the goal was initialized",
                        True,
                        "2026-10-15T00:00:00Z",
                    ),
                ],
                graph_edges=["->informs_goal->", "<-informs_goal<-"],
                recommended_queries=[
                    "SELECT * FROM goal WHERE competition = 'arc-prize-2026' AND status = 'active';",
                    "SELECT * FROM goal:arc_2_ascension<-informs_goal<-loop_trace;",
                ],
            ),
            "loop_trace": TableSemantic(
                table_name="loop_trace",
                description="Deterministic iteration logs recording hypothesis execution, code diffs, and scalar scores.",
                fields=[
                    FieldSemantic(
                        "id", "record", "Unique loop run record ID", True, "loop_trace:run_101"
                    ),
                    FieldSemantic(
                        "goal_id", "record", "Associated parent goal", True, "goal:arc_2_ascension"
                    ),
                    FieldSemantic(
                        "epoch", "int", "Current iteration counter within loop", True, "42"
                    ),
                    FieldSemantic(
                        "outcome",
                        "string",
                        "Result state: 'SUCCESS', 'FAILURE', 'INCONCLUSIVE'",
                        True,
                        "SUCCESS",
                    ),
                    FieldSemantic(
                        "scalar_score", "float", "Objective function outcome value", True, "0.9430"
                    ),
                    FieldSemantic(
                        "latency_ms",
                        "float",
                        "Inference wall-clock duration in milliseconds",
                        True,
                        "1840.5",
                    ),
                ],
                graph_edges=["->informs_goal->goal", "->verifies_segment->plan_segment"],
                recommended_queries=[
                    "SELECT * FROM loop_trace WHERE outcome = 'SUCCESS' ORDER BY scalar_score DESC LIMIT 5;",
                    "SELECT id, scalar_score, latency_ms FROM loop_trace WHERE goal_id = goal:rsna_knee;",
                ],
            ),
            "agentic_contract": TableSemantic(
                table_name="agentic_contract",
                description="Typed contracts generated by read-only IdeationAgent containing falsifiable rubrics (arXiv:2610.18933).",
                fields=[
                    FieldSemantic(
                        "id", "record", "Unique contract ID", True, "agentic_contract:c1"
                    ),
                    FieldSemantic(
                        "title",
                        "string",
                        "Concise title of proposed hypothesis",
                        True,
                        "Modulo Error Routing",
                    ),
                    FieldSemantic(
                        "falsifiable_hypothesis",
                        "string",
                        "Specific falsifiable scientific statement",
                        False,
                        "Modulo error routing prevents gradient attenuation in hidden layers.",
                    ),
                    FieldSemantic(
                        "worker_id",
                        "string",
                        "Originating worker beam identifier",
                        True,
                        "worker_0",
                    ),
                    FieldSemantic(
                        "target_rubrics",
                        "array",
                        "List of programmatic rubric checks that must be satisfied",
                        False,
                        "[{'id': 'R1_DALE'}]",
                    ),
                ],
                graph_edges=["->contract_evaluated_by->attempt_outcome"],
                recommended_queries=[
                    "SELECT * FROM agentic_contract WHERE worker_id = 'worker_0' ORDER BY created_at DESC LIMIT 5;",
                ],
            ),
        }

    def generate_skill_markdown(self) -> str:
        """Renders the Agent-Ready Schema into the standard PRIME skill template."""
        md = [
            "# SKILL: QUANT_RETRIEVAL_PRIME",
            "",
            "## DOMAIN EXPERTISE",
            "Expert retrieval interface for Cohezion's SurrealDB v3.3.0 knowledge mesh. "
            "Instructs agents on searching like a 2010 Quant by combining exact metadata filters, "
            "dense vector similarity, lexical keyword matching, and graph relationship hops. "
            "Prevents context poisoning by requiring early retrieval quality gating before reasoning.",
            "",
            "## KEY TEXTS & CONCEPTS",
            "- **The Retrieval Problem (BrowseComp-Plus)**: Model intelligence collapses from 93% to 14% under poor retrieval.",
            "- **Search Like a 2010 Quant (Bratseth Thesis)**: Agents must use multi-faceted structured queries instead of short human-style text prompts.",
            "- **Schema-to-Skill**: Semantic understanding of field definitions, filter capabilities, and graph edges.",
            "- **Early Quality Gate**: Halt execution if top retrieval score < 0.65 to avoid hallucinating over poisoned context.",
            "",
            "## AGENT-READY SCHEMAS & SEMANTIC FIELD GUIDANCE",
            "",
        ]

        for name, table in self.tables.items():
            md.append(f"### Table: `{name}`")
            md.append(f"**Purpose**: {table.description}\n")
            md.append("| Field | Type | Filterable | Semantic Meaning | Example |")
            md.append("|---|---|:---:|---|---|")
            for f in table.fields:
                filter_mark = "✓" if f.is_filterable else "✗"
                md.append(
                    f"| `{f.name}` | `{f.data_type}` | {filter_mark} | {f.semantic_meaning} | `{f.example_value}` |"
                )

            if table.graph_edges:
                md.append(f"\n**Graph Traversals**: `{'`, `'.join(table.graph_edges)}`")

            if table.recommended_queries:
                md.append("\n**Quant Query Templates**:")
                md.append("```sql")
                for q in table.recommended_queries:
                    md.append(q)
                md.append("```\n")

        md.extend(
            [
                "## INSTRUCTION",
                "1. Formulate a rich `QuantQuery` specifying `table`, `structured_filters`, `lexical_terms`, and optional `graph_relation`.",
                "2. Invoke `QuantRetriever.retrieve(query)` to obtain ranked `RetrievalItem` objects.",
                "3. Execute `QuantRetriever.evaluate_retrieval_quality(items)`. If `is_sufficient` is False, DO NOT GUESS OR HALLUCINATE.",
                "4. Reformulate search terms or alert the orchestrator when `confidence_level == 'CRITICAL_DEFICIT'`.",
                "",
                "## VERSION",
                "v1.0.0",
                "",
                "## SEE ALSO",
                "- `surrealdb-vector.md`",
                "- `surrealql.md`",
                "- `SURREALDB_V3_TABLE_REFACTORING_PRIME`",
            ]
        )

        return "\n".join(md)

    def write_skill_file(
        self, target_path: str = "src/cohezion/skills/QUANT_RETRIEVAL_PRIME.md"
    ) -> str:
        """Writes the generated skill to the target markdown path."""
        content = self.generate_skill_markdown()
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Generated and saved Agent-Ready Schema skill to: {target_path}")
        return str(path.resolve())
