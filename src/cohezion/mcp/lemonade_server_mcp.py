"""Lemonade MCP Server — expose local Lemonade models as MCP tools.

A stdio FastMCP bridge that lets premier (cloud) reasoning models invoke the
local Lemonade server (http://localhost:13305 by default) for chat, vision,
image generation, text-to-speech, transcription, and model management.

Environment:
    LEMONADE_BASE_URL   Full base URL of the Lemonade server (default: http://localhost:13305)
    LEMONADE_HOST       Hostname, used only if LEMONADE_BASE_URL is unset (default: localhost)
    LEMONADE_PORT       Port, used only if LEMONADE_BASE_URL is unset (default: 13305)
    MCP_TRANSPORT       "stdio" or "http" (default: stdio)
    MCP_PORT            HTTP server port when transport=http (default: 8362)

Usage:
    uv run python -m cohezion.mcp.lemonade_server_mcp
"""

from __future__ import annotations

import base64
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("lemonade-mcp")

app = FastMCP("lemonade-local")


def _base_url() -> str:
    """Resolve Lemonade base URL from environment."""
    if base := os.getenv("LEMONADE_BASE_URL"):
        return base.rstrip("/")
    host = os.getenv("LEMONADE_HOST", "localhost")
    port = int(os.getenv("LEMONADE_PORT", "13305"))
    return f"http://{host}:{port}"


def _httpx_client() -> httpx.AsyncClient:
    """Create a short-lived async HTTP client."""
    return httpx.AsyncClient(timeout=120.0)


async def _safe_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to Lemonade and return the parsed response or an error dict."""
    url = f"{_base_url()}{path}"
    async with _httpx_client() as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            text = exc.response.text[:400]
            logger.error("Lemonade POST failed: %s %s", exc, text)
            return {"error": f"HTTP {exc.response.status_code}: {text}"}
        except Exception as exc:  # pragma: no cover - real network failures
            logger.error("Lemonade POST error: %s", exc)
            return {"error": str(exc)}


async def _safe_get(path: str) -> dict[str, Any]:
    """GET JSON from Lemonade and return the parsed response or an error dict."""
    url = f"{_base_url()}{path}"
    async with _httpx_client() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            text = exc.response.text[:400]
            return {"error": f"HTTP {exc.response.status_code}: {text}"}
        except Exception as exc:  # pragma: no cover - real network failures
            return {"error": str(exc)}


@app.tool()
async def lemonade_list_models(downloaded_only: bool = False) -> dict[str, Any]:
    """List models registered with the local Lemonade server.

    Args:
        downloaded_only: If True, list only models that are already downloaded.
    """
    params = {"downloaded": "true"} if downloaded_only else None
    async with _httpx_client() as client:
        resp = await client.get(f"{_base_url()}/v1/models", params=params)
        resp.raise_for_status()
        data = resp.json()
    models = data.get("data", [])
    return {
        "count": len(models),
        "models": [{"id": m.get("id"), "object": m.get("object")} for m in models],
        "raw": data,
    }


@app.tool()
async def lemonade_load_model(
    model_name: str,
    ctx_size: int = 16384,
    backend: str = "rocm",
    save_options: bool = True,
) -> dict[str, Any]:
    """Load a model into the local Lemonade server with safe bounded context.

    Always caps ctx_size to avoid the unbounded KV-cache crash vector on heavy
    models (N3 invariant). Use this before chat/vision/image tasks so the model
    is warm and does not auto-load at ctx_size=-1.

    Args:
        model_name: Lemonade model ID (e.g. "Gemma-4-E4B-it-GGUF").
        ctx_size: Maximum context window. Default 16384; clipped to [1024, 32768].
        backend: Backend recipe: "rocm", "vulkan", "cpu", or "flm".
        save_options: Persist recipe options so later loads use the same bounds.
    """
    ctx_size = max(1024, min(32768, ctx_size))
    payload = {
        "model_name": model_name,
        "ctx_size": ctx_size,
        "save_options": save_options,
    }
    if backend:
        payload["llamacpp_backend"] = backend
    return await _safe_post("/v1/load", payload)


@app.tool()
async def lemonade_chat(
    messages: list[dict[str, str]],
    model: str = "Gemma-4-E4B-it-GGUF",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a chat completion against a local Lemonade model.

    Args:
        messages: Conversation history, e.g. [{"role": "user", "content": "..."}].
        model: Lemonade model ID to use.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        tools: Optional OpenAI-style tool definitions for tool-calling models.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    data = await _safe_post("/v1/chat/completions", payload)
    if "error" in data:
        return data
    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    return {
        "content": msg.get("content", ""),
        "role": msg.get("role", "assistant"),
        "tool_calls": msg.get("tool_calls"),
        "model": data.get("model", model),
        "usage": data.get("usage", {}),
        "raw": data,
    }


@app.tool()
async def lemonade_analyze_image(
    image_path: str,
    prompt: str,
    model: str = "Gemma-4-E4B-it-GGUF",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Send an image plus prompt to a local vision-capable Lemonade model.

    Args:
        image_path: Path to the image file on the local filesystem.
        prompt: Question or instruction about the image.
        model: Vision-capable Lemonade model ID.
        max_tokens: Maximum tokens to generate.
    """
    path = Path(image_path)
    if not path.exists():
        return {"error": f"Image file not found: {image_path}"}

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    ext = path.suffix.lower().lstrip(".") or "png"
    mime = f"image/{ext}"
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    return await lemonade_chat(messages, model=model, max_tokens=max_tokens)


