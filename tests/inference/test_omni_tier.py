"""Live-validation tests for OmniTier (LMX-Omni-52B-Halo client-side orchestrator).

These hit the real lemonade OmniRouter + the 4 component models. Marked as live;
skip in CI without lemonade on :13305 / :8008. Run with:
  .venv/bin/python -m pytest tests/inference/test_omni_tier.py -v

Unit-only tests (no network) are NOT mocked here — the orchestrator is too
thin between its sub-tiers to mock profitably. The unit-style tests live
in the "imports" / "dataclass" / "tool_schemas" tests below that don't touch HTTP.
"""

from __future__ import annotations

import socket

import pytest

from cohezion.inference.omni_tier import (
    LMX_OMNI_TOOLS,
    TOOL_ANALYZE_IMAGE,
    TOOL_EDIT_IMAGE,
    TOOL_GENERATE_IMAGE,
    TOOL_TEXT_TO_SPEECH,
    OmniRequest,
    OmniResult,
    OmniTier,
    ToolCallLog,
    build_omni_tier,
)


def lemonade_router_reachable(host: str = "localhost", port: int = 13305) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def lemonade_kokoro_reachable(host: str = "localhost", port: int = 8008) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


LIVE = pytest.mark.skipif(
    not lemonade_router_reachable() or not lemonade_kokoro_reachable(),
    reason="lemonade OmniRouter :13305 and/or kokoro :8008 not reachable",
)


# ---- Pure-unit tests (no network) ------------------------------------------


def test_omni_tier_default_wiring() -> None:
    """All three sub-tiers instantiate with the right ports.

    As of 2026-06-10: TTS, image gen, and STT ALL route through the
    OmniRouter (:13305). The legacy :8008 kokoro port is no longer used.
    """
    t = OmniTier()
    assert t.port == 13305
    assert t.planner_model == "Qwen3.6-35B-A3B-MTP-GGUF"
    assert t.image_tier.port == 13305
    assert t.stt_tier.port == 13305
    assert t.tts_tier.port == 13305


def test_omni_tier_custom_port() -> None:
    t = OmniTier(port=13000)
    assert t.image_tier.port == 13000
    assert t.stt_tier.port == 13000


def test_omni_tier_base_url_kwarg() -> None:
    """base_url kwarg overrides the port-derived URL (D refactor)."""
    t = OmniTier(base_url="http://remote-host:9999")
    assert t._base_url == "http://remote-host:9999"
    assert t._chat_url == "http://remote-host:9999/v1/chat/completions"
    assert t.port == 9999


def test_omni_tier_factory_base_url() -> None:
    """build_omni_tier passes base_url through to OmniTier."""
    t = build_omni_tier(base_url="http://custom:8080")
    assert t._base_url == "http://custom:8080"


def test_omni_tier_factory() -> None:
    t = build_omni_tier()
    assert isinstance(t, OmniTier)
    assert t.port == 13305


def test_tool_schemas_have_five_tools() -> None:
    """The 5 LMX-Omni tool schemas are the canonical set from lemonade-sdk."""
    assert len(LMX_OMNI_TOOLS) == 5
    names = {t["function"]["name"] for t in LMX_OMNI_TOOLS}
    assert names == {
        "generate_image",
        "edit_image",
        "text_to_speech",
        "transcribe_audio",
        "analyze_image",
    }


def test_tool_schemas_match_lemonade_sdk_canonical() -> None:
    """Tool definitions must match lemonade-sdk/toolDefinitions.json verbatim.
    Planners are aligned to these exact names; custom schemas get hallucinated."""
    for schema in LMX_OMNI_TOOLS:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"
        # The 4 tools that have user input all require a 'prompt' or 'input' field
    assert "prompt" in TOOL_GENERATE_IMAGE["function"]["parameters"]["properties"]
    assert "prompt" in TOOL_EDIT_IMAGE["function"]["parameters"]["properties"]
    assert "input" in TOOL_TEXT_TO_SPEECH["function"]["parameters"]["properties"]
    assert "image_url" in TOOL_ANALYZE_IMAGE["function"]["parameters"]["properties"]


def test_omni_request_defaults() -> None:
    req = OmniRequest(prompt="hi")
    assert req.user_audio is None
    assert req.user_image is None
    assert req.max_iterations == 6
    assert req.planner_model == "Qwen3.6-35B-A3B-MTP-GGUF"
    assert req.image_model == "Flux-2-Klein-9B-GGUF"
    assert req.tts_model == "kokoro-v1"
    assert req.asr_model == "Whisper-Large-v3-Turbo"


def test_omni_result_ok_property() -> None:
    r_ok = OmniResult(
        text="hello",
        images=[],
        audio=None,
        transcript=None,
        tool_calls=[],
        iterations=1,
        total_latency_ms=100.0,
        planner_model="x",
        error=None,
    )
    assert r_ok.ok is True

    r_err = OmniResult(
        text="",
        images=[],
        audio=None,
        transcript=None,
        tool_calls=[],
        iterations=1,
        total_latency_ms=100.0,
        planner_model="x",
        error="boom",
    )
    assert r_err.ok is False


def test_tool_call_log_construction() -> None:
    log = ToolCallLog(
        tool_name="generate_image",
        arguments={"prompt": "apple"},
        result_summary="ok",
        latency_ms=0.0,
        artefact_kind="image",
    )
    assert log.tool_name == "generate_image"
    assert log.artefact_kind == "image"
    assert log.error is None


