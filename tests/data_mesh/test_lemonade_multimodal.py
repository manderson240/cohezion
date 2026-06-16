"""Unit tests for LemonadeMultimodalClient and CorpusQualityConsumer TTS wiring.

All tests are fully mocked — no real network calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# LemonadeMultimodalClient
# ---------------------------------------------------------------------------


class TestSpeak:
    def test_speak_returns_bytes(self):
        """speak() POSTs to /v1/audio/speech and returns response bytes."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"audio"
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.return_value = mock_resp
            mock_client.get.return_value = MagicMock(status_code=200)

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.speak("hello world")

        assert result == b"audio"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/v1/audio/speech"
        payload = call_args[1]["json"]
        assert payload["model"] == "kokoro-v1"
        assert payload["input"] == "hello world"

    def test_speak_non_fatal_on_error(self):
        """speak() returns b"" when the HTTP call raises an exception."""
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.side_effect = ConnectionError("router down")

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.speak("hello")

        assert result == b""

    def test_speak_voice_and_speed_forwarded(self):
        """speak() passes voice and speed to the JSON payload."""
        mock_resp = MagicMock()
        mock_resp.content = b"audio"
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.return_value = mock_resp

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            client.speak("test", voice="bm_lewis", speed=1.2)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["voice"] == "bm_lewis"
        assert payload["speed"] == 1.2


