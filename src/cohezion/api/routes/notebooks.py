"""Notebook + simulation static-content routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException


notebooks_router = APIRouter(tags=["notebooks"])


@notebooks_router.get("/notebooks")
async def list_notebooks():
    """List all research notebooks."""
    notebooks_dir = Path("docs/notebooks")
    if not notebooks_dir.exists():
        return {"notebooks": []}
    notebooks = [f.stem for f in notebooks_dir.glob("*.md")]
    return {"notebooks": notebooks}


@notebooks_router.get("/notebooks/{name}")
async def get_notebook(name: str):
    """Get a specific notebook."""
    # Validate name: only allow alphanumeric, dash, underscore (prevent path traversal)
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid notebook name")

    base_dir = Path("docs/notebooks").resolve()
    notebook_path = (base_dir / f"{name}.md").resolve()

    # Ensure resolved path stays within the base directory
    if not str(notebook_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"name": name, "content": notebook_path.read_text()}


@notebooks_router.get("/simulations")
async def list_simulations():
    """List all physics simulations."""
    import json

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        return {"simulations": []}
    data = json.loads(sim_file.read_text())
    return {"simulations": [s["id"] for s in data.get("simulations", [])]}


@notebooks_router.get("/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    """Get a specific simulation result."""
    import json

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        raise HTTPException(status_code=404, detail="No simulations found")
    data = json.loads(sim_file.read_text())
    for sim in data.get("simulations", []):
        if sim["id"] == sim_id:
            return sim
    raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
