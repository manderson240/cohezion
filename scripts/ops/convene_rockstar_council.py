#!/usr/bin/env python3
"""CLI runner to convene the Council of Rockstar Scientist Digital Twins.

Analyzes the Cohezion monolith and synthesizes an autonomous microservices blueprint.
Persists findings to SurrealDB (port 8001) and Obsidian Vault.
"""

from __future__ import annotations

import asyncio
import base64
import json
import urllib.request
from pathlib import Path

from cohezion.swarm.agents.rockstar_twins.twin_council import RockstarCouncil


_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_NS = "cohezion"
_SURREAL_DB = "main"
_AUTH = base64.b64encode(b"root:root").decode()


def persist_to_surrealdb(session_id: str, result_dict: dict) -> None:
    """Persist council session deliberation into SurrealDB."""
    try:
        safe_id = session_id.replace("-", "_")
        sql = f"UPSERT council_session:{safe_id} CONTENT {json.dumps(result_dict)};"
        req = urllib.request.Request(
            _SURREAL_URL,
            data=sql.encode("utf-8"),
            headers={
                "surreal-ns": _SURREAL_NS,
                "surreal-db": _SURREAL_DB,
                "Content-Type": "text/plain",
                "Authorization": f"Basic {_AUTH}",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            resp_data = json.loads(resp.read().decode("utf-8"))
            print(
                f"✔ Persisted council session to SurrealDB (port 8001): {resp_data[0].get('status')}"
            )
    except Exception as exc:
        print(f"⚠ SurrealDB persistence advisory: {exc}")


def persist_to_obsidian_vault(session_id: str, markdown_content: str) -> None:
    """Write deliberation retrospective to Obsidian Vault."""
    vault_dir = Path.home() / "vaults" / "cohezion-vault" / "retros"
    vault_dir.mkdir(parents=True, exist_ok=True)
    out_file = vault_dir / f"{session_id}-microservice-refactoring.md"
    try:
        out_file.write_text(markdown_content, encoding="utf-8")
        print(f"✔ Persisted retrospective to Obsidian Vault: {out_file}")
    except Exception as exc:
        print(f"⚠ Obsidian Vault advisory: {exc}")


async def main() -> None:
    print("=" * 85)
    print("🏛 CONVENING COUNCIL OF ROCKSTAR SCIENTIST DIGITAL TWINS")
    print("=" * 85)

    base_dir = Path(__file__).resolve().parents[2] / "src" / "cohezion"
    council = RockstarCouncil()
    deliberation = await council.convene(base_dir)

    md = deliberation.to_markdown()

    # 1. Write project documentation blueprint
    doc_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "architecture"
        / "rockstar_scientist_microservices_blueprint.md"
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(md, encoding="utf-8")
    print(f"✔ Generated microservices architecture blueprint: {doc_path}")

    # 2. Persist to SurrealDB
    result_dict = {
        "session_id": deliberation.session_id,
        "twins": deliberation.twins,
        "total_monolith_loc_analyzed": deliberation.total_monolith_loc_analyzed,
        "mean_entropy_reduction_pct": deliberation.mean_entropy_reduction_pct,
        "proposals": [p.to_dict() for p in deliberation.proposals],
        "timestamp": deliberation.timestamp,
    }
    persist_to_surrealdb(deliberation.session_id, result_dict)

    # 3. Persist to Obsidian Vault
    persist_to_obsidian_vault(deliberation.session_id, md)

    print("\n" + md)


if __name__ == "__main__":
    asyncio.run(main())
