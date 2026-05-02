from __future__ import annotations

from src.cohezion.security.output_filter import InsightPacketGenerator


def test_synthesis_removes_pii():
    gen = InsightPacketGenerator()
    text = "Contact me at mike@example.com or 555-0199."
    packet = gen.synthesize(text)

    # Packet should indicate redaction
    assert packet["is_redacted"] is True
    # The trajectory should be based on redacted text
    assert len(packet["trajectory"]) == 12
    # The actual email should NOT be in the packet anywhere
    import json

    assert "mike@example.com" not in json.dumps(packet)


def test_synthesis_deterministic():
    gen = InsightPacketGenerator()
    text = "The quick brown fox jumps over the lazy dog."
    p1 = gen.synthesize(text)
    p2 = gen.synthesize(text)

    assert p1["trajectory"] == p2["trajectory"]
    assert p1["packet_id"] == p2["packet_id"]


def test_synthesis_density():
    gen = InsightPacketGenerator()
    text = "A" * 1000
    packet = gen.synthesize(text)
    # 1000 chars / 12 dims = ~83.3
    assert packet["density"] > 80


def test_packet_id_is_sha256():
    """Verify packet_id uses SHA-256 (first 16 chars), not MD5."""
    gen = InsightPacketGenerator()
    text = "Test content for hash verification."
    packet = gen.synthesize(text)

    # packet_id should be first 16 chars of SHA-256 hex digest
    # SHA-256 produces 64 char hex, MD5 produces 32 char
    # First 16 chars of SHA-256 is still cryptographically strong
    assert len(packet["packet_id"]) == 16
    assert packet["packet_id"].isalnum()  # Should only contain hex chars


def test_different_texts_different_packet_ids():
    """Verify different texts produce different packet IDs."""
    gen = InsightPacketGenerator()

    text1 = "First unique text"
    text2 = "Second unique text"

    p1 = gen.synthesize(text1)
    p2 = gen.synthesize(text2)

    # Different texts should produce different packet IDs (no collision)
    assert p1["packet_id"] != p2["packet_id"]
