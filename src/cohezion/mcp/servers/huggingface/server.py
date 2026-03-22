"""Hugging Face MCP Server - Model discovery, inference, and dataset access.

Port: 8365
Features:
- Search models, datasets, spaces
- Model inference via API
- Download and cache models
- Dataset exploration
- Space deployment info
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

import aiohttp
from aiohttp import web

from cohezion.security.credentials import get_credentials


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8365"))
# Primary: Vault Warden, Fallback: Environment
HF_API_TOKEN = get_credentials().get_secret("COHEZION_HF_TOKEN", env_var="HF_API_TOKEN") or ""
HF_API_BASE = "https://huggingface.co/api"


class HuggingFaceService:
    """Hugging Face Hub API client."""

    def __init__(self, token: str | None = None):
        self.token = token or HF_API_TOKEN
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            headers = {
                "Accept": "application/json",
                "User-Agent": "Cohezion-HF-MCP/1.0",
            }
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def search_models(
        self, query: str = "", library: str | None = None, task: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Search Hugging Face models."""
        session = await self._get_session()
        url = f"{HF_API_BASE}/models"

        params = {"limit": limit}
        if query:
            params["search"] = query
        if library:
            params["library"] = library
        if task:
            params["task"] = task

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "id": m["id"],
                            "modelId": m["modelId"],
                            "author": m.get("author", ""),
                            "downloads": m.get("downloads", 0),
                            "likes": m.get("likes", 0),
                            "tags": m.get("tags", []),
                            "pipeline_tag": m.get("pipeline_tag", "unknown"),
                            "url": f"https://huggingface.co/{m['id']}",
                        }
                        for m in data
                    ][:limit]
                else:
                    logger.error(f"HF API error: {resp.status}")
                    return []
        except Exception as e:
            logger.exception(f"Error searching models: {e}")
            return []

    async def get_model_info(self, model_id: str) -> dict[str, Any] | None:
        """Get detailed model information."""
        session = await self._get_session()
        url = f"{HF_API_BASE}/models/{model_id}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "id": data["id"],
                        "modelId": data["modelId"],
                        "author": data.get("author", ""),
                        "downloads": data.get("downloads", 0),
                        "likes": data.get("likes", 0),
                        "tags": data.get("tags", []),
                        "pipeline_tag": data.get("pipeline_tag", "unknown"),
                        "config": data.get("config", {}),
                        "siblings": [s["rfilename"] for s in data.get("siblings", [])[:20]],
                        "url": f"https://huggingface.co/{data['id']}",
                        "card": data.get("cardData", {}),
                    }
                else:
                    return None
        except Exception as e:
            logger.exception(f"Error getting model info: {e}")
            return None

    async def search_datasets(self, query: str = "", limit: int = 10) -> list[dict]:
        """Search Hugging Face datasets."""
        session = await self._get_session()
        url = f"{HF_API_BASE}/datasets"

        params = {"limit": limit}
        if query:
            params["search"] = query

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "id": d["id"],
                            "author": d.get("author", ""),
                            "downloads": d.get("downloads", 0),
                            "likes": d.get("likes", 0),
                            "tags": d.get("tags", []),
                            "url": f"https://huggingface.co/datasets/{d['id']}",
                        }
                        for d in data
                    ][:limit]
                else:
                    return []
        except Exception as e:
            logger.exception(f"Error searching datasets: {e}")
            return []

    async def search_spaces(self, query: str = "", limit: int = 10) -> list[dict]:
        """Search Hugging Face Spaces."""
        session = await self._get_session()
        url = f"{HF_API_BASE}/spaces"

        params = {"limit": limit}
        if query:
            params["search"] = query

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "id": s["id"],
                            "author": s.get("author", ""),
                            "likes": s.get("likes", 0),
                            "sdk": s.get("sdk", "unknown"),
                            "url": f"https://huggingface.co/spaces/{s['id']}",
                        }
                        for s in data
                    ][:limit]
                else:
                    return []
        except Exception as e:
            logger.exception(f"Error searching spaces: {e}")
            return []

    async def get_inference_api(self, model_id: str, inputs: str) -> dict[str, Any]:
        """Run inference on a model via HF Inference API."""
        if not self.token:
            return {"error": "HF_API_TOKEN required for inference"}

        session = await self._get_session()
        url = f"https://api-inference.huggingface.co/models/{model_id}"

        try:
            async with session.post(url, json={"inputs": inputs}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "model_id": model_id,
                        "result": data,
                        "status": "success",
                    }
                else:
                    text = await resp.text()
                    return {
                        "error": f"Inference failed: {resp.status}",
                        "details": text,
                    }
        except Exception as e:
            logger.exception(f"Inference error: {e}")
            return {"error": str(e)}

    async def get_model_readme(self, model_id: str) -> str:
        """Get model README content."""
        session = await self._get_session()
        url = f"https://huggingface.co/{model_id}/raw/main/README.md"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    return f"README not found for {model_id}"
        except Exception as e:
            return f"Error fetching README: {e}"

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global service instance
_service: HuggingFaceService | None = None


