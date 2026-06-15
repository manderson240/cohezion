"""Tests for PrefixAligner (KV cache alignment) in context_engineering.py."""

from __future__ import annotations

from cohezion.inference.context_engineering import PrefixAligner


class TestPrefixAlignerStability:
    """PrefixAligner must produce identical output for semantically equivalent inputs."""

    def test_whitespace_normalization(self):
        """Extra spaces/tabs → single space after align."""
        aligner = PrefixAligner()
        result = aligner.align("You  are   a   helpful\t\t assistant.")
        assert "  " not in result
        assert "\t" not in result

    def test_same_input_stable(self):
        """Identical system prompts → identical output."""
        aligner = PrefixAligner()
        p1 = aligner.align("You are a helpful assistant.")
        p2 = aligner.align("You are a helpful assistant.")
        assert p1 == p2

    def test_whitespace_variant_stable(self):
        """Whitespace variants of the same text → same aligned output."""
        aligner = PrefixAligner()
        p1 = aligner.align("You are a helpful assistant.")
        p2 = aligner.align("You  are  a  helpful  assistant.")
        assert p1 == p2

    def test_context_bullets_sorted(self):
        """Context bullets are sorted for KV stability regardless of insertion order."""
        aligner = PrefixAligner()
        p1 = aligner.align("Base.", context_bullets=["B info", "A info", "C info"])
        p2 = aligner.align("Base.", context_bullets=["C info", "A info", "B info"])
        assert p1 == p2

    def test_duplicate_bullets_removed(self):
        """Duplicate context bullets are deduplicated."""
        aligner = PrefixAligner()
        p1 = aligner.align("Base.", context_bullets=["A info"])
        p2 = aligner.align("Base.", context_bullets=["A info", "A info", "A info"])
        assert p1 == p2

    def test_empty_bullets_skipped(self):
        """Empty/whitespace bullets are ignored."""
        aligner = PrefixAligner()
        p1 = aligner.align("Base.", context_bullets=["A info"])
        p2 = aligner.align("Base.", context_bullets=["A info", "", "  "])
        assert p1 == p2


class TestPrefixAlignerTruncation:
    """PrefixAligner respects max_prefix_chars without splitting words."""

    def test_short_prompt_not_truncated(self):
        result = PrefixAligner(max_prefix_chars=512).align("Short.")
        assert result == "Short."

    def test_long_prompt_truncated(self):
        aligner = PrefixAligner(max_prefix_chars=20)
        result = aligner.align("This is a rather long system prompt that should be truncated.")
        assert len(result) <= 20

    def test_truncation_at_word_boundary(self):
        aligner = PrefixAligner(max_prefix_chars=10)
        result = aligner.align("Hello world foo bar")
        # Should cut at a space, not mid-word
        assert not result.endswith(" ")
        words = result.split()
        # Every word in result should be a complete word from the original
        for word in words:
            assert word in ["Hello", "world", "foo", "bar"]


class TestPrefixAlignerPayload:
    """align_payload modifies system message in chat completions dict."""

    def test_existing_system_message_aligned(self):
        aligner = PrefixAligner()
        payload = {
            "messages": [
                {"role": "system", "content": "You  are  helpful."},
                {"role": "user", "content": "Hi"},
            ]
        }
        result = aligner.align_payload(payload)
        assert result["messages"][0]["content"] == "You are helpful."

    def test_context_bullets_appended_to_system(self):
        aligner = PrefixAligner()
        payload = {
            "messages": [
                {"role": "system", "content": "Base."},
                {"role": "user", "content": "Query"},
            ]
        }
        result = aligner.align_payload(payload, context_bullets=["Fact A", "Fact B"])
        sys_msg = result["messages"][0]["content"]
        assert "Fact A" in sys_msg
        assert "Fact B" in sys_msg

    def test_no_system_with_bullets_prepends(self):
        aligner = PrefixAligner()
        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        result = aligner.align_payload(payload, context_bullets=["Info"])
        assert result["messages"][0]["role"] == "system"
        assert "Info" in result["messages"][0]["content"]

    def test_payload_returns_same_dict(self):
        """align_payload mutates and returns the same dict (not a copy)."""
        aligner = PrefixAligner()
        payload = {"messages": [{"role": "system", "content": "Sys"}, {"role": "user", "content": "Q"}]}
        result = aligner.align_payload(payload)
        assert result is payload