@app.tool()
async def lemonade_generate_image(
    prompt: str,
    model: str = "SD-Turbo",
    n: int = 1,
    size: str = "512x512",
    response_format: str = "b64_json",
) -> dict[str, Any]:
    """Generate an image using a local Lemonade image model.

    Args:
        prompt: Text description of the image.
        model: Lemonade image-generation model ID (e.g. "SD-Turbo").
        n: Number of images (server support varies).
        size: Image dimensions "WxH".
        response_format: "b64_json" or "url".
    """
    payload = {
        "prompt": prompt,
        "model": model,
        "n": n,
        "size": size,
        "response_format": response_format,
    }
    data = await _safe_post("/v1/images/generations", payload)
    if "error" in data:
        return data
    return {"images": data.get("data", []), "raw": data}


@app.tool()
async def lemonade_text_to_speech(
    text: str,
    model: str = "kokoro-v1",
    voice: str = "af_bella",
    response_format: str = "mp3",
    speed: float = 1.0,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Synthesize speech using a local Lemonade TTS model.

    Args:
        text: Text to speak.
        model: Lemonade TTS model ID (e.g. "kokoro-v1").
        voice: Voice identifier.
        response_format: Audio format such as "mp3" or "wav".
        speed: Playback speed multiplier.
        output_path: Optional path to write the audio file; otherwise returned as base64.
    """
    payload = {
        "input": text,
        "model": model,
        "voice": voice,
        "response_format": response_format,
        "speed": speed,
    }
    url = f"{_base_url()}/v1/audio/speech"
    async with _httpx_client() as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            audio_bytes = resp.content
        except Exception as exc:  # pragma: no cover
            return {"error": str(exc)}

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    if output_path:
        Path(output_path).write_bytes(audio_bytes)
        return {
            "output_path": output_path,
            "format": response_format,
            "size_bytes": len(audio_bytes),
            "base64_preview": b64_audio[:200] + "..." if len(b64_audio) > 200 else b64_audio,
        }
    return {
        "audio_base64": b64_audio,
        "format": response_format,
        "size_bytes": len(audio_bytes),
    }


@app.tool()
async def lemonade_transcribe_audio(
    audio_path: str,
    model: str = "Whisper-Large-v3-Turbo",
    language: str | None = None,
    response_format: str = "json",
) -> dict[str, Any]:
    """Transcribe audio using a local Lemonade Whisper model.

    Args:
        audio_path: Path to the audio file.
        model: Lemonade Whisper model ID.
        language: Optional language code (e.g. "en").
        response_format: "json", "text", "srt", "vtt", or "verbose_json".
    """
    path = Path(audio_path)
    if not path.exists():
        return {"error": f"Audio file not found: {audio_path}"}

    url = f"{_base_url()}/v1/audio/transcriptions"
    async with _httpx_client() as client:
        try:
            files = {"file": (path.name, path.read_bytes(), f"audio/{path.suffix.lstrip('.')}")}
            data = {"model": model, "response_format": response_format}
            if language:
                data["language"] = language
            resp = await client.post(url, files=files, data=data)
            resp.raise_for_status()
            result = resp.json()
        except Exception as exc:  # pragma: no cover
            return {"error": str(exc)}

    return {
        "text": result.get("text", ""),
        "raw": result,
    }


@app.tool()
async def lemonade_server_status() -> dict[str, Any]:
    """Return the local Lemonade server status and loaded models."""
    status = await _safe_get("/api/v1/status")
    models = await _safe_get("/v1/models")
    return {
        "status": status,
        "models": models.get("data", []),
        "base_url": _base_url(),
    }


def main():
    """Run the Lemonade MCP server."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    logger.info("Lemonade MCP server starting (transport=%s, base_url=%s)", transport, _base_url())
    if transport == "stdio":
        app.run(transport="stdio")
    else:
        port = int(os.getenv("MCP_PORT", "8362"))
        app.run(host="0.0.0.0", port=port, transport="http")


if __name__ == "__main__":
    main()