class TestTranscribe:
    def test_transcribe_sends_multipart(self):
        """transcribe() uses multipart/form-data with a 'file' field."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"text": "hello there"}

        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.return_value = mock_resp

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.transcribe(b"\x00\x01\x02", filename="clip.wav")

        assert result == "hello there"
        call_kwargs = mock_client.post.call_args[1]
        assert "files" in call_kwargs
        assert "file" in call_kwargs["files"]
        # file field is a (filename, bytes, content-type) tuple
        fname, data, ctype = call_kwargs["files"]["file"]
        assert fname == "clip.wav"
        assert data == b"\x00\x01\x02"
        assert ctype == "audio/wav"

    def test_transcribe_non_fatal_on_error(self):
        """transcribe() returns '' when HTTP raises."""
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.side_effect = OSError("timeout")

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.transcribe(b"audio")

        assert result == ""


class TestEmbed:
    def test_embed_returns_768d_vectors(self):
        """embed() returns list of 768-dim float vectors from the response data."""
        vector = [0.1] * 768
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vector}]}

        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.return_value = mock_resp

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.embed(["test sentence"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert len(result[0]) == 768
        assert result[0][0] == pytest.approx(0.1)

    def test_embed_non_fatal_on_error(self):
        """embed() returns [] when HTTP raises."""
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.post.side_effect = RuntimeError("oops")

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            result = client.embed(["text"])

        assert result == []


class TestIsAvailable:
    def test_is_available_true_on_200(self):
        """is_available() returns True when GET /v1/models returns 200."""
        mock_resp = MagicMock(status_code=200)

        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.get.return_value = mock_resp

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            assert client.is_available() is True

        # Verify the 2s timeout override
        call_kwargs = mock_client.get.call_args[1]
        assert call_kwargs.get("timeout") == 2.0

    def test_is_available_false_on_exception(self):
        """is_available() returns False when the router is unreachable."""
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.get.side_effect = ConnectionError("refused")

            from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient

            client = LemonadeMultimodalClient()
            assert client.is_available() is False


# ---------------------------------------------------------------------------
# make_multimodal_client factory
# ---------------------------------------------------------------------------


class TestMakeMultimodalClient:
    def test_returns_client_when_available(self):
        """Factory returns a LemonadeMultimodalClient when router is up."""
        with patch("cohezion.data_mesh.lemonade_multimodal.LemonadeMultimodalClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_cls.return_value = mock_instance

            from cohezion.data_mesh.lemonade_multimodal import make_multimodal_client

            result = make_multimodal_client()

        assert result is mock_instance

    def test_make_multimodal_client_returns_none_when_down(self):
        """Factory returns None when the router is unreachable."""
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            # GET /v1/models raises — router is down
            mock_client.get.side_effect = ConnectionError("refused")

            from cohezion.data_mesh.lemonade_multimodal import make_multimodal_client

            result = make_multimodal_client()

        assert result is None


# ---------------------------------------------------------------------------
# CorpusQualityConsumer TTS wiring
# ---------------------------------------------------------------------------


class TestTTSAnnounceOnAugmentation:
    @pytest.mark.asyncio
    async def test_tts_announce_on_augmentation(self):
        """speak() is called with the right message when tts_announce=True and results come back."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        consumer = CorpusQualityConsumer(tts_announce=True)

        # Stub the augmentor — returns 3 fake results
        mock_augmentor = MagicMock()
        mock_augmentor.augment_batch.return_value = ["r1", "r2", "r3"]
        consumer._augmentor = mock_augmentor

        # Stub the multimodal client
        mock_mm = MagicMock()
        mock_mm.speak.return_value = b""
        consumer._mm_client = mock_mm

        # Build a minimal quality alert event
        from cohezion.core.event_bus import Event, EventType

        event = Event(
            type=EventType.DATA_PRODUCT_QUALITY_ALERT,
            source="test",
            payload={"skill_filter": "my-skill", "limit": 3},
        )
        await consumer._handle_quality_alert(event)

        mock_mm.speak.assert_called_once()
        spoken = mock_mm.speak.call_args[0][0]
        assert "3 traces improved" in spoken
        assert "my-skill" in spoken

    @pytest.mark.asyncio
    async def test_tts_not_called_when_disabled(self):
        """speak() is NOT called when tts_announce=False (default)."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        consumer = CorpusQualityConsumer()  # default: tts_announce=False

        mock_augmentor = MagicMock()
        mock_augmentor.augment_batch.return_value = ["r1", "r2"]
        consumer._augmentor = mock_augmentor

        mock_mm = MagicMock()
        consumer._mm_client = mock_mm

        from cohezion.core.event_bus import Event, EventType

        event = Event(
            type=EventType.DATA_PRODUCT_QUALITY_ALERT,
            source="test",
            payload={"skill_filter": None},
        )
        await consumer._handle_quality_alert(event)

        mock_mm.speak.assert_not_called()

    @pytest.mark.asyncio
    async def test_tts_not_called_on_empty_results(self):
        """speak() is NOT called when augment_batch returns zero results."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        consumer = CorpusQualityConsumer(tts_announce=True)

        mock_augmentor = MagicMock()
        mock_augmentor.augment_batch.return_value = []
        consumer._augmentor = mock_augmentor

        mock_mm = MagicMock()
        consumer._mm_client = mock_mm

        from cohezion.core.event_bus import Event, EventType

        event = Event(
            type=EventType.DATA_PRODUCT_QUALITY_ALERT,
            source="test",
            payload={"skill_filter": "empty-skill"},
        )
        await consumer._handle_quality_alert(event)

        mock_mm.speak.assert_not_called()

    @pytest.mark.asyncio
    async def test_tts_announce_all_skills_when_no_filter(self):
        """speak() message uses 'all skills' when skill_filter is None."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        consumer = CorpusQualityConsumer(tts_announce=True)

        mock_augmentor = MagicMock()
        mock_augmentor.augment_batch.return_value = ["r1"]
        consumer._augmentor = mock_augmentor

        mock_mm = MagicMock()
        mock_mm.speak.return_value = b""
        consumer._mm_client = mock_mm

        from cohezion.core.event_bus import Event, EventType

        event = Event(
            type=EventType.DATA_PRODUCT_QUALITY_ALERT,
            source="test",
            payload={},
        )
        await consumer._handle_quality_alert(event)

        spoken = mock_mm.speak.call_args[0][0]
        assert "all skills" in spoken

    @pytest.mark.asyncio
    async def test_tts_failure_does_not_propagate(self):
        """A TTS error must not cause _handle_quality_alert to raise."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        consumer = CorpusQualityConsumer(tts_announce=True)

        mock_augmentor = MagicMock()
        mock_augmentor.augment_batch.return_value = ["r1"]
        consumer._augmentor = mock_augmentor

        mock_mm = MagicMock()
        mock_mm.speak.side_effect = RuntimeError("audio device missing")
        consumer._mm_client = mock_mm

        from cohezion.core.event_bus import Event, EventType

        event = Event(
            type=EventType.DATA_PRODUCT_QUALITY_ALERT,
            source="test",
            payload={"skill_filter": "test-skill"},
        )
        # Should NOT raise
        await consumer._handle_quality_alert(event)
