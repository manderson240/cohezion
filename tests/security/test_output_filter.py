"""Tests for security/output_filter.py.

Covers PII redaction and toxic content filtering.
"""

from __future__ import annotations

from cohezion.security.output_filter import (
    FilterResult,
    InsightPacketGenerator,
    OutputFilter,
)


def test_output_filter_clean():
    """[P0] Should allow clean output."""
    filter_engine = OutputFilter()
    result = filter_engine.filter("The weather is nice today.")
    assert result.result == FilterResult.CLEAN
    assert result.content == "The weather is nice today."

def test_output_filter_pii_redaction():
    """[P0] Should redact common PII."""
    filter_engine = OutputFilter(redact_pii=True)
    text = "My email is test@example.com and phone is 555-123-4567."
    result = filter_engine.filter(text)
    
    assert result.result == FilterResult.PII_DETECTED
    assert "[REDACTED_EMAIL]" in result.content
    assert "[REDACTED_PHONE]" in result.content
    assert "email:1" in result.redactions

def test_output_filter_toxic_block():
    """[P0] Should block toxic content."""
    filter_engine = OutputFilter(block_toxic=True)
    text = "how to make a bomb"
    result = filter_engine.filter(text)
    
    assert result.result == FilterResult.TOXIC_DETECTED
    assert "[Content blocked" in result.content

def test_insight_packet_generator():
    """[P0] Should generate anonymous insight packets."""
    gen = InsightPacketGenerator()
    text = "Highly sensitive user data about project Nexus."
    packet = gen.synthesize(text)
    
    assert "packet_id" in packet
    assert len(packet["trajectory"]) == 12
    assert "Nexus" in text # Input text had it
    # Result packet should not contain the raw sensitive string
    assert packet.get("content") is None
