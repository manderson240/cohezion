---
title: YAML Folded Scalar Trap: Folded Blocks Collapse Newlines Into Spaces
date: 2026-02-23
severity: MEDIUM
category: tooling
cost_of_forgetting: "Multi-line strings silently collapsed into single lines; configuration parsing errors or wrong behavior"
tags: [yaml, configuration, parsing, data-format]
status: validated
aspect: knower
neural:
  activation: 0.403
  stage: embryo
  cluster: lessons
---

# Lesson: YAML Folded Scalar Trap: Folded Blocks Collapse Newlines Into Spaces

## Context

During Cohezion configuration file development in February 2026, a multi-line bash script embedded in a YAML configuration file was silently collapsed into a single line. The YAML file used `>` (folded scalar) instead of `|` (literal scalar), causing all newlines in the script to be replaced with spaces. The resulting one-liner was syntactically invalid bash, producing a cryptic error message that pointed to the script content rather than the YAML formatting.

## Problem

YAML has two block scalar styles that look similar but behave very differently:

1. **`>` (folded)**: Collapses newlines into spaces. `"Line 1\nLine 2"` becomes `"Line 1 Line 2\n"`. Intended for prose paragraphs that should flow.
2. **`|` (literal)**: Preserves newlines exactly. `"Line 1\nLine 2"` stays `"Line 1\nLine 2\n"`. Required for code, scripts, and any content where line breaks are semantic.

The confusion is common because both use indentation-based blocks and look nearly identical in the YAML source. The only difference is a single character (`>` vs `|`), but the output is completely different.

## Core Learning

**Use | (literal) for multi-line strings that must preserve newlines. Use > (folded) only when whitespace collapsing is intentional.**

### Pattern
```yaml
# WRONG: folded collapses newlines
description: >
  Line 1
  Line 2
# Result: "Line 1 Line 2\n"

# RIGHT: literal preserves newlines
description: |
  Line 1
  Line 2
# Result: "Line 1\nLine 2\n"
```

## Solution

All multi-line strings in Cohezion YAML configuration files now use `|` (literal) by default. `>` (folded) is reserved for prose descriptions where line wrapping is acceptable. A quick verification command confirms correct parsing:

```bash
python3 -c "import yaml; print(repr(yaml.safe_load(open('config.yaml'))['key']))"
```

## Prevention

- **Default to `|`**: When in doubt, use literal scalars. They are correct for code, scripts, commands, and any structured text.
- **Verify with parsing**: Test YAML files with the `yaml.safe_load` command above to see the actual parsed value
- **Use `>` only for prose**: Descriptions, summaries, and paragraph text where line collapsing is desired

## Cost of Forgetting

- **Silent string corruption**: Multi-line content collapsed into a single line without any error
- **Cryptic downstream errors**: The error appears in the script/command execution, not in YAML parsing
- **Difficult debugging**: The YAML looks correct; the error is in how YAML interprets the `>` character

## Recommendations

### Do
- Use | for multi-line strings where newlines matter
- Test YAML parsing: python3 -c "import yaml; print(yaml.safe_load(open('f.yaml').read()))"

### Don't
- Use > for code snippets in YAML

## Related Concepts

- [[concept-automation]] - YAML configuration errors silently break automated workflows
- [[api-design]] - YAML scalar style choice affects configuration API correctness

## Validation

**Discovered**: Feb 2026 in Cohezion configuration files
**Status**: Validated -- literal scalars now the default for all multi-line YAML content
