"""Tests for EVO modality handlers — text, audio, image, video."""

import json
import urllib.error
from unittest.mock import MagicMock, patch


def _make_chat_response(content: str, model: str = "Gemma-4-E4B-it-GGUF") -> bytes:
    """Build a minimal OpenAI-compatible chat/completions response."""
    return json.dumps({
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
    }).encode()


def _mock_chat_urlopen(content: str, model: str = "Gemma-4-E4B-it-GGUF"):
    """Return a mock context manager that yields a response with `content`."""
    inner = MagicMock()
    inner.read.return_value = _make_chat_response(content, model)
    cm = MagicMock()
    cm.__enter__.return_value = inner
    cm.__exit__.return_value = False
    return cm


class TestTextModality:
    def test_invoke_returns_modal_result(self):
        from cohezion.evo.modalities import ModalityResult, TextModality

        with patch("urllib.request.urlopen", return_value=_mock_chat_urlopen("Latent coherence improved.")):
            r = TextModality().invoke("EVO step description")

        assert isinstance(r, ModalityResult)
        assert r.modality == "text"

    def test_invoke_success_when_router_responds(self):
        """TextModality returns the LLM synthesis, not the prompt echo."""
        from cohezion.evo.modalities import TextModality

        synthesis = "The latent vector converged toward the HIHO attractor."
        with patch("urllib.request.urlopen", return_value=_mock_chat_urlopen(synthesis)):
            r = TextModality().invoke("synthesize EVO step")

        assert r.success is True
        assert r.output == synthesis

    def test_invoke_calls_chat_completions_endpoint(self):
        """Discriminating: must call /v1/chat/completions, not just echo the prompt."""
        from cohezion.evo.modalities import TextModality

        captured_url = []

        def capture_request(req, **kw):
            captured_url.append(req.full_url)
            return _mock_chat_urlopen("synthesis")

        with patch("urllib.request.urlopen", side_effect=capture_request):
            TextModality().invoke("EVO step")

        assert len(captured_url) == 1
        assert "/v1/chat/completions" in captured_url[0]

    def test_invoke_output_differs_from_prompt_when_llm_works(self):
        """Discriminating: success output is LLM text, not the input prompt echoed back."""
        from cohezion.evo.modalities import TextModality

        prompt = "step: HIHO attractor dynamics"
        synthesis = "Coherence stabilized at the HIHO equilibrium point."
        with patch("urllib.request.urlopen", return_value=_mock_chat_urlopen(synthesis)):
            r = TextModality().invoke(prompt)

        # The critical assertion: output is the LLM reply, not the prompt
        assert r.output == synthesis
        assert r.output != prompt[:200]

    def test_invoke_graceful_failure_when_router_offline(self):
        """Fail-soft: network failure returns structured failure, never raises."""
        from cohezion.evo.modalities import TextModality

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            r = TextModality().invoke("will fail gracefully")

        assert r.modality == "text"
        assert r.success is False
        assert r.error is not None

    def test_invoke_fallback_includes_prompt_on_failure(self):
        """On failure, output is the prompt echo so the pipeline has something to work with."""
        from cohezion.evo.modalities import TextModality

        prompt = "EVO step for testing"
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            r = TextModality().invoke(prompt)

        assert prompt[:200] in r.output or r.output == prompt[:200]

    def test_invoke_does_not_raise_on_failure(self):
        """Constitution §fail-soft — modality errors must never propagate."""
        from cohezion.evo.modalities import TextModality

        with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
            r = TextModality().invoke("anything")  # must not raise

        assert r is not None

    def test_invoke_handles_empty_llm_response(self):
        """Empty LLM content → success=False so the tracer knows synthesis didn't happen."""
        from cohezion.evo.modalities import TextModality

        with patch("urllib.request.urlopen", return_value=_mock_chat_urlopen("")):
            r = TextModality().invoke("EVO step")

        assert r.success is False
        assert r.error is not None

    def test_invoke_truncates_long_prompts_in_request(self):
        """Long prompts are capped at 500 chars in the request payload."""
        from cohezion.evo.modalities import TextModality

        captured_payloads = []

        def capture(req, **kw):
            captured_payloads.append(json.loads(req.data))
            return _mock_chat_urlopen("synthesis")

        with patch("urllib.request.urlopen", side_effect=capture):
            TextModality().invoke("x" * 2000)

        user_content = captured_payloads[0]["messages"][1]["content"]
        assert len(user_content) <= 500


