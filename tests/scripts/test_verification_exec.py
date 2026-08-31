"""Tests for scripts/ci/verification_exec.py — the harness.md verification executor.

These are DISCRIMINATING, not smoke tests. Each one fails against the most plausible wrong
implementation, named per test. Three of them pin bugs the gate produced on its own first
runs, because a doc linter that invents findings is worse than no linter: the team turns it
off within a week and the real drift goes back to being invisible.

The classification is the product here, not the pass/fail count. "This command never
compiled" and "this command ran and its assertion failed" are opposite diagnoses -- one
sends you to the doc, the other to the code -- so every test below asserts the STATUS, never
merely that something was reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
# Same mechanism as tests/scripts/test_dormancy_scan.py. Deliberately NOT
# spec_from_file_location + exec_module: that leaves the module absent from sys.modules, and
# @dataclass resolves its annotations via sys.modules[cls.__module__], so importing this
# particular script that way dies at collection with an opaque NoneType AttributeError.
_SCRIPTS_CI_DIR = REPO / "scripts" / "ci"
if str(_SCRIPTS_CI_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_CI_DIR))

import verification_exec as vx  # noqa: E402


def status_of(doc: str) -> str:
    """Audit a one-block fixture and return its single status."""
    rep = vx.audit(doc, interp=sys.executable)
    assert len(rep.results) == 1, f"expected exactly one result, got {len(rep.results)}"
    return rep.results[0].status


class TestClassificationIsTheProduct:
    """Each failure mode must be told apart from the others, not pooled into FAIL."""

    def test_uncompilable_snippet_is_syntax_not_fail(self):
        # Discriminating: an implementation that runs everything and reports the exit code
        # returns FAIL here. FAIL means "it ran and the invariant is false"; the truth is
        # that this command has NEVER executed, so the invariant was never verified once.
        # This is the LM3 class -- `assert` inside a comprehension, live in harness.md for
        # months. The leading token `assert` is what proves it is broken Python rather than
        # an unknown shell program.
        assert status_of("- **Verification**: `assert [x for x in range(3) assert x]`") == "SYNTAX"

    def test_failing_assertion_is_assert_not_stale_ref(self):
        assert status_of("- **Verification**: `import sys; assert 1 == 2`") == "ASSERT"

    def test_missing_symbol_is_stale_ref_not_assert(self):
        # Discriminating: pooling every non-zero exit into one bucket cannot separate
        # "the code moved" (fix the doc) from "the invariant is violated" (fix the code).
        doc = "- **Verification**: `from cohezion.nope_missing import Gone; assert Gone`"
        assert status_of(doc) == "STALE_REF"

    def test_prose_in_command_position_is_prose_not_stale_ref(self):
        # harness.md W3/W4 verbatim in shape: it reads like a command but binds no `result`,
        # so no interpreter can ever run it. Discriminating: a runner without the AST check
        # executes it, gets NameError, and files it as STALE_REF -- sending a reader to
        # hunt for a renamed symbol that was never referenced.
        doc = '- **Verification**: `result.metrics["suggested_tier"] in {"npu", "igpu"}`'
        assert status_of(doc) == "PROSE"

    def test_real_check_still_passes(self):
        # Negative control. Without it, a gate that reported every block as broken would
        # satisfy every other test in this class.
        assert (
            status_of("- **Verification**: `import sys; assert sys.version_info >= (3, 13)`")
            == "PASS"
        )


class TestExtractorBlindnessIsLoud:
    """V1: a block the parser cannot read must be REPORTED, never dropped."""

    def test_unparseable_block_yields_a_result(self):
        # Discriminating: the natural `if not m: continue` makes a parser bug invisible --
        # every block it fails to read simply vanishes and the summary goes green. The
        # first throwaway probe written for this work did exactly that, twice.
        rep = vx.audit("- **Verification**: covered by the section above", interp=sys.executable)
        assert len(rep.results) == 1
        assert rep.results[0].status == "UNPARSED"

    def test_external_dependency_is_skipped_with_a_reason(self):
        # An unreachable port must never be scored as a pass, and never as a failure either.
        doc = "- **Verification**: `curl -s http://localhost:13305/v1/models`"
        rep = vx.audit(doc, interp=sys.executable)
        assert rep.results[0].status == "SKIP"
        assert rep.results[0].detail, "a skip without a reason is indistinguishable from a bug"


class TestFalsePositiveRegressionPins:
    """Bugs this gate produced against real harness.md. A scanner that invents findings
    gets disabled, and then the drift it existed to catch is invisible again."""

    def test_multiline_python_keeps_its_newlines(self):
        # `" ".join(cmd.split())` is the obvious normalisation and it manufactures a
        # SyntaxError out of any multi-line `python -c` script -- a false positive
        # indistinguishable from the genuine "never executable" finding.
        doc = '- **Verification**: `uv run python -c "\nimport sys\nassert sys.version_info\n"`'
        assert status_of(doc) == "PASS"

    def test_grep_expecting_empty_passes_on_no_match(self):
        # grep's exit code is a PREDICATE. S4 ("no hardcoded URLs") passes when grep exits
        # 1; assuming exit 0 == pass inverts it and reports a clean invariant as broken.
        # Scoped to pyproject.toml deliberately: a fixture that greps the tree containing
        # the fixture matches its own source.
        doc = '- **Verification**: `grep "no_such_token_here" pyproject.toml` must return empty'
        assert status_of(doc) == "PASS"

    def test_grep_expecting_matches_passes_on_match(self):
        doc = '- **Verification**: `grep -l "cohezion" pyproject.toml` returns a non-empty result'
        assert status_of(doc) == "PASS"

    def test_grep_without_stated_polarity_abstains(self):
        # Discriminating: guessing a default polarity makes half the verdicts coin flips.
        # An honest abstention beats a 50%-wrong answer on a gate.
        assert status_of('- **Verification**: `grep -r "anything" pyproject.toml`') == "SKIP"


class TestInterpreterResolution:
    """L367: never `sys.executable` -- under `uv run` in a worktree without its own .venv
    it resolves to whichever venv launched the process, which during this script's own
    development was a DIFFERENT worktree's venv. That verifies the wrong tree silently."""

    def test_resolves_to_a_real_interpreter_and_flags_fallback(self):
        interp, warning = vx.find_interpreter()
        assert Path(interp).exists(), f"resolved interpreter does not exist: {interp}"
        # Discriminating: a resolver that silently substitutes another tree's venv returns
        # an empty warning. Any interpreter outside THIS repo must be announced.
        if not interp.startswith(str(REPO)):
            assert warning, "a foreign interpreter must be reported, not used silently"


class TestAgainstTheRealDocument:
    """The gate must actually work on harness.md, not just on fixtures."""

    @pytest.mark.skipif(
        not (REPO / ".claude" / "rules" / "harness.md").exists(), reason="harness.md absent"
    )
    def test_every_block_produces_exactly_one_result(self):
        text = (REPO / ".claude" / "rules" / "harness.md").read_text(encoding="utf-8")
        blocks = text.count("**Verification**")
        # classify-only: this test asks an ACCOUNTING question, not an execution one, and
        # executing 38 subprocesses to count them took 287s in the first draft. The
        # classify pass still detects UNPARSED, which is the failure mode that would
        # actually break the identity below.
        rep = vx.audit(text, execute=False)
        # Discriminating: this is the accounting identity that makes the summary
        # trustworthy. Any block silently dropped by the extractor breaks it, so the
        # count -- not the pass rate -- is what proves the scan was complete.
        assert len(rep.results) == blocks, (
            f"{blocks} blocks in the doc but {len(rep.results)} results — "
            "the extractor dropped some, so the summary understates the drift"
        )
