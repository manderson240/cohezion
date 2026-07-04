---
title: 'Friction Reduction and Test Fixes'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
baseline_commit: 'b000ffd0655dace637da8dfa4b53f514e02a3bd1'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:**
1. In PyTorch 2.5.1, `torchao` fails to import due to missing `torch.int1` attribute. This breaks `transformers` import inside `tests/conftest.py`, falling back to `MagicMock` and causing `test_autoencoder.py` to fail with `unittest.mock.InvalidSpecError`.
2. Multiple core implementation files, skills, and unit tests are untracked on the `feat/stealthskater-bridge` branch.
3. Dynamically generated experiment logs (`tcrao_*.md`) are untracked, bloating the git index which currently exceeds the strict 10k file limit.

**Approach:**
1. Mock `torchao` in `sys.modules` within `tests/conftest.py` before `transformers` is imported to prevent PyTorch compatibility issues.
2. Git stage all missing implementation files, skills, and unit tests on the `feat/stealthskater-bridge` branch.
3. Update `.gitignore` to exclude dynamically generated `tcrao_` experiment logs and other temporary runtime files.

## Boundaries & Constraints

**Always:**
* Maintain exact Python Black formatting (100 line length).
* All tests must pass cleanly.
* Keep the git index clean of transient build/run outputs.

**Ask First:**
* Deleting any files that are not clearly temporary test files.

**Never:**
* Track `node_modules`, large binary artifacts, or dynamically generated experiment logs that belong in databases/vaults.

</frozen-after-approval>

## Code Map

- `tests/conftest.py` -- Global test config/fixtures where transformers is mocked/loaded.
- `.gitignore` -- Root git ignore definitions.

## Tasks & Acceptance

**Execution:**
- [x] `tests/conftest.py` -- Mock `torchao` in `sys.modules` before `transformers` import -- Prevent PyTorch compatibility errors from breaking transformers imports in tests.
- [x] `.gitignore` -- Add ignore patterns for `tcrao_` files and root `tmp_untested_*.py` files -- Avoid git index bloat and keep working tree clean.
- [x] Git Index -- Stage all untracked source, tests, and skills on the active branch -- Ensure completeness of the branch code for checkout and CI runs.

**Acceptance Criteria:**
- Given PyTorch 2.5.1 is active, when `make test-fast` is run, then all 706 unit tests (including `test_autoencoder.py`) pass without mock spec errors.
- Given the `feat/stealthskater-bridge` branch, when `git status` is checked after execution, then no missing core implementation files or test scripts remain untracked.
- Given the `tcrao` orchestrator is run, when new experiment logs are generated, then they are ignored by Git.

## Spec Change Log

*No entries yet.*

## Verification

**Commands:**
- `make test-fast` -- expected: all unit tests pass cleanly.
- `make validate` -- expected: full validation passes.
- `git status` -- expected: clean working tree for untracked code.


## Suggested Review Order

**Global Test Configuration**

- Mock `torchao` to `None` in `sys.modules` to prevent import errors in PyTorch 2.5.1
  [`conftest.py:41`](../../tests/conftest.py#L41)

- Reset `SemanticCache` singleton before/after each test to prevent test state pollution
  [`conftest.py:232`](../../tests/conftest.py#L232)

**Git Configuration**

- Ignore dynamically generated `tcrao_` experiment logs and temporary scan files
  [`.gitignore:303`](../../.gitignore#L303)
