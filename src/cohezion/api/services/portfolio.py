"""FastAPI portfolio routes — competition and project tracking.

Endpoints:
    GET  /api/portfolio              → list all projects (summaries)
    GET  /api/portfolio/{id}         → full project detail
    PATCH /api/portfolio/{id}        → update project fields
    POST  /api/portfolio/{id}/note   → append a note
    POST  /api/portfolio             → create / upsert a project
    GET  /api/portfolio/report       → markdown status report
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cohezion.portfolio import PortfolioProject, PortfolioSummary, get_tracker


portfolio_router = APIRouter(tags=["portfolio"])


# ------------------------------------------------------------------
# Request bodies
# ------------------------------------------------------------------


class PatchRequest(BaseModel):
    status: str | None = None
    score: float | None = None
    score_label: str | None = None
    kernel: str | None = None
    worktree: str | None = None


class NoteRequest(BaseModel):
    text: str


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@portfolio_router.get("/portfolio", response_model=list[PortfolioSummary])
async def list_portfolio() -> list[PortfolioSummary]:
    """Return all tracked projects ordered by deadline."""
    return get_tracker().summaries()


@portfolio_router.get("/portfolio/report")
async def portfolio_report() -> dict[str, str]:
    """Return a markdown status report for all projects."""
    from cohezion.portfolio.agent import PortfolioAgent

    agent = PortfolioAgent()
    return {"report": agent.bulk_status_report()}


@portfolio_router.get("/portfolio/{project_id}", response_model=PortfolioProject)
async def get_project(project_id: str) -> PortfolioProject:
    project = get_tracker().get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


@portfolio_router.post("/portfolio", response_model=PortfolioProject, status_code=201)
async def create_project(project: PortfolioProject) -> PortfolioProject:
    """Create or replace a portfolio project."""
    return get_tracker().upsert(project)


@portfolio_router.patch("/portfolio/{project_id}", response_model=PortfolioProject)
async def update_project(project_id: str, body: PatchRequest) -> PortfolioProject:
    """Patch specific fields on an existing project."""
    updates: dict[str, Any] = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = get_tracker().patch(project_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return result


@portfolio_router.post("/portfolio/{project_id}/note", response_model=PortfolioProject)
async def add_note(project_id: str, body: NoteRequest) -> PortfolioProject:
    """Append a timestamped note to a project."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")
    result = get_tracker().add_note(project_id, body.text.strip())
    if result is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return result
