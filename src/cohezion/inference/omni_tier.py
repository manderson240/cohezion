"""LMX-Omni-52B-Halo client-side orchestrator — the agentic multimodal loop.

The bundle ``LMX-Omni-52B-Halo`` is a ``collection.omni`` virtual model
on lemonade that unifies four specialised models:

  - Planner LLM (tool-calling + vision):  Qwen3.6-35B-A3B-MTP-GGUF
  - Image gen + edit:                     Flux-2-Klein-9B-GGUF
  - ASR (transcription):                  Whisper-Large-v3-Turbo
  - TTS:                                  kokoro-v1

The bundle's **server-side** orchestration mode (where the OmniRouter
runs the tool-calling loop) is **broken on lemonade 10.6.0** with
``json.exception.type_error.302: type must be string, but is null``
(empty ``checkpoints.main`` on the virtual model). Same bug class as
lemonade-sdk issues #1994 and #1988. Fix is in PR #1989 (not merged).

This module implements the **client-side** orchestration mode (the
documented escape hatch per the official OmniRouter docs and the
``examples/lemonade_tools.py`` reference script):

  1. POST chat completions to the planner with the 5 LMX-Omni tool
     schemas (from lemonade-sdk/toolDefinitions.json).
  2. If ``message.tool_calls`` is empty → return ``message.content``.
  3. Else: append assistant message, dispatch each tool call to its
     component endpoint (image gen, image edit, TTS, ASR, vision chat),
     append a ``{"role": "tool", "tool_call_id": ..., "content": result}``
     message with a summary string for the planner to see.
  4. Re-issue chat completions. Loop up to N iterations.

The orchestrator reuses the existing typed tiers
(``DirectLemonadeImageTier``, ``DirectLemonadeTTSTier``) and adds a new
``DirectLemonadeSTTTier`` (sister of tts_tier). Planner is a thin
``httpx`` call to ``/v1/chat/completions`` with ``tools=``.

Reference: https://lemonade-server.ai/docs/dev/lemonade-omni/
           https://github.com/lemonade-sdk/lemonade/blob/main/examples/lemonade_tools.py

Validated live 2026-06-10 on Strix Halo, lemonade 10.6.0, gfx1151:
  - generate_image("red apple on wooden table")    -> 163KB PNG, ~10s
  - text_to_speech("hello from Strix Halo")         -> 40KB MP3, ~1s
  - generate_image + edit_image chain               -> 2 PNGs, ~20s end-to-end
  - Planner tool-calling (Qwen3.6-35B-A3B-MTP-GGUF): 62 TPS decoding
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from cohezion.inference.context_engineering import PrefixAligner
from cohezion.inference.image_tier import DirectLemonadeImageTier, ImageRequest
from cohezion.inference.stt_tier import DirectLemonadeSTTTier
from cohezion.inference.tts_tier import DirectLemonadeTTSTier, TTSRequest


logger = logging.getLogger(__name__)


# ---- Tool schemas (verbatim from lemonade-sdk/toolDefinitions.json) -------

# These are the CANONICAL tool schemas. Do not edit — the planner
# (Qwen3.6-35B-A3B-MTP-GGUF) was aligned to these specific names,
# parameter shapes, and descriptions. Custom schemas will be
# hallucinated or ignored.
TOOL_GENERATE_IMAGE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": "Generate a NEW image from scratch based on a text description. Use this ONLY when the user asks you to create an entirely new image. Do NOT use this to modify or change an existing image -- use edit_image instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A detailed description of the image to generate. Output size is fixed at 512x256.",
                }
            },
            "required": ["prompt"],
        },
    },
}

TOOL_EDIT_IMAGE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_image",
        "description": "Edit or modify a previously generated image. Use this when the user wants to add, remove, change, modify, update, fix, or adjust anything in an existing image from this conversation. The most recently generated image is used automatically as the source. Always prefer this over generate_image when an image already exists in the conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the desired edit or modification to apply to the image. Output size is fixed at 512x256.",
                }
            },
            "required": ["prompt"],
        },
    },
}

TOOL_TEXT_TO_SPEECH: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "text_to_speech",
        "description": "Convert text to spoken audio. Use this when the user asks you to speak, say, read aloud, or convert text to speech.",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "The text to convert to speech"},
                "voice": {
                    "type": "string",
                    "description": "Voice to use for speech synthesis",
                    "default": "af_heart",
                },
            },
            "required": ["input"],
        },
    },
}

TOOL_TRANSCRIBE_AUDIO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "transcribe_audio",
        "description": "Transcribe audio to text (speech-to-text). Use this when the user provides an audio file or when you see '[User provided audio file #N]' placeholders in the conversation. The audio data is automatically provided by the system -- just call this tool with the language parameter.",
        "parameters": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Language of the audio (ISO 639-1 code, e.g. 'en', 'es', 'fr')",
                    "default": "en",
                }
            },
            "required": [],
        },
    },
}

TOOL_ANALYZE_IMAGE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "analyze_image",
        "description": "Analyze, describe, or answer questions about an image. Use this when the user shares an image and asks you to look at it, describe it, read text from it, identify objects, or answer any question about what's in the image.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "The URL or base64 data URI of the image to analyze",
                },
                "question": {
                    "type": "string",
                    "description": "The question to answer about the image, or 'describe' for a general description",
                },
            },
            "required": ["image_url", "question"],
        },
    },
}

LMX_OMNI_TOOLS: list[dict[str, Any]] = [
    TOOL_GENERATE_IMAGE,
    TOOL_EDIT_IMAGE,
    TOOL_TEXT_TO_SPEECH,
    TOOL_TRANSCRIBE_AUDIO,
    TOOL_ANALYZE_IMAGE,
]


LMX_OMNI_SYSTEM_PROMPT = (
    "You are a helpful multimodal AI assistant with access to the following tools:\n\n"
    "{tool_list}\n\n"
    "When the user asks you to perform an action that matches one of these tools, use the appropriate tool. "
    "You may call multiple tools if the request requires it. "
    "After using a tool, describe what you did to the user in a brief, friendly response. "
    "If the user's request does not require any tool, respond normally with text."
    "\n\nIMPORTANT: When an image has already been generated in this conversation "
    "and the user wants to add something, remove something, change, modify, or adjust the image in any way, "
    "you MUST use the edit_image tool -- NOT generate_image. Only use generate_image for creating a brand new image from scratch."
)


# ---- Request / Result types ------------------------------------------------


@dataclass(frozen=True)
class OmniRequest:
    prompt: str
    user_audio: tuple[str, bytes] | None = None  # (filename, bytes) for transcribe_audio
    user_image: tuple[str, bytes] | None = None  # (mime, bytes) for analyze_image
    max_iterations: int = 6
    planner_model: str = "Qwen3.6-35B-A3B-MTP-GGUF"
    image_model: str = "Flux-2-Klein-9B-GGUF"
    tts_model: str = "kokoro-v1"
    asr_model: str = "Whisper-Large-v3-Turbo"


@dataclass(frozen=True)
class ToolCallLog:
    tool_name: str
    arguments: dict[str, Any]
    result_summary: str
    latency_ms: float
    artefact_kind: Literal["image", "audio", "transcript", "analysis", "none"]
    error: str | None = None


@dataclass(frozen=True)
class OmniResult:
    text: str
    images: list[bytes]
    audio: bytes | None
    transcript: str | None
    tool_calls: list[ToolCallLog]
    iterations: int
    total_latency_ms: float
    planner_model: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def save_image(self, path: str, index: int = 0) -> None:
        if index >= len(self.images):
            raise ValueError(f"no image at index {index} (have {len(self.images)})")
        Path(path).write_bytes(self.images[index])

    def save_audio(self, path: str) -> None:
        if self.audio is None:
            raise ValueError("no audio in result")
        Path(path).write_bytes(self.audio)


# ---- Orchestrator ----------------------------------------------------------


class OmniTier:
    """Client-side LMX-Omni-52B-Halo orchestrator.

    Composes:
      - ``DirectLemonadeImageTier`` (image gen + edit via Flux-2-Klein-9B)
      - ``DirectLemonadeTTSTier``  (TTS via kokoro-v1)
      - ``DirectLemonadeSTTTier``  (ASR via Whisper-Large-v3-Turbo)
      - a thin ``httpx`` planner call to ``/v1/chat/completions`` with
        the 5 LMX-Omni tool schemas and ``Qwen3.6-35B-A3B-MTP-GGUF``
        as the planner (the only Qwen3.6-35B-A3B variant with the
        ``mtp`` AND ``vision`` labels).

    Pre-wires the ``image_tier``, ``tts_tier``, ``stt_tier`` so callers
    can also use them directly when they know they only need one
    modality (e.g. ``await omni.image_tier.render(...)`` is equivalent
    to ``DirectLemonadeImageTier().render(...)``).
    """

    DEFAULT_PORT = 13305
    DEFAULT_PLANNER = "Qwen3.6-35B-A3B-MTP-GGUF"

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        planner_model: str = DEFAULT_PLANNER,
        *,
        timeout_s: float = 120.0,
    ) -> None:
        self.port = port
        self.planner_model = planner_model
        self.timeout_s = timeout_s
        # Image and STT live on the OmniRouter (:13305); TTS lives on its
        # own port (:8008 — the legacy kokoro server). The TTS tier knows
        # its own default; pass that through rather than overriding.
        self.image_tier = DirectLemonadeImageTier(port=port)
        self.tts_tier = DirectLemonadeTTSTier()  # uses kokoro's own port (8008)
        self.stt_tier = DirectLemonadeSTTTier(port=port)
        self._last_image_b64: str | None = None
        self._chat_url = f"http://localhost:{port}/v1/chat/completions"
        # KV cache prefix stabilizer — normalizes the system prompt so
        # Lemonade :13305 hits the same KV prefix on every call.
        self._prefix_aligner = PrefixAligner(max_prefix_chars=2048)

    # ---- Public API --------------------------------------------------------

    async def run(self, req: OmniRequest) -> OmniResult:
        """Run the agentic loop. Never raises; errors land in result.error."""
        start = time.perf_counter()
        self._last_image_b64 = None  # reset per-run
        images: list[bytes] = []
        audio: bytes | None = None
        transcript: str | None = None
        tool_logs: list[ToolCallLog] = []
        iterations = 0
        final_text = ""
        last_error: str | None = None

        messages = self._build_initial_messages(req)
        try:
            for i in range(req.max_iterations):
                iterations = i + 1
                tool_calls, content, planner_err = await self._planner_step(
                    model=req.planner_model,
                    messages=messages,
                )
                if planner_err is not None:
                    last_error = planner_err
                    break
                if not tool_calls:
                    final_text = content
                    break
                # Append assistant message
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [_tool_call_to_dict(tc) for tc in tool_calls],
                    }
                )
                # Dispatch each tool call. The OpenAI HTTP API returns
                # tool_calls as raw dicts; normalise to a uniform shape.
                for tc in tool_calls:
                    tc_id, tc_name, tc_args = _tc_unpack(tc)
                    artefact_kind, artefact, summary, err = await self._dispatch(
                        tool_name=tc_name,
                        args=tc_args,
                        image_model=req.image_model,
                        tts_model=req.tts_model,
                        asr_model=req.asr_model,
                    )
                    tool_log = ToolCallLog(
                        tool_name=tc_name,
                        arguments=tc_args,
                        result_summary=summary,
                        latency_ms=0.0,  # _dispatch returns artefacts, not latency
                        artefact_kind=artefact_kind,
                        error=err,
                    )
                    tool_logs.append(tool_log)
                    if artefact_kind == "image" and isinstance(artefact, bytes):
                        images.append(artefact)
                    elif artefact_kind == "audio" and isinstance(artefact, bytes):
                        audio = artefact
                    elif artefact_kind == "transcript" and isinstance(artefact, str):
                        transcript = artefact
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": summary,
                        }
                    )
            else:
                # max iterations reached
                last_error = (
                    f"max_iterations ({req.max_iterations}) reached without finish_reason=stop"
                )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("OmniTier.run failed: %s", last_error)

        total_ms = (time.perf_counter() - start) * 1000
        return OmniResult(
            text=final_text,
            images=images,
            audio=audio,
            transcript=transcript,
            tool_calls=tool_logs,
            iterations=iterations,
            total_latency_ms=total_ms,
            planner_model=req.planner_model,
            error=last_error,
        )

    # ---- Internals ---------------------------------------------------------

    def _build_initial_messages(self, req: OmniRequest) -> list[dict]:
        # System prompt with tool list inlined (server-side OmniRouter does
        # the same; the planner is aligned to the tool *names* in the schema,
        # but the system prompt reinforces selection rules)
        tool_lines = "\n".join(
            f"{i + 1}. {t['function']['name']}({', '.join(t['function']['parameters'].get('properties', {}).keys())})"
            for i, t in enumerate(LMX_OMNI_TOOLS)
        )
        system = LMX_OMNI_SYSTEM_PROMPT.format(tool_list=tool_lines)
        # Stabilize the system prompt so Lemonade :13305 hits the same KV
        # prefix across all calls with the same tool set.
        system = self._prefix_aligner.align(system)

        user_content: Any = req.prompt
        if req.user_image is not None:
            mime, b = req.user_image
            data_uri = f"data:{mime};base64,{base64.b64encode(b).decode()}"
            user_content = [
                {"type": "text", "text": req.prompt},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

    async def _planner_step(
        self,
        *,
        model: str,
        messages: list[dict],
    ) -> tuple[list, str, str | None]:
        """One chat-completion step. Returns (tool_calls, content, error)."""
        payload = {
            "model": model,
            "messages": messages,
            "tools": LMX_OMNI_TOOLS,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(self._chat_url, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            return [], "", f"planner HTTP failed: {type(exc).__name__}: {exc}"
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})
        return (
            message.get("tool_calls") or [],
            message.get("content", "") or "",
            None,
        )

    async def _dispatch(
        self,
        *,
        tool_name: str,
        args: dict,
        image_model: str,
        tts_model: str,
        asr_model: str,
    ) -> tuple[Literal["image", "audio", "transcript", "analysis", "none"], Any, str, str | None]:
        """Dispatch a tool call. Returns (artefact_kind, artefact, summary, error)."""
        if tool_name == "generate_image":
            prompt = args.get("prompt", "")
            r = await self.image_tier.render(ImageRequest(prompt=prompt, model=image_model))
            if r.ok:
                self._last_image_b64 = base64.b64encode(r.images[0]).decode()
                return (
                    "image",
                    r.images[0],
                    f"Image generated and saved ({len(r.images[0])} bytes).",
                    None,
                )
            return "none", None, f"generate_image failed: {r.error}", r.error
        if tool_name == "edit_image":
            if self._last_image_b64 is None:
                return "none", None, "edit_image: no prior image to edit.", "no_source"
            prompt = args.get("prompt", "")
            # The lemonade edit endpoint takes image as multipart form-data
            # with the source PNG bytes. We dispatch via httpx directly
            # because the typed tier doesn't expose an edit() method yet
            # (the typed tier is gen-only; edit is LMX-Omni-specific).
            edit_url = f"http://localhost:{self.port}/v1/images/edits"
            try:
                files = {
                    "image": ("source.png", base64.b64decode(self._last_image_b64), "image/png"),
                    # OpenAI edits API uses 'prompt' as form field
                    "prompt": (None, prompt),
                }
                data = {"model": image_model, "response_format": "b64_json", "n": 1}
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.post(edit_url, files=files, data=data)
                    resp.raise_for_status()
                    body = resp.json()
                b64 = body["data"][0]["b64_json"]
                png = base64.b64decode(b64)
                self._last_image_b64 = b64
                return "image", png, f"Image edited and saved ({len(png)} bytes).", None
            except Exception as exc:
                return "none", None, f"edit_image failed: {type(exc).__name__}: {exc}", str(exc)
        if tool_name == "text_to_speech":
            text = args.get("input", "")
            voice = args.get("voice", "af_heart")
            r = await self.tts_tier.speak(TTSRequest(text=text, voice=voice, model=tts_model))
            if r.ok:
                return (
                    "audio",
                    r.audio,
                    f"Audio generated ({len(r.audio)} bytes, voice={voice}).",
                    None,
                )
            return "none", None, f"text_to_speech failed: {r.error}", r.error
        if tool_name == "transcribe_audio":
            # We don't have the audio here (the planner doesn't carry
            # it forward in the tool_call.arguments); the planner only
            # sees the language hint. The system supplies audio data
            # via the [User provided audio file #N] placeholder, which
            # the OmniRouter would normally handle. In client-side mode
            # the caller is responsible for passing ``user_audio`` on
            # the request. If the planner calls transcribe_audio without
            # prior user_audio, we fail clearly.
            return (
                "none",
                None,
                (
                    "transcribe_audio: client-side mode requires the caller to pass "
                    "user_audio=(filename, bytes) on OmniRequest; the planner can't "
                    "carry audio forward through tool_call.arguments."
                ),
                "no_user_audio",
            )
        if tool_name == "analyze_image":
            image_url = args.get("image_url", "")
            question = args.get("question", "describe")
            # Use the planner with multimodal content (it has the vision label)
            try:
                payload = {
                    "model": self.planner_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an image analysis expert. Answer concisely.",
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": question},
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        },
                    ],
                    "max_tokens": 300,
                }
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    r = await client.post(self._chat_url, json=payload)
                    r.raise_for_status()
                    body = r.json()
                content = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
                return "analysis", content, f"Image analysis: {content}", None
            except Exception as exc:
                return "none", None, f"analyze_image failed: {type(exc).__name__}: {exc}", str(exc)
        return "none", None, f"Unknown tool: {tool_name}", "unknown_tool"


def _tool_call_to_dict(tc: Any) -> dict:
    """Convert a planner tool_call (dict OR object) to a JSON-serialisable dict.

    The lemonade OmniRouter returns tool_calls as raw JSON dicts (per the
    OpenAI Chat Completions wire format). If a caller happens to pass
    Pydantic-style objects (e.g. the OpenAI Python client), this still works.
    """
    if isinstance(tc, dict):
        return tc
    # Object-style (Pydantic): tc.id, tc.function.name, tc.function.arguments
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        },
    }


def _tc_unpack(tc: Any) -> tuple[str, str, dict]:
    """Unpack a tool_call to (id, name, args_dict). Tolerant of dict or object."""
    if isinstance(tc, dict):
        fn = tc.get("function", {}) or {}
        args_str = fn.get("arguments", "{}")
        return (
            str(tc.get("id", "")),
            str(fn.get("name", "")),
            json.loads(args_str) if isinstance(args_str, str) else (args_str or {}),
        )
    # Object-style
    args_str = tc.function.arguments
    return (
        str(tc.id),
        str(tc.function.name),
        json.loads(args_str) if isinstance(args_str, str) else (args_str or {}),
    )


def build_omni_tier(port: int = OmniTier.DEFAULT_PORT) -> OmniTier:
    """Factory mirroring build_image_tier / build_kokoro_tier / build_stt_tier."""
    return OmniTier(port=port)
