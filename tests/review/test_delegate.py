"""V-model tests for the delegated review path.

Structural tests cover parsing and fail-soft behaviour. The discriminating tests target the
two properties that a plausible-but-wrong implementation would break silently:

  1. Prompt PREFIX STABILITY. Reordering the prompt sections so the diff comes first still
     produces a correct-looking review, but destroys KV-cache reuse across files. Nothing in
     the output would reveal it, so it is asserted directly.
  2. PER-FILE FAILURE ISOLATION. An implementation that lets one exception escape loses the
     entire review; the happy path cannot tell the difference.
"""

from __future__ import annotations

import pytest

from cohezion.review.delegate import (
    DelegatedReview,
    ReviewFile,
    build_prompt,
    parse_preview,
    run_review,
)


PREVIEW = """# Files (2 reviewable / 2 total)

- mode: commit
- commit: 62efde8e6
- background: feat(knowledge): semantic corpus retrieval

Two corpora were embedded with NO consumer.
- total_insertions: 292
- total_deletions: 0

  - `src/cohezion/knowledge/corpus.py` [added] +141/-0
  - `src/cohezion/mcp/knowledge_server.py` [modified] +46/-0
"""


def _review() -> DelegatedReview:
    return DelegatedReview(
        mode="commit",
        ref="abc123",
        background="why this change exists",
        rules="RULE ONE\nRULE TWO\n" + ("padding rule text. " * 200),
        files=[
            ReviewFile("a.py", "added", 10, 0),
            ReviewFile("b.py", "modified", 5, 2),
        ],
    )


class TestParsePreview:
    def test_parses_files_metadata_and_background(self):
        r = parse_preview(PREVIEW)
        assert r.mode == "commit"
        assert r.ref == "62efde8e6"
        assert [f.path for f in r.files] == [
            "src/cohezion/knowledge/corpus.py",
            "src/cohezion/mcp/knowledge_server.py",
        ]
        assert r.files[0].status == "added"
        assert (r.files[0].insertions, r.files[0].deletions) == (141, 0)
        assert r.files[1].status == "modified"
        assert "semantic corpus retrieval" in r.background
        # DISCRIMINATING: background is multi-line prose; an implementation that stops at the
        # first newline drops the body and silently ships a reviewer with less context.
        assert "NO consumer" in r.background
        # ...but it must NOT swallow the metadata lines that follow it.
        assert "total_insertions" not in r.background

    def test_empty_input_yields_empty_review_not_error(self):
        r = parse_preview("")
        assert r.files == [] and r.mode == "" and r.background == ""


class TestPromptConstruction:
    def test_prompt_contains_rules_background_and_diff(self):
        r = _review()
        p = build_prompt(r, r.files[0], "DIFF-BODY-HERE")
        assert "RULE ONE" in p and "why this change exists" in p and "DIFF-BODY-HERE" in p

    def test_prompt_prefix_is_stable_across_files(self):
        """DISCRIMINATING: the cache-reuse property.

        Every file's prompt must share a byte-identical prefix containing the whole rule
        corpus. An implementation that puts the diff first, or interpolates the filename into
        the header, produces reviews that read fine but re-prefill thousands of tokens per
        file. Only a direct assertion catches that.
        """
        r = _review()
        p1 = build_prompt(r, r.files[0], "diff one")
        p2 = build_prompt(r, r.files[1], "diff two")

        common = 0
        for c1, c2 in zip(p1, p2):
            if c1 != c2:
                break
            common += 1

        assert r.rules in p1[:common], "rule corpus must fall inside the shared prefix"
        assert common > len(r.rules), (
            f"shared prefix is only {common} chars but the rules alone are {len(r.rules)} — "
            "the stable sections are not leading the prompt, so KV reuse is lost"
        )

    def test_diff_is_last_so_it_cannot_split_the_prefix(self):
        r = _review()
        p = build_prompt(r, r.files[0], "TAIL-MARKER")
        assert p.rstrip().endswith("TAIL-MARKER")


class TestRunReview:
    def test_reviews_every_file_and_keys_by_path(self):
        r = _review()
        out = run_review(r, chat_fn=lambda p: "no defects", diff_fn=lambda path: f"diff {path}")
        assert set(out) == {"a.py", "b.py"}
        assert out["a.py"] == "no defects"

    def test_diff_fn_receives_each_path(self):
        r = _review()
        seen: list[str] = []

        def diff_fn(path: str) -> str:
            seen.append(path)
            return "d"

        run_review(r, chat_fn=lambda p: "ok", diff_fn=diff_fn)
        assert seen == ["a.py", "b.py"]

    def test_one_file_failing_does_not_lose_the_others(self):
        """DISCRIMINATING: partial results beat a lost review.

        A wrong implementation lets the exception propagate; every assertion about the happy
        path still passes, and the failure only shows up in production on a bad file.
        """
        r = _review()

        def chat_fn(prompt: str) -> str:
            if "a.py" in prompt:
                raise RuntimeError("model timeout")
            return "clean"

        out = run_review(r, chat_fn=chat_fn, diff_fn=lambda p: "d")
        assert out["b.py"] == "clean", "the healthy file must still be reviewed"
        assert out["a.py"].startswith("ERROR:")


class TestFailSoft:
    def test_collect_returns_empty_review_when_ocr_missing(self, monkeypatch):
        import cohezion.review.delegate as mod

        monkeypatch.setattr(mod, "_OCR_BIN", "definitely-not-a-real-binary-xyz")
        r = mod.collect(commit="deadbeef")
        assert r.files == []

    def test_rules_not_fetched_when_no_files(self, monkeypatch):
        """No files means nothing to rule on; a second subprocess would be pure waste."""
        import cohezion.review.delegate as mod

        calls: list[list[str]] = []

        def fake_run(args, cwd=None):
            calls.append(args)
            return ""

        monkeypatch.setattr(mod, "_run_ocr", fake_run)
        mod.collect(commit="deadbeef")
        assert len(calls) == 1 and calls[0][:2] == ["delegate", "preview"]


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
