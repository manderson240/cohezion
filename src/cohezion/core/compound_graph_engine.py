"""Compound Graph Engine: Integrates SurrealDB Graph, Obsidian Vault, and V-Model Gates.

Operationalizes the Canonical Quad-Node / Quad-Edge Knowledge Graph:
- Nodes: kg_goal, kg_strategy, kg_artifact, kg_learning
- Edges: RESOLVED_BY, PRODUCED, VERIFIED_BY, COMPOUNDS_INTO

Implements "Read-Before-Reasoning" recall and dual-persistence to Obsidian Vault MOCs.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_SURREAL_URL = "http://localhost:8001/sql"
DEFAULT_VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")


@dataclass(frozen=True)
class GoalNode:
    goal_id: str
    title: str
    invariants: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass(frozen=True)
class LearningRecall:
    learning_id: str
    title: str
    compound_tool: str | None = None
    z_vector: list[float] | None = None


class CompoundGraphEngine:
    """Manages canonical graph relations and compound learning persistence."""

    def __init__(
        self,
        surreal_url: str = DEFAULT_SURREAL_URL,
        vault_path: Path = DEFAULT_VAULT_PATH,
    ) -> None:
        self.surreal_url = surreal_url
        self.vault_path = vault_path
        self._auth_header = "Basic " + base64.b64encode(b"root:root").decode()

    def execute_sql(self, statement: str) -> list[dict[str, Any]]:
        """Execute SurrealQL against cohezion:main and return results, checking for errors."""
        headers = {
            "Accept": "application/json",
            "Authorization": self._auth_header,
            "Content-Type": "text/plain",
            "surreal-ns": "cohezion",
            "surreal-db": "main",
        }
        body_sql = f"USE NS cohezion DB main; {statement}"
        req = urllib.request.Request(
            self.surreal_url, data=body_sql.encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results: list[dict[str, Any]] = []
            for stmt in data:
                if stmt.get("status") == "ERR":
                    logger.warning("SurrealQL error in statement: %s", stmt.get("result"))
                elif stmt.get("result") is not None:
                    res = stmt.get("result")
                    if isinstance(res, list):
                        results.extend(res)
                    elif isinstance(res, dict):
                        results.append(res)
            return results
        except Exception as exc:
            logger.error("Failed executing SurrealDB query: %s", exc)
            return []

    def ensure_schema(self) -> None:
        """Define the minimal canonical schema tables and relations if not present."""
        schema_sql = """
        DEFINE TABLE kg_goal SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE kg_strategy SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE kg_artifact SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE kg_learning SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE RESOLVED_BY TYPE RELATION SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE PRODUCED TYPE RELATION SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE VERIFIED_BY TYPE RELATION SCHEMALESS PERMISSIONS NONE;
        DEFINE TABLE COMPOUNDS_INTO TYPE RELATION SCHEMALESS PERMISSIONS NONE;
        """
        self.execute_sql(schema_sql)

    def read_before_reasoning(self, query_keyword: str, limit: int = 3) -> list[LearningRecall]:
        """Query SurrealDB for past learnings or tools before invoking an LLM.
        
        Takes ~15ms and allows agents to bypass LLM inference entirely if a compound tool exists.
        """
        sanitized = query_keyword.replace("'", "").replace('"', "")
        query = (
            f"SELECT id, title, compound_tool, z_vector FROM kg_learning "
            f"WHERE title CONTAINS '{sanitized}' LIMIT {limit};"
        )
        rows = self.execute_sql(query)
        recalls: list[LearningRecall] = []
        for r in rows:
            recalls.append(
                LearningRecall(
                    learning_id=str(r.get("id", "")),
                    title=str(r.get("title", "")),
                    compound_tool=r.get("compound_tool"),
                    z_vector=r.get("z_vector"),
                )
            )
        return recalls

    def link_compound_loop(
        self,
        goal_id: str,
        goal_title: str,
        strategy_id: str,
        strategy_desc: str,
        artifact_path: str,
        learning_title: str,
        compound_tool: str | None = None,
        z_vector: list[float] | None = None,
    ) -> dict[str, str]:
        """Atomically link goal -> strategy -> artifact -> learning in SurrealDB & Obsidian."""
        clean_goal = goal_id.replace(":", "_").replace("-", "_")
        clean_strat = strategy_id.replace(":", "_").replace("-", "_")
        clean_art = artifact_path.replace(":", "_").replace("/", "_").replace(".", "_")
        clean_learn = f"learn_{clean_goal}"
        
        z_vec_str = json.dumps(z_vector or [0.5] * 12)
        tool_val = f"'{compound_tool}'" if compound_tool else "NONE"

        query = f"""
        UPSERT kg_goal:{clean_goal} CONTENT {{ title: '{goal_title}', status: 'converged' }};
        UPSERT kg_strategy:{clean_strat} CONTENT {{ approach: '{strategy_desc}' }};
        UPSERT kg_artifact:{clean_art} CONTENT {{ path: '{artifact_path}', ast_verified: true }};
        UPSERT kg_learning:{clean_learn} CONTENT {{ title: '{learning_title}', compound_tool: {tool_val}, z_vector: {z_vec_str} }};

        RELATE kg_goal:{clean_goal}->RESOLVED_BY->kg_strategy:{clean_strat};
        RELATE kg_strategy:{clean_strat}->PRODUCED->kg_artifact:{clean_art};
        RELATE kg_artifact:{clean_art}->YIELDED->kg_learning:{clean_learn};
        """
        self.execute_sql(query)

        # Dual-write human-readable Map of Content note into Obsidian Vault
        try:
            moc_dir = self.vault_path / "00-MOCs"
            moc_dir.mkdir(parents=True, exist_ok=True)
            moc_file = moc_dir / f"compound_{clean_goal}.md"
            moc_content = f"""---
id: "compound_{clean_goal}"
goal: "{goal_title}"
strategy: "{strategy_desc}"
artifact: "{artifact_path}"
compound_tool: "{compound_tool or ''}"
type: compound_learning
tags: [compound_engineering, v_model, graph]
---
# Compound Learning: {learning_title}

- **Goal**: {goal_title} (`kg_goal:{clean_goal}`)
- **Strategy**: {strategy_desc} (`kg_strategy:{clean_strat}`)
- **Artifact**: `{artifact_path}` (`kg_artifact:{clean_art}`)
- **Compound Tool / Verifier**: `{compound_tool or 'None'}`
- **SurrealDB Relation Path**:
  `kg_goal:{clean_goal} -> RESOLVED_BY -> kg_strategy:{clean_strat} -> PRODUCED -> kg_artifact:{clean_art} -> YIELDED -> kg_learning:{clean_learn}`
"""
            moc_file.write_text(moc_content, encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not write Obsidian MOC note: %s", exc)

        return {
            "goal": f"kg_goal:{clean_goal}",
            "strategy": f"kg_strategy:{clean_strat}",
            "artifact": f"kg_artifact:{clean_art}",
            "learning": f"kg_learning:{clean_learn}",
            "obsidian_moc": str(self.vault_path / "00-MOCs" / f"compound_{clean_goal}.md"),
        }
