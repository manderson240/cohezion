# Gemma 4 Developer Agent Synthesis

We need answer user asks: "For the Gemma 4 Developer Agent competition ($150k, SWE-bench verified agentic coding), write a self-contained Python function `verify_git_patch_invariants(patch_str: str) -> bool` that checks: 1) patch is non-empty, 2) touches only allowed repository paths, 3) contains valid unified diff headers (--- and +++), and 4) avoids test deletion or truncation. Enclose valid Python code in ```python ```."

Need produce code only likely. Need think about requirements. Need write self-contained Python function. Need infer allowed repository paths? Not specified. Need maybe define constant ALLOWED_REPOSITORY_PATHS? Need robust. We need implement checks. Need avoid test deletion or truncation. Need parse patch. Need maybe use regex. Need ensure valid unified diff headers. Need check non-empty. Need touches only allowed repository paths. Need decide allowed paths. Since not specified, maybe include a set of allowed prefixes like ["src/", "lib/", "app/", "pyproject.toml", "setup.py", "README.md"]? But user didn't specify. Could define ALLOWED_PATHS as parameter? Function signature only patch_str. Need maybe hardcode allowed repository paths as constant. But competition? SWE-bench verified agentic coding likely allowed paths are repo-specific. We can define a default set and mention? But code only. Need maybe use a conservative default: allow any path except tests? But requirement says touches only allowed repository paths. Need define allowed. Could use a set of common source paths and config files, exclude tests. But if patch touches tests, should fail? Requirement 4 avoids test deletion or truncation, not necessarily all test modifications. But allowed repository paths maybe exclude tests? Hmm.

Need parse unified diff. Need check headers. Need avoid test deletion or truncation. "test deletion or truncation" means if a file under test path has deleted lines or file deleted? Need detect deletion of test files or truncation (maybe hunk removing lines from test file). Need maybe check if any hunk in a test file has more deletions than additions? Or any deletion lines in test file? "avoids test deletion or truncation" likely means no deletion of test files and no hunk that deletes lines from test files? Could be stricter: no deletion lines in test files. Need implement.

Need produce self-contained function. Let's design.

Function verify_git_patch_invariants(patch_str: str) -> bool:
- if not patch_str or not patch_str.strip(): return False
- Define ALLOWED_REPOSITORY_PATHS = { ... } maybe as a set of prefixes. Need choose. Could include "src/", "lib/", "app/", "gemma/", "scripts/", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "README.md", "LICENSE", "Makefile", "Dockerfile", ".github/", "docs/"? But "allowed repository paths" maybe should be broad but exclude tests. Could define as a tuple of allowed prefixes. But if patch touches "tests/test_foo.py", should fail allowed paths? Requirement 4 separately avoids test deletion/truncation, but maybe test modifications allowed? In SWE-bench, patches often modify tests? Actually SWE-bench verified tasks require fixing code, not tests. The patch should not modify tests. So allowed paths likely exclude tests. So we can set allowed paths to exclude any path containing "test" or under tests/ directory. But requirement says "touches only allowed repository paths" not "exclude tests". Could define allowed as non-test paths. Need maybe include common source directories.

But maybe better: define ALLOWED_REPOSITORY_PATHS as a set of exact file prefixes or directory prefixes. Since unknown repo, we can allow any path that is not under tests/ and not a test file. But that would be too permissive. The instruction says "touches only allowed repository paths" - maybe they expect a constant list. We can define a set of allowed prefixes like:
ALLOWED_REPOSITORY_PATHS = {
    "src/", "lib/", "app/", "gemma/", "scripts/", "tools/",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "README.md", "LICENSE", "Makefile", "Dockerfile", ".github/",
    "docs/", "config/", "conf/", "assets/", "data/"
}
But this is arbitrary. Could be acceptable for self-contained.

Alternatively, we can make function accept allowed paths via global constant that user can modify. But signature fixed. We can define ALLOWED_REPOSITORY_PATHS at top.

Need parse patch. Unified diff format:
--- a/path
+++ b/path
@@ -l,c +l,c @@
 context
-deleted
+added

Need extract file paths from --- and +++ lines. Need handle /dev/null for new/deleted files. Need check headers: each file section should have --- and +++ lines. Could use regex to find all lines starting with --- and +++. Need ensure at least one pair. Need maybe check that each --- has corresponding +++? Could parse sequentially.

Simpler: use regex to find all file headers:
header_pattern = re.compile(r'^---\s+(\S+)\s*$', re.MULTILINE)
plus_pattern = re.compile(r'^\+\+\+\s+(\S+)\s*$', re.MULTILINE)
Need ensure counts match and each file has both. But could be multiple. Need maybe check that for each --- there is a +++ after it before next ---. Could parse line by line.

Need extract paths: from --- and +++ lines, strip prefixes a/ or b/. Usually --- a/path, +++ b/path. Could be /dev/null. Need handle. Paths may have spaces? Git quotes paths with spaces? In unified diff, paths with spaces are quoted? Actually git diff uses --- a/foo bar? It may quote. But we can assume simple.

Need check allowed paths: for each path from --- and +++ (excluding /dev/null), check if it starts with any allowed prefix or equals allowed file. Also maybe check not test path. Could define is_allowed_path(path) -> bool:
- if path == "/dev/null": return True (not a real path)
- if path starts with "a/" or "b/": strip that prefix.
- if any part of path indicates test: e.g., path contains "/test" or "test_" or "_test" or starts with "tests/" or "test/"? We can exclude.
- Check if path starts with any allowed prefix or equals allowed file.
But if allowed set includes "src/", then "src/foo.py" allowed. If path is "src/foo.py" okay.

Need avoid test deletion or truncation:
- Identify test files: paths that look like tests. Could define is_test_path(path): path contains "/tests/", "/test/", starts with "tests/", "test/", or filename contains "test_" or "_test" or ends with "_test.py" etc.
- For each file section, if it's a test file:
  - If file is deleted (--- path, +++ /dev/null) -> fail.
  - If any hunk has deletion lines (lines starting with '-' not '---') -> fail? That would avoid any deletion in test file. "truncation" could mean removing lines. So yes, fail if any deletion line in test file.
  - Also maybe if hunk has more deletions than additions? But any deletion is bad.
- Could also check if file content is truncated: maybe if hunk header indicates only deletions? But any deletion line is enough.

Need parse hunks. Could split patch into file sections by lines starting with "diff --git" or by ---/+++ pairs. Simpler: iterate lines, track current file path and whether it's test file. When see --- line, record old path; when see +++ line, record new path; then after headers, when see lines starting with '-' (but not '---') and current file is test, return False. Also if new path is /dev/null and old path is test, fail.

Need ensure valid unified diff headers: at least one --- and +++ line, and each file section has both. Could check that for every --- line there is a subsequent +++ line before next ---. Or simpler: count of --- lines equals count of +++ lines and both >0. But could have --- without +++? That would be invalid. Need more robust.

Could parse line by line:
- Split patch into lines.
- Iterate with index.
- Track seen_header = False, current_old_path = None, current_new_path = None, in_file = False.
- When line starts with "--- ":
   - if current_old_path is not None and current_new_path is None: invalid (previous file missing +++)
   - set current_old_path = parse path after ---
   - set in_file = True
- When line starts with "+++ ":
   - if current_old_path is None: invalid (+++ without ---)
   - set current_new_path = parse path after +++
   - process file paths: check allowed, test deletion etc.
   - reset current_old_path/current_new_path for next file? Actually after +++ we have both, then we can process. But we need continue to check deletion lines in this file. So keep current file info until next ---.
- When line starts with "@@
