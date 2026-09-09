"""Callers get the ANSWER, whichever channel the backend delivered it in.

Reasoning lands in `content` (as an inline `<think>` block) or in `reasoning_content`, and which
one is NOT a property of the model: it depends on whether `reasoning_format="none"` was sent,
which depends on a substring match in `_THINKING_MODEL_MARKERS`, and which the FLM backend
ignores outright. Measured 2026-08-16 against a llamacpp control, `(content, reasoning)` chars:

    llamacpp Gemma-4-26B   baseline (206, 2474)  ->  arg set (2984, 0)     flag WORKS
    FLM deepseek-r1-8b     baseline (182,  925)  ->  arg set ( 238,  933)  silently IGNORED

So no server-side setting can normalise the fleet, and it has to happen client-side.
`gauntlet.py:201-202` already had the pattern; `gaia_adapter` had copied only the first of its
two lines, so a guarded lane returned its entire chain of thought to every caller.
"""

from __future__ import annotations

import pytest

from cohezion.inference.gaia_adapter import _answer_only


class TestDelimiterQuotedAsContent:
    """A delimiter QUOTED in prose is not markup, and must not truncate the text.

    Found by the normaliser corrupting an adversarial review OF ITSELF: two of three review
    lanes returned only the text following the `<channel|>` they were discussing, destroying
    their own preamble. The failure presented as the model "stopping early", which is why it
    took a direct test to locate — the output looked truncated by generation, not by us.

    Anything that reviews markup-handling code, quotes a protocol, or explains a delimiter hits
    this. The rule: a closer is markup only when its OPENER precedes it.
    """

    def test_quoted_closer_without_opener_is_not_stripped(self) -> None:
        """DISCRIMINATING: an unpaired-closer implementation returns only 'which is...'."""
        raw = "Analysis: the code splits on <channel|> which is\nFINDING: real answer here"
        assert _answer_only(raw, "") == raw

    def test_review_text_quoting_the_closer_survives_intact(self) -> None:
        raw = "===FINAL===\nFINDING: splitting on <channel|> is unsafe\nSEVERITY: high"
        got = _answer_only(raw, "")
        assert got.startswith("===FINAL===")
        assert "SEVERITY: high" in got

    def test_paired_markup_is_still_stripped(self) -> None:
        """The guard must not disable the real feature: opener BEFORE closer is markup."""
        raw = "<|channel>thought reasoning here<channel|>THE ANSWER"
        assert _answer_only(raw, "") == "THE ANSWER"

    def test_opener_after_closer_is_not_markup(self) -> None:
        """Order matters. Both tokens present but out of order is prose, not a channel."""
        raw = "the closer <channel|> comes before the opener <|channel> in this sentence"
        assert _answer_only(raw, "") == raw

    def test_quoted_think_closer_already_safe(self) -> None:
        """_THINK_RE requires BOTH tags, so this path never had the bug. Guards a regression."""
        raw = "The bug is that </think> appears alone, so nothing should be removed."
        assert _answer_only(raw, "") == raw


class TestInlineThinkStripped:
    def test_think_block_removed_answer_kept(self) -> None:
        assert _answer_only("<think>weighing options</think>VERDICT: no", "") == "VERDICT: no"

    def test_multiline_and_case_insensitive(self) -> None:
        got = _answer_only("<THINK>\nline one\nline two\n</Think>\n  ANSWER  ", "")
        assert got == "ANSWER"

    def test_multiple_blocks_all_removed(self) -> None:
        assert _answer_only("<think>a</think>X<think>b</think>Y", "") == "XY"

    def test_plain_content_untouched(self) -> None:
        assert _answer_only("just an answer", "") == "just an answer"


