---
name: pre-commit-yaml-hooks
description: |
  Fix for invalid YAML in .pre-commit-config.yaml when using inline bash in `entry` fields.
  Use when: (1) "mapping values are not allowed here" YAML scanner error on .pre-commit-config.yaml,
  (2) pre-commit tests fail with yaml.scanner.ScannerError, (3) adding local hooks with complex
  bash commands that contain colons, dollar signs, or semicolons. Root cause: YAML interprets
  unquoted colons as key-value separators inside entry strings.
author: Claude Code
version: 1.0.0
---

# Pre-commit YAML Hooks: Inline Bash Breaks YAML

## Problem

Adding local hooks with inline bash `entry` commands breaks YAML parsing:

```yaml
# THIS BREAKS - colon in bash command confuses YAML parser
- id: my-hook
  entry: bash -c 'for f in "$@"; do echo "ERROR: $f exceeds limit"; done'
```

Error: `yaml.scanner.ScannerError: mapping values are not allowed here`

## Root Cause

YAML treats unquoted `:` as a key-value separator. Inside `entry` strings:
- `echo "ERROR: message"` → YAML sees `ERROR` as a key
- `stat --format=%s` → colon breaks mapping parsing
- Multi-statement bash with semicolons and redirects → similar issues

## Solution

**Option A (preferred): Extract to a Python script**

```yaml
- id: version-consistency
  language: python
  entry: python scripts/hooks/check_version_consistency.py
  pass_filenames: false
  stages: [pre-commit]
```

Then write `scripts/hooks/check_version_consistency.py` with full logic.

**Option B: Simple inline Python (for one-liners without colons)**

```yaml
- id: large-artifact-gate
  language: python
  entry: python -c "import sys,os;[sys.exit(1) for f in sys.argv[1:] if os.path.getsize(f)>52428800]"
  stages: [pre-commit]
```

**Option C: Use `args` instead of embedding in `entry`**

```yaml
- id: size-check
  entry: python scripts/hooks/check_size.py
  args: [--max-mb, "50"]
  stages: [pre-commit]
```

## What NOT To Do

```yaml
# BAD - colon in message, dollar in variable
entry: bash -c 'size=$(stat -f%z "$f"); echo "ERROR: too big"'

# BAD - even wrapping in double quotes doesn't reliably fix it
entry: "bash -c 'echo \"ERROR: too big\"'"
```

## Verification

```bash
python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml')); print('YAML valid')"
```

## Diagnosis Pattern

```bash
# Find the exact line number of the YAML error
python3 -c "
import yaml
try:
    yaml.safe_load(open('.pre-commit-config.yaml'))
except yaml.YAMLError as e:
    print(e)
"
```

The error reports `line N, column M` — look at that line for unquoted colons in bash strings.

## References

- `.pre-commit-config.yaml` in this repo
- `scripts/hooks/check_version_consistency.py` as a working example