class TestAudioModality:
    def _mock_urlopen(self, audio_data: bytes = b"MP3_AUDIO" * 100):
        mock_inner = MagicMock()
        mock_inner.read.return_value = audio_data
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_inner
        mock_cm.__exit__.return_value = False
        return mock_cm

    def test_invoke_success_when_lemonade_responds(self):
        from cohezion.evo.modalities import AudioModality

        with patch("urllib.request.urlopen", return_value=self._mock_urlopen()):
            r = AudioModality().invoke("synthesize this speech")

        assert r.modality == "audio"
        assert r.success is True
        assert "kokoro-v1" in r.output
        assert r.latency_ms >= 0.0

    def test_invoke_graceful_failure_when_lemonade_offline(self):
        from cohezion.evo.modalities import AudioModality

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            r = AudioModality().invoke("will fail gracefully")

        assert r.modality == "audio"
        assert r.success is False
        assert r.error is not None

    def test_invoke_does_not_raise_on_failure(self):
        """Audio failure must never propagate — Constitution §fail-soft."""
        from cohezion.evo.modalities import AudioModality

        with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
            r = AudioModality().invoke("anything")  # must not raise

        assert r is not None
        assert r.success is False


class TestImageModality:
    def _mock_urlopen(self, url: str = "http://localhost:13305/tmp/img.png"):
        payload = f'{{"data": [{{"url": "{url}"}}]}}'.encode()
        mock_inner = MagicMock()
        mock_inner.read.return_value = payload
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_inner
        mock_cm.__exit__.return_value = False
        return mock_cm

    def test_invoke_success_when_lemonade_responds(self):
        from cohezion.evo.modalities import ImageModality

        with patch("urllib.request.urlopen", return_value=self._mock_urlopen()):
            r = ImageModality(model="SD-Turbo").invoke("latent space visualization")

        assert r.modality == "image"
        assert r.success is True
        assert "localhost:13305" in r.output

    def test_invoke_graceful_failure_when_lemonade_offline(self):
        from cohezion.evo.modalities import ImageModality

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            r = ImageModality().invoke("will fail gracefully")

        assert r.success is False
        assert r.error is not None

    def test_invoke_does_not_raise_on_failure(self):
        from cohezion.evo.modalities import ImageModality

        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            r = ImageModality().invoke("anything")  # must not raise

        assert r is not None


class TestVideoModality:
    def test_invoke_returns_structured_failure(self):
        """Video not in lemonade 10.6.0 — must return structured failure, never raise."""
        from cohezion.evo.modalities import VideoModality

        r = VideoModality().invoke("generate EVO journey video")
        assert r.modality == "video"
        assert r.success is False
        assert r.error is not None
        assert "lemonade" in r.error.lower()

    def test_video_error_mentions_forward_compatibility(self):
        from cohezion.evo.modalities import VideoModality

        r = VideoModality().invoke("anything")
        assert "forward" in r.error.lower() or "video" in r.error.lower()

    def test_video_does_not_raise(self):
        from cohezion.evo.modalities import VideoModality

        VideoModality().invoke("must not raise")  # asserts no exception

    def test_video_catalog_gap_constant_is_descriptive(self):
        from cohezion.evo.modalities import VideoModality

        assert "lemonade" in VideoModality.CATALOG_GAP.lower()


class TestModalityRegistry:
    def test_get_modality_text(self):
        from cohezion.evo.modalities import TextModality, get_modality

        assert isinstance(get_modality("text"), TextModality)

    def test_get_modality_audio(self):
        from cohezion.evo.modalities import AudioModality, get_modality

        assert isinstance(get_modality("audio"), AudioModality)

    def test_get_modality_image(self):
        from cohezion.evo.modalities import ImageModality, get_modality

        assert isinstance(get_modality("image"), ImageModality)

    def test_get_modality_video(self):
        from cohezion.evo.modalities import VideoModality, get_modality

        assert isinstance(get_modality("video"), VideoModality)

    def test_get_modality_unknown_falls_back_to_text(self):
        from cohezion.evo.modalities import TextModality, get_modality

        assert isinstance(get_modality("hologram"), TextModality)
        assert isinstance(get_modality("haptic"), TextModality)
