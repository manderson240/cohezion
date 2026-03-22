---
name: ruff-large-static-data
description: |
  Handle ruff formatter collapsing large static data (list/frozenset/dict literals)
  into single lines that cause E501 (line too long) violations.
  Use when: (1) ruff keeps reformatting your multi-line list/frozenset to one line,
  (2) a Python file exceeds 300 lines primarily due to static vocabulary/lookup data,
  (3) ruff --fix makes E501 violations worse by collapsing literals.
  Common contexts: NLP stopword lists, vocabulary tables, operation mappings, enum lookup dicts.
author: Claude Code
version: 1.0.0
---

# Ruff Large Static Data

## Problem

Ruff's formatter aggressively normalizes list and frozenset literals. When you have
a large static data set (e.g. a 100-word stopword list), ruff may expand it to one
item per line (making files huge) or collapse it to a single line (causing E501
"line too long" violations). Re-running `ruff --fix` cycles between these states.

## Context / Trigger Conditions

- File has large vocabulary table, stopword list, or lookup dict
- `ruff check` reports E501 on a list/frozenset literal line
- `ruff format` re-collapses the list after you manually split it
- File size creeps above 300 lines (project hard limit) due to ruff expansion
- You see ruff looping: check → fix → check → same E501 violation again

## Solution

### Option A: String concatenation (best for word lists / stopwords)

Instead of a list or frozenset literal, build the data from string concatenation.
Ruff does NOT collapse string literals across multiple assignment statements:

```python
# WRONG — ruff will collapse this to one line (E501)
STOPWORDS: frozenset[str] = frozenset([
    "a", "an", "the", "and", "or", "but", ...  # 80+ words → E501
])

# RIGHT — ruff leaves multi-assignment strings alone
_SW = "a an the and or but in on at to for of with by from as is it"
_SW += " are was were been have has had do does did will would could"
_SW += " should may might shall can not no nor so yet both either"
STOPWORDS: frozenset[str] = frozenset(_SW.split())
```

### Option B: Extract into a companion module (best for complex tables)

When a file is approaching or exceeding the 300-line limit AND contains large
static data (vocab mappings, templates, lookup dicts), extract the data into a
dedicated module:

```
parser.py       → imports from _vocab.py
_vocab.py       → contains STOPWORDS, OPERATION_VOCAB, COMPLEXITY_BOOSTERS
specifier.py    → imports from _templates.py
_templates.py   → contains _OPERATION_TEMPLATES dict
```

Naming convention: `_<purpose>.py` (underscore prefix = private implementation detail).

This serves double duty:
1. Keeps the main logic file under 300 lines
2. Ruff can format the vocab file however it likes without affecting logic readability

### Option C: `# fmt: skip` or `# fmt: off` (last resort)

```python
STOPWORDS: frozenset[str] = frozenset(["a", "an", "the", ...])  # fmt: skip
```

Avoid this — it disables formatting for the line, which can hide real issues.
Use Option A or B instead.

## Verification

After applying Option A or B:
```bash
uv run ruff check src/cohezion/vibe/ --select E501
uv run ruff format src/cohezion/vibe/ --check
# Both should exit 0 with no violations
```

## Example

Real case from Cohezion Vibe parser (Phase 3, MASFactory architecture):

`src/cohezion/vibe/parser.py` hit 386 lines after ruff expanded the stopword frozenset.

Fix: extracted all static data to `src/cohezion/vibe/_vocab.py`:
- `STOPWORDS` — built with `_SW = "..."; _SW += "..."` string concatenation
- `OPERATION_VOCAB` — dict literal (short enough per line, ruff left it alone)
- `COMPLEXITY_BOOSTERS` / `COMPLEXITY_REDUCERS` — short list literals

Result: `parser.py` dropped from 386 → 169 lines. `_vocab.py` is 126 lines.
Both files clean under `ruff check` and `ruff format --check`.

## References

- Ruff formatter magic trailing comma: https://docs.astral.sh/ruff/formatter/#magic-trailing-comma
- The magic trailing comma (`[item,]`) can force one-item-per-line expansion if you
  want ruff to expand (inverse of this problem).