def test_omni_result_save_helpers(tmp_path) -> None:
    r = OmniResult(
        text="hi",
        images=[b"\x89PNG\r\n\x1a\n"],
        audio=b"MP3BYTES",
        transcript=None,
        tool_calls=[],
        iterations=1,
        total_latency_ms=10.0,
        planner_model="x",
    )
    img_path = tmp_path / "out.png"
    audio_path = tmp_path / "out.mp3"
    r.save_image(str(img_path), 0)
    r.save_audio(str(audio_path))
    assert img_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert audio_path.read_bytes() == b"MP3BYTES"


def test_omni_result_save_image_index_error() -> None:
    r = OmniResult(
        text="hi",
        images=[],
        audio=None,
        transcript=None,
        tool_calls=[],
        iterations=1,
        total_latency_ms=10.0,
        planner_model="x",
    )
    with pytest.raises(ValueError, match="no image at index"):
        r.save_image("/tmp/x.png", 0)


def test_omni_result_save_audio_none() -> None:
    r = OmniResult(
        text="hi",
        images=[],
        audio=None,
        transcript=None,
        tool_calls=[],
        iterations=1,
        total_latency_ms=10.0,
        planner_model="x",
    )
    with pytest.raises(ValueError, match="no audio"):
        r.save_audio("/tmp/x.mp3")


# ---- PrefixAligner wiring structural tests (no network) -------------------


def test_omni_tier_has_prefix_aligner() -> None:
    """OmniTier must have a _prefix_aligner instance (structural guard)."""
    t = OmniTier()
    from cohezion.inference.context_engineering import PrefixAligner

    assert isinstance(t._prefix_aligner, PrefixAligner)


def test_omni_tier_system_prompt_normalized() -> None:
    """_build_initial_messages must return a normalized (no double-spaces) system prompt.

    Discriminating: a wrong implementation without PrefixAligner would
    preserve any double-spaces from LMX_OMNI_SYSTEM_PROMPT.format().
    """
    t = OmniTier()
    req = OmniRequest(prompt="Draw a cat.")
    msgs = t._build_initial_messages(req)
    system_content = msgs[0]["content"]
    assert msgs[0]["role"] == "system"
    assert "  " not in system_content, "system prompt must not contain double-spaces"
    assert "\t" not in system_content, "system prompt must not contain tabs"


def test_omni_tier_system_prompt_stable_across_calls() -> None:
    """Identical OmniRequest → identical system prompt (KV cache stability)."""
    t = OmniTier()
    req = OmniRequest(prompt="irrelevant")
    msgs1 = t._build_initial_messages(req)
    msgs2 = t._build_initial_messages(req)
    assert msgs1[0]["content"] == msgs2[0]["content"]


# ---- Live (network) tests --------------------------------------------------


@LIVE
@pytest.mark.asyncio
async def test_omni_text_only_no_tool_call() -> None:
    """Pure text prompt with no tool call should return planner text only."""
    tier = OmniTier()
    req = OmniRequest(prompt="Reply with the single word: OK. Nothing else.")
    r = await tier.run(req)
    assert r.error is None, f"omni failed: {r.error}"
    assert "OK" in r.text or "ok" in r.text.lower()


@LIVE
@pytest.mark.asyncio
async def test_omni_generate_image_end_to_end() -> None:
    """Single generate_image call: should produce a real PNG artefact."""
    tier = OmniTier()
    req = OmniRequest(
        prompt="Generate an image of a red apple on a wooden table. "
        "Do not add any other text. Just generate the image.",
        max_iterations=3,
    )
    r = await tier.run(req)
    assert r.error is None, f"omni failed: {r.error}"
    assert len(r.images) == 1, f"expected 1 image, got {len(r.images)}"
    assert r.images[0][:8] == b"\x89PNG\r\n\x1a\n", "not a valid PNG"
    assert any(t.tool_name == "generate_image" for t in r.tool_calls)


@LIVE
@pytest.mark.asyncio
async def test_omni_text_to_speech_end_to_end() -> None:
    """Single text_to_speech call: should produce a real audio artefact."""
    tier = OmniTier()
    req = OmniRequest(
        prompt='Use the text_to_speech tool to say exactly: "Hello from Strix Halo." '
        "Do not add any other text.",
        max_iterations=3,
    )
    r = await tier.run(req)
    assert r.error is None, f"omni failed: {r.error}"
    assert r.audio is not None, "no audio in result"
    # MP3 starts with ID3 or 0xFF 0xFB
    assert r.audio[:3] == b"ID3" or r.audio[:2] == b"\xff\xfb"
    assert any(t.tool_name == "text_to_speech" for t in r.tool_calls)


@LIVE
@pytest.mark.asyncio
async def test_omni_multi_tool_chain() -> None:
    """Multi-tool chain: generate + edit produces 2 images in one run."""
    tier = OmniTier()
    req = OmniRequest(
        prompt="First, generate an image of a blue sports car. "
        "Then, edit that image to make the car red. "
        "Do not add any other text.",
        max_iterations=5,
    )
    r = await tier.run(req)
    assert r.error is None, f"omni failed: {r.error}"
    tool_names = [t.tool_name for t in r.tool_calls]
    assert "generate_image" in tool_names
    assert "edit_image" in tool_names
    assert len(r.images) == 2