def get_service() -> HuggingFaceService:
    """Get or create HF service."""
    global _service
    if _service is None:
        _service = HuggingFaceService(HF_API_TOKEN)
    return _service


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "huggingface",
            "port": MCP_PORT,
            "authenticated": bool(HF_API_TOKEN),
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Hugging Face MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "authenticated": bool(HF_API_TOKEN),
            "tools": [
                "hf_search_models",
                "hf_get_model_info",
                "hf_search_datasets",
                "hf_search_spaces",
                "hf_inference",
                "hf_get_readme",
            ],
        }
    )


@routes.post("/tools/hf_search_models")
async def tool_hf_search_models(request: web.Request) -> web.Response:
    """Search Hugging Face models."""
    try:
        data = await request.json()
        query = data.get("query", "")
        library = data.get("library")  # e.g., "transformers", "pytorch"
        task = data.get("task")  # e.g., "text-classification"
        limit = data.get("limit", 10)

        service = get_service()
        models = await service.search_models(query, library, task, limit)

        return web.json_response(
            {
                "tool": "hf_search_models",
                "query": query,
                "library": library,
                "task": task,
                "count": len(models),
                "models": models,
            }
        )
    except Exception as e:
        logger.exception("Error searching models")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/hf_get_model_info")
async def tool_hf_get_model_info(request: web.Request) -> web.Response:
    """Get detailed model information."""
    try:
        data = await request.json()
        model_id = data.get("model_id", "")

        if not model_id:
            return web.json_response({"error": "model_id is required"}, status=400)

        service = get_service()
        info = await service.get_model_info(model_id)

        if info:
            return web.json_response(
                {
                    "tool": "hf_get_model_info",
                    "model_id": model_id,
                    "info": info,
                }
            )
        else:
            return web.json_response({"error": f"Model not found: {model_id}"}, status=404)
    except Exception as e:
        logger.exception("Error getting model info")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/hf_search_datasets")
async def tool_hf_search_datasets(request: web.Request) -> web.Response:
    """Search Hugging Face datasets."""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 10)

        service = get_service()
        datasets = await service.search_datasets(query, limit)

        return web.json_response(
            {
                "tool": "hf_search_datasets",
                "query": query,
                "count": len(datasets),
                "datasets": datasets,
            }
        )
    except Exception as e:
        logger.exception("Error searching datasets")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/hf_search_spaces")
async def tool_hf_search_spaces(request: web.Request) -> web.Response:
    """Search Hugging Face Spaces."""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 10)

        service = get_service()
        spaces = await service.search_spaces(query, limit)

        return web.json_response(
            {
                "tool": "hf_search_spaces",
                "query": query,
                "count": len(spaces),
                "spaces": spaces,
            }
        )
    except Exception as e:
        logger.exception("Error searching spaces")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/hf_inference")
async def tool_hf_inference(request: web.Request) -> web.Response:
    """Run inference on a model."""
    try:
        data = await request.json()
        model_id = data.get("model_id", "")
        inputs = data.get("inputs", "")

        if not model_id or not inputs:
            return web.json_response({"error": "model_id and inputs are required"}, status=400)

        if not HF_API_TOKEN:
            return web.json_response(
                {"error": "HF_API_TOKEN environment variable required for inference"}, status=401
            )

        service = get_service()
        result = await service.get_inference_api(model_id, inputs)

        return web.json_response(
            {
                "tool": "hf_inference",
                "model_id": model_id,
                "result": result,
            }
        )
    except Exception as e:
        logger.exception("Inference error")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/hf_get_readme")
async def tool_hf_get_readme(request: web.Request) -> web.Response:
    """Get model README."""
    try:
        data = await request.json()
        model_id = data.get("model_id", "")

        if not model_id:
            return web.json_response({"error": "model_id is required"}, status=400)

        service = get_service()
        readme = await service.get_model_readme(model_id)

        return web.json_response(
            {
                "tool": "hf_get_readme",
                "model_id": model_id,
                "readme": readme[:5000] if len(readme) > 5000 else readme,
                "truncated": len(readme) > 5000,
            }
        )
    except Exception as e:
        logger.exception("Error getting README")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the Hugging Face MCP Server."""
    get_service()

    logger.info(f"Starting Hugging Face MCP Server on port {MCP_PORT}")
    if not HF_API_TOKEN:
        logger.warning("HF_API_TOKEN not set - inference will fail")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ HF MCP Server running on http://localhost:{MCP_PORT}")
    logger.info("   API: https://huggingface.co/docs/api")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("HF MCP Server stopped")