class TestNeverReturnsEmpty:
    """The guard `gauntlet.py:202` lacks. These separate this implementation from that one."""

    def test_content_that_is_entirely_thinking_is_not_emptied(self) -> None:
        """DISCRIMINATING: a bare `_THINK_RE.sub("", text)` returns "" here.

        Empty content is defect 4dd925b0081f -- the exact failure the reasoning_format guard
        exists to prevent -- so a cleanup step that can produce it has reintroduced the bug it
        was meant to tidy up after. Returning the raw thinking at least shows the caller what
        happened.
        """
        raw = "<think>I thought about it and never answered</think>"
        assert _answer_only(raw, "") == raw

    def test_whitespace_only_remainder_is_not_emptied(self) -> None:
        """Trailing whitespace after the block still leaves nothing, so the guard must fire.

        Asserts NON-EMPTY rather than byte-equality with the input: `content.strip()` runs
        before the regex, so the returned text is whitespace-normalised. Pinning the exact
        bytes would test that incidental detail instead of the invariant that matters.
        """
        got = _answer_only("<think>reasoning</think>   \n  ", "")
        assert got, "guard must fire -- an all-thinking reply must not normalise to empty"
        assert "reasoning" in got


class TestGemmaChannelFormat:
    """Gemma-4 uses `<|channel>thought ... <channel|>answer`, NOT `<think>`.

    Added after a live boundary check: 16 unit tests passed while a real guarded lane still
    returned 3214 chars of raw reasoning, because every fixture used the delimiter that was
    already known. Stub tests cannot discover a format you have not seen.
    """

    def test_channel_reasoning_removed(self) -> None:
        raw = "<|channel>thought\nweighing it up\n<channel|>No, it is not sufficient."
        assert _answer_only(raw, "") == "No, it is not sufficient."

    def test_last_channel_wins(self) -> None:
        """DISCRIMINATING: Gemma drafts the answer inside its reasoning before the real one.

        An implementation splitting on the FIRST delimiter returns the draft plus everything
        after it; only splitting on the LAST one isolates the final answer.
        """
        raw = "<|channel>thought reasoning<channel|>draft answer<channel|>FINAL"
        assert _answer_only(raw, "") == "FINAL"

    def test_channel_with_no_answer_after_it_is_not_emptied(self) -> None:
        raw = "<|channel>thought all reasoning and nothing after<channel|>"
        got = _answer_only(raw, "")
        assert got, "guard must fire for the channel format too, not just <think>"
        assert "reasoning" in got

    def test_unrecognised_channel_variant_returned_as_is(self) -> None:
        """A family whose delimiter we do not know must degrade to today's behaviour."""
        raw = "<|somefuture>thinking about it, the answer is yes"
        assert _answer_only(raw, "") == raw


class TestUnclosedThinkLeftAlone:
    def test_unclosed_block_is_not_stripped(self) -> None:
        """Budget ran out before `</think>`. With no closing tag there is no way to tell where
        reasoning stops and an answer starts, so removing anything would be a guess."""
        raw = "<think>ran out of budget mid-thought"
        assert _answer_only(raw, "") == raw


class TestChannelFallback:
    def test_empty_content_falls_back_to_reasoning(self) -> None:
        assert _answer_only("", "the reasoning is all there is") == "the reasoning is all there is"

    def test_whitespace_content_falls_back(self) -> None:
        assert _answer_only("   \n ", "fallback text") == "fallback text"

    def test_content_wins_when_both_present(self) -> None:
        """The split-channel case: reasoning is separate, content is the answer, take content."""
        assert _answer_only("ANSWER", "separate chain of thought") == "ANSWER"

    def test_think_stripped_from_the_fallback_too(self) -> None:
        """A backend can put a think block in reasoning_content while content is empty."""
        assert _answer_only("", "<think>x</think>recovered answer") == "recovered answer"

    def test_both_empty_returns_empty(self) -> None:
        """Nothing to normalise. Empty in, empty out -- do not fabricate a value."""
        assert _answer_only("", "") == ""


@pytest.mark.parametrize(
    ("content", "reasoning", "expected"),
    [
        ("<think>a</think>B", "ignored", "B"),
        ("B", "", "B"),
        ("", "B", "B"),
        ("<think>only</think>", "", "<think>only</think>"),
    ],
)
def test_table(content: str, reasoning: str, expected: str) -> None:
    assert _answer_only(content, reasoning) == expected
