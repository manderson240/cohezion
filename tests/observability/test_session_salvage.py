"""Discriminating tests for session_salvage — transcript content extraction.

Companion to test_claude_usage: that module counts TOKENS, this one recovers WORK.
Every test below is written to FAIL against a plausible-but-wrong implementation,
per .claude/rules/verification-depth.md (test the claim, not the component).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.observability.session_salvage import (
    SessionArtifacts,
    extract_session_artifacts,
    is_ephemeral,
    is_subagent_transcript,
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


class TestUniqueWritesForEdits:
    """An Edit's payload is a FRAGMENT (the replacement span), not a whole file.

    Comparing a fragment against whole-file contents is unconditionally unequal, so every
    Edit was flagged as "work that never landed" — 213 of 305 reported findings (70%) were
    false positives against the real corpus. The earlier tests built only Write records, so
    this entire input class went unexercised.
    """

    def _edit(self, path: str, new_string: str) -> SessionArtifacts:
        return extract_session_artifacts(
            [_assistant(_tool_use("Edit", file_path=path, old_string="OLD", new_string=new_string))]
        )

    def test_edit_that_landed_is_not_unique(self, tmp_path):
        """Discriminating: the edit succeeded and its text is in the file on disk. A
        fragment-vs-whole-file comparison reports this as lost work."""
        f = tmp_path / "landed.py"
        f.write_text("import os\n\n\ndef go():\n    return 2\n")
        assert unique_writes(self._edit(str(f), "return 2")) == []

    def test_edit_that_did_not_land_is_unique(self, tmp_path):
        """The mirror case: the fragment is absent, so the work really is only in the
        transcript. Guards against 'fix' by never flagging Edits at all."""
        f = tmp_path / "reverted.py"
        f.write_text("import os\n\n\ndef go():\n    return 1\n")
        assert [w.path for w in unique_writes(self._edit(str(f), "return 2"))] == [str(f)]

    def test_edit_to_vanished_file_is_unique(self, tmp_path):
        assert len(unique_writes(self._edit(str(tmp_path / "gone.py"), "x = 1"))) == 1

    def test_write_still_uses_exact_comparison(self, tmp_path):
        """A Write payload IS the whole file, so a merely-contained match is not enough."""
        f = tmp_path / "w.py"
        f.write_text("prefix\nx = 1\nsuffix\n")
        art = extract_session_artifacts(
            [_assistant(_tool_use("Write", file_path=str(f), content="x = 1\n"))]
        )
        assert [w.path for w in unique_writes(art)] == [str(f)]


class TestMalformedLeafValues:
    """`.get("text", "")` defaults only when the key is ABSENT. A present-but-null value
    reached str.join and raised, falsifying the 'never raises' contract — and the batch has
    no per-file guard, so one such record in one of 221 transcripts aborted the whole run."""

    def test_null_text_value_does_not_raise(self):
        recs = [{"type": "user", "message": {"content": [{"type": "text", "text": None}]}}]
        assert extract_session_artifacts(recs).user_prompts == []

    def test_non_string_text_values_do_not_raise(self):
        for bad in (123, ["a"], {"k": "v"}, True):
            recs = [{"type": "user", "message": {"content": [{"type": "text", "text": bad}]}}]
            assert extract_session_artifacts(recs).user_prompts == []

    def test_valid_text_still_extracted_alongside_bad(self):
        """Discriminating: guards against 'fixing' this by dropping the branch entirely."""
        recs = [
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "text", "text": None},
                        {"type": "text", "text": "real ask"},
                    ]
                },
            }
        ]
        assert extract_session_artifacts(recs).user_prompts == ["real ask"]


class TestTextBlockExtraction:
    """The list-of-text-blocks branch is live: 17 real prompts arrive in this shape. The
    tool-result test appears to cover it but returns early, so the branch was unexercised —
    mutating it to `return ""` survived the whole suite."""

    def test_text_blocks_in_a_list_are_extracted(self):
        recs = [{"type": "user", "message": {"content": [{"type": "text", "text": "do it"}]}}]
        assert extract_session_artifacts(recs).user_prompts == ["do it"]

    def test_multiple_text_blocks_are_joined(self):
        recs = [
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "text", "text": "first"},
                        {"type": "text", "text": "second"},
                    ]
                },
            }
        ]
        assert extract_session_artifacts(recs).user_prompts == ["first\nsecond"]


class TestClassifiers:
    """is_ephemeral and is_subagent_transcript both survived `return False` mutations.
    The subagent filter is load-bearing: 165 of 221 real transcripts are subagents."""

    def test_ephemeral_paths_detected(self):
        for p in ("/tmp/x.py", "/a/scratchpad/b.md", "/h/.cache/c", "/n/node_modules/d"):
            assert is_ephemeral(p), p

    def test_real_paths_are_not_ephemeral(self):
        for p in ("/home/u/dev/repo/src/a.py", "/opt/thing/b.md"):
            assert not is_ephemeral(p), p

    def test_subagent_transcript_detected(self):
        assert is_subagent_transcript(Path("/p/sess/subagents/agent-a1.jsonl"))

    def test_main_session_is_not_subagent(self):
        assert not is_subagent_transcript(Path("/p/sess.jsonl"))


class TestArtifactAccounting:
    def test_first_and_last_timestamps_differ(self):
        """first_ts must be the FIRST seen, not overwritten by each record."""
        recs = [
            {"type": "assistant", "timestamp": f"2026-07-18T0{i}:00:00Z", "message": {}}
            for i in (1, 2, 3)
        ]
        art = extract_session_artifacts(recs)
        assert art.first_ts.startswith("2026-07-18T01")
        assert art.last_ts.startswith("2026-07-18T03")

    def test_files_touched_dedupes_preserving_order(self):
        art = extract_session_artifacts(
            [
                _assistant(_tool_use("Write", file_path=p, content="c"))
                for p in ("/a.py", "/b.py", "/a.py")
            ]
        )
        assert art.files_touched == ["/a.py", "/b.py"]


class TestNonRegularFiles:
    """unique_writes reads a transcript-supplied path. A planted `/dev/urandom` would be
    read until OOM; a FIFO blocks forever. Non-regular files take the 'only copy' branch."""

    def test_directory_path_does_not_read(self, tmp_path):
        d = tmp_path / "adir"
        d.mkdir()
        art = extract_session_artifacts(
            [_assistant(_tool_use("Write", file_path=str(d), content="x"))]
        )
        assert len(unique_writes(art)) == 1

    def test_device_node_is_not_read(self):
        """Discriminating: an impl calling read_text on /dev/zero never returns."""
        art = extract_session_artifacts(
            [_assistant(_tool_use("Write", file_path="/dev/zero", content="x"))]
        )
        assert len(unique_writes(art)) == 1
