"""Hugging Face MCP Server - Model Context Protocol wrapper for Hugging Face Hub access.

Provides: Search models, datasets, spaces, inference, and README access.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from fastmcp import FastMCP

from cohezion.security.credentials import get_credentials


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("huggingface-mcp")

# Lazy accessor for HF_API_TOKEN to prevent startup latency
_hf_api_token: str | None = None


def get_hf_api_token() -> str:
    """Get Hugging Face API token with lazy initialization."""
    global _hf_api_token
    if _hf_api_token is None:
        _hf_api_token = (
            get_credentials().get_secret("COHEZION_HF_TOKEN", env_var="HF_API_TOKEN") or ""
        )
    return _hf_api_token


HF_API_BASE = "https://huggingface.co/api"

# Initialize FastMCP server
app = FastMCP("cohezion-huggingface")


class HuggingFaceService:
    """Hugging Face Hub API client."""

    def __init__(self, token: str | None = None):
        self.token = token or get_hf_api_token()
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


# Global service instance
_service: HuggingFaceService | None = None


def get_service() -> HuggingFaceService:
    """Get or create HF service."""
    global _service
    if _service is None:
        _service = HuggingFaceService(get_hf_api_token())
    return _service


@app.tool()
async def hf_search_models(
    query: str = "", library: str | None = None, task: str | None = None, limit: int = 10
) -> dict[str, Any]:
    """Search Hugging Face models.

    Args:
        query: Search query
        library: Filter by library (transformers, pytorch, etc.)
        task: Filter by task (text-classification, image-segmentation, etc.)
        limit: Max results
    """
    service = get_service()
    models = await service.search_models(query, library, task, limit)
    return {"count": len(models), "models": models}


@app.tool()
async def hf_get_model_info(model_id: str) -> dict[str, Any]:
    """Get detailed model information.

    Args:
        model_id: Model identifier (e.g., 'meta-llama/Llama-2-7b')
    """
    service = get_service()
    info = await service.get_model_info(model_id)
    if not info:
        return {"error": f"Model not found: {model_id}"}
    return info


@app.tool()
async def hf_search_datasets(query: str = "", limit: int = 10) -> dict[str, Any]:
    """Search Hugging Face datasets.

    Args:
        query: Search query
        limit: Max results
    """
    service = get_service()
    datasets = await service.search_datasets(query, limit)
    return {"count": len(datasets), "datasets": datasets}


@app.tool()
async def hf_search_spaces(query: str = "", limit: int = 10) -> dict[str, Any]:
    """Search Hugging Face Spaces.

    Args:
        query: Search query
        limit: Max results
    """
    service = get_service()
    spaces = await service.search_spaces(query, limit)
    return {"count": len(spaces), "spaces": spaces}


@app.tool()
async def hf_inference(model_id: str, inputs: str) -> dict[str, Any]:
    """Run inference on a model.

    Args:
        model_id: Model identifier
        inputs: Input data for the model
    """
    service = get_service()
    return await service.get_inference_api(model_id, inputs)


@app.tool()
async def hf_get_readme(model_id: str) -> dict[str, Any]:
    """Get model README.

    Args:
        model_id: Model identifier
    """
    service = get_service()
    readme = await service.get_model_readme(model_id)
    return {
        "model_id": model_id,
        "readme": readme[:5000] if len(readme) > 5000 else readme,
        "truncated": len(readme) > 5000,
    }


if __name__ == "__main__":
    if not get_hf_api_token():
        logger.warning("HF_API_TOKEN not set - inference will fail")
    app.run(transport="stdio")
