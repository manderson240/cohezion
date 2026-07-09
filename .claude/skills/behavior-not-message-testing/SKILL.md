---
name: behavior-not-message-testing
description: Use when writing or reviewing exception tests. The pattern: assert on exception TYPE, not on the message STRING. Discovered in WS1 (PR #218 follow-up) where `assert "default" in str(exc.value)` coupled a test to the implementation; the fix was `pytest.raises(RecipeMisalignment)` with no message check.
when_to_use: |
  - Writing a test that asserts an exception is raised
  - Reviewing a test that uses `assert "..." in str(exc.value)` or `assert exc.value.args[0] == "..."`
  - Debugging a flaky test that broke after a copy-edit to an error message
when_not_to_use: |
  - The error message IS the API contract (i18n, security audit logs,
    user-facing errors). Then assert on the message.
  - You're testing that a string IS or ISN'T in a log output.
decision_tree: |
  Is the test about: "this code raises this EXCEPTION TYPE"
  or "this code emits this MESSAGE"?
  ├─ Exception TYPE → pytest.raises(ExceptionType)  # no message check
  └─ Message       → use sparingly; only when the message is the contract
worked_example: |
  WRONG (couples test to implementation):
    with pytest.raises(RecipeMisalignment) as exc:
        RecipeGuard.assert_aligned(bad_params)
    msg = str(exc.value).lower()
    assert "default" in msg or "unaligned" in msg or "missing" in msg
  # The test breaks if the message changes from "default params are
  # a bug" to "params are unaligned". Both are correct; the test
  # shouldn't care.

  RIGHT (asserts the contract):
    with pytest.raises(RecipeMisalignment):
        RecipeGuard.assert_aligned(bad_params)
  # The test breaks only if the EXCEPTION TYPE changes. That's the
  # contract the caller actually depends on.
anti_patterns:
  - `assert "..." in str(exc.value)` — couples test to message wording
  - `assert exc.value.args[0] == "..."` — couples to format string
  - `assert isinstance(exc.value, SomeError) and "key" in str(exc.value)`
    — the isinstance part is fine; the key check is a smell
  - Snapshot testing the message with `repr()` — same coupling
  - Adding a `match=` regex to `pytest.raises(match=...)` for the sake
    of it. The match arg IS appropriate when the message is the API;
    otherwise it's coupling.
  - Asserting `not str(exc.value)` (the empty check) — that's testing
    the absence of a message, which is a different contract
  - Storing the expected message in a constant and asserting equality.
    "DRY" the coupling, but it's still coupling.
related_skills:
  - compound-build (the build ritual that surfaced this)
  - xfail-strict-bug-bridge-pattern (a related but distinct lesson
    about XPASS marking)
  - prompt-injection-guard (when message checking IS the right thing
    — guarding against injection in error message content)
verification:
  before_landing:
    - `grep -rn "in str(.*exc\|in str(.*err\|exc.value.args" tests/`
      should return ZERO matches
    - Or: `grep -rn "match=" tests/` — `pytest.raises(match=...)` is
      allowed only with a comment explaining why the message IS the contract
  after_landing:
    - `pytest.raises(...)` calls have NO message assertion after them
    - The exception TYPE is the only thing under test
honest_residuals:
  - Some teams use message-matching as a "smoke test" that the
    intended code path ran. This is a different test (a behavioral
    smoke test) — write it as `assert "expected_substring" in caplog.text`
    or `assert mock_logger.warning.call_args` instead.
  - The `match=` arg in `pytest.raises` is fine when the test exists
    to pin the message (e.g. security warnings). The skill applies
    to *default* behavior, not to deliberate message-pinning tests.
version: 1
captured: 2026-06-04
captured_from: cohezion-internal WS1 follow-up to PR #218 (RecipeGuard tests)
