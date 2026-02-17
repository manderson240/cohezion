"""Miscellaneous endpoints - notebooks, simulations, etc."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException


logger = logging.getLogger(__name__)

router = APIRouter(tags=["misc"])


# Notebook endpoints
@router.get("/notebooks")
async def list_notebooks():
    """List all research notebooks."""

    notebooks_dir = Path("docs/notebooks")
    if not notebooks_dir.exists():
        return {"notebooks": []}
    notebooks = [f.stem for f in notebooks_dir.glob("*.md")]
    return {"notebooks": notebooks}


@router.get("/notebooks/{name}")
async def get_notebook(name: str):
    """Get a specific notebook."""

    notebook_path = Path(f"docs/notebooks/{name}.md")
    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail=f"Notebook {name} not found")
    return {"name": name, "content": notebook_path.read_text()}


# Simulation endpoints
@router.get("/simulations")
async def list_simulations():
    """List all physics simulations."""
    from pathlib import Path

    sim_file = Path(
        "src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json"
    )
    if not sim_file.exists():
        return {"simulations": []}
    data = json.loads(sim_file.read_text())
    return {"simulations": [s["id"] for s in data.get("simulations", [])]}


@router.get("/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    """Get a specific simulation result."""
    from pathlib import Path

    sim_file = Path(
        "src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json"
    )
    if not sim_file.exists():
        raise HTTPException(status_code=404, detail="No simulations found")
    data = json.loads(sim_file.read_text())
    for sim in data.get("simulations", []):
        if sim["id"] == sim_id:
            return sim
    raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
