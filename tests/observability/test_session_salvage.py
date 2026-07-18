"""Discriminating tests for session_salvage — transcript content extraction.

Companion to test_claude_usage: that module counts TOKENS, this one recovers WORK.
Every test below is written to FAIL against a plausible-but-wrong implementation,
per .claude/rules/verification-depth.md (test the claim, not the component).
"""

from __future__ import annotations

from cohezion.observability.session_salvage import (
    SessionArtifacts,
    extract_session_artifacts,
    unique_writes,
)


def _assistant(*blocks: dict) -> dict:
    return {"type": "assistant", "message": {"content": list(blocks)}}


def _tool_use(name: str, **inp: object) -> dict:
    return {"type": "tool_use", "name": name, "input": inp}


class TestExtraction:
    def test_write_tool_captured_with_path_and_size(self):
        recs = [_assistant(_tool_use("Write", file_path="/a/b.py", content="x = 1\n"))]
        art = extract_session_artifacts(recs)
        assert len(art.file_writes) == 1
        w = art.file_writes[0]
        assert w.path == "/a/b.py"
        assert w.tool == "Write"
        assert w.n_bytes == len("x = 1\n")

    def test_edit_tool_also_captured(self):
        """Discriminating: an impl that only handles Write returns 0 here."""
        recs = [_assistant(_tool_use("Edit", file_path="/a/c.py", old_string="a", new_string="bb"))]
        art = extract_session_artifacts(recs)
        assert [w.path for w in art.file_writes] == ["/a/c.py"]
        assert art.file_writes[0].tool == "Edit"
        # Edit size is the NEW content, not the old
        assert art.file_writes[0].n_bytes == len("bb")

    def test_bash_is_a_command_not_a_file_write(self):
        """Discriminating: an impl treating every tool_use as a write miscounts."""
        recs = [_assistant(_tool_use("Bash", command="git status"))]
        art = extract_session_artifacts(recs)
        assert art.file_writes == []
        assert art.bash_commands == ["git status"]

    def test_tool_results_are_not_mistaken_for_user_prompts(self):
        """Discriminating: tool_result entries arrive as type=user, and real ones carry a
        sibling text block. Without the _is_tool_result guard, that sibling text is
        harvested as if the human had typed it — poisoning the salvage summary with tool
        output. The mixed-block shape below is what makes this test bite: a payload of a
        bare tool_result alone would pass either way (see _text_of), which is precisely
        the placebo-test trap this asserts against."""
        recs = [
            {"type": "user", "message": {"content": "please fix the parser"}},
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                        {"type": "text", "text": "ERROR: build failed on line 42"},
                    ]
                },
            },
        ]
        art = extract_session_artifacts(recs)
        assert art.user_prompts == ["please fix the parser"]

    def test_slash_command_invocations_extracted(self):
        recs = [
            {
                "type": "user",
                "message": {"content": "<command-name>/doctor</command-name>"},
            }
        ]
        art = extract_session_artifacts(recs)
        assert art.commands_invoked == ["doctor"]

    def test_malformed_records_are_skipped_not_fatal(self):
        recs = [
            {},
            {"type": "assistant"},
            {"type": "assistant", "message": {}},
            {"type": "assistant", "message": {"content": "not-a-list"}},
            _assistant(_tool_use("Write", file_path="/ok.py", content="1")),
        ]
        art = extract_session_artifacts(recs)
        assert [w.path for w in art.file_writes] == ["/ok.py"]

    def test_session_metadata_captured(self):
        recs = [
            {
                "type": "assistant",
                "sessionId": "s-1",
                "cwd": "/repo",
                "timestamp": "2026-07-18T10:00:00Z",
                "message": {"content": []},
            }
        ]
        art = extract_session_artifacts(recs)
        assert art.session_id == "s-1"
        assert art.cwd == "/repo"


class TestUniqueWrites:
    """unique_writes isolates the ONLY content transcripts hold that git does not:
    files whose transcript content differs from what is on disk now."""

    def _art(self, *writes: tuple[str, str]) -> SessionArtifacts:
        recs = [_assistant(_tool_use("Write", file_path=p, content=c)) for p, c in writes]
        return extract_session_artifacts(recs)

    def test_write_matching_disk_is_not_unique(self, tmp_path):
        f = tmp_path / "same.py"
        f.write_text("kept = 1\n")
        art = self._art((str(f), "kept = 1\n"))
        assert unique_writes(art) == []

    def test_write_differing_from_disk_is_unique(self, tmp_path):
        """Discriminating: an impl checking only path-existence returns [] here,
        missing the case that matters most — work that was later overwritten."""
        f = tmp_path / "changed.py"
        f.write_text("current = 2\n")
        art = self._art((str(f), "original = 1\n"))
        assert [w.path for w in unique_writes(art)] == [str(f)]

    def test_write_to_vanished_file_is_unique(self, tmp_path):
        art = self._art((str(tmp_path / "gone.py"), "lost = 1\n"))
        assert len(unique_writes(art)) == 1

    def test_latest_write_wins_for_same_path(self, tmp_path):
        """A session that writes the same file 3 times should surface ONE candidate
        (the final state), not three."""
        f = tmp_path / "iter.py"
        art = self._art((str(f), "v1"), (str(f), "v2"), (str(f), "v3"))
        uniq = unique_writes(art)
        assert len(uniq) == 1
        assert uniq[0].content == "v3"
