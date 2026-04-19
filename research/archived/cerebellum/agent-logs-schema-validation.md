---
title: "Agent Logs Schema Validation Checklist"
date: 2026-02-11
tags: [pattern, validation, schema, agent-logs, entire.io]
status: active
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 5
  synapse_out: 14
---

## Purpose

Pre-commit validation checklist for `daily/agent-logs/*.md` files to ensure consistency with schema before writing to vault.

**Use**: Daemon validation (Week 2), manual reviews, CI/CD checks

---

## Frontmatter Validation

### Required Fields

- [ ] **date**
  - Format: ISO 8601 with timezone (e.g., "2026-02-11T14:30:00Z")
  - Must be within session timestamp range
  - Fail if: missing, invalid format, wrong timezone

- [ ] **title**
  - Format: "Agent Execution Summary - {session_id}"
  - Must match session_id field
  - Fail if: missing, doesn't contain "Agent Execution Summary"

- [ ] **tags**
  - Must include: [agent, execution, entire.io]
  - Optional: Additional context tags (phase-1, research, etc)
  - Fail if: agent or execution tags missing

- [ ] **status**
  - Must be: "archived"
  - Never other values (active, draft, etc)
  - Fail if: any other value

- [ ] **source**
  - Must be: "entire.io"
  - Identifies data origin for future integrations
  - Fail if: different source

- [ ] **session_id**
  - Format: Matches entire.io session identifier
  - Must be non-empty, alphanumeric + hyphens
  - Fail if: missing, contains special characters

- [ ] **agent_names**
  - Format: YAML array of strings
  - Example: [researcher, implementer, tester]
  - Fail if: not array, empty array, invalid names

### Validation Rules

```python
def validate_frontmatter(metadata):
    errors = []

    # 1. date validation
    if not metadata.get('date'):
        errors.append("Missing required field: date")
    elif not is_iso8601(metadata['date']):
        errors.append(f"Invalid date format: {metadata['date']}")

    # 2. title validation
    if not metadata.get('title'):
        errors.append("Missing required field: title")
    elif "Agent Execution Summary" not in metadata['title']:
        errors.append("Title must contain 'Agent Execution Summary'")
    elif metadata['session_id'] not in metadata['title']:
        errors.append("Title must contain session_id")

    # 3. tags validation
    tags = metadata.get('tags', [])
    if 'agent' not in tags:
        errors.append("Missing required tag: agent")
    if 'execution' not in tags:
        errors.append("Missing required tag: execution")
    if 'entire.io' not in tags:
        errors.append("Missing required tag: entire.io")

    # 4. status validation
    if metadata.get('status') != 'archived':
        errors.append(f"Status must be 'archived', got: {metadata.get('status')}")

    # 5. source validation
    if metadata.get('source') != 'entire.io':
        errors.append(f"Source must be 'entire.io', got: {metadata.get('source')}")

    # 6. session_id validation
    if not metadata.get('session_id'):
        errors.append("Missing required field: session_id")
    elif not is_valid_session_id(metadata['session_id']):
        errors.append(f"Invalid session_id format: {metadata['session_id']}")

    # 7. agent_names validation
    if not metadata.get('agent_names'):
        errors.append("Missing required field: agent_names")
    elif not isinstance(metadata['agent_names'], list):
        errors.append(f"agent_names must be array, got: {type(metadata['agent_names'])}")
    elif len(metadata['agent_names']) == 0:
        errors.append("agent_names cannot be empty")

    return errors
```

---

## Content Validation

### Section Structure

Required sections (in order):
1. [ ] Execution Summary
2. [ ] Key Decisions (optional but recommended)
3. [ ] Context Shifts (optional but recommended)
4. [ ] Extracted Learnings (optional but recommended)
5. [ ] Session Artifacts (optional but recommended)
6. [ ] Related Research (optional but recommended)
7. [ ] Metrics & Performance
8. [ ] Session ID

### Execution Summary Validation

```markdown
## Execution Summary

**Duration**: {{duration_ms}}ms
**Status**: {{status}}
**Model**: {{model_used}}
**Turns**: {{total_turns}}
**Functions**: {{total_functions}}
```

Validation:
- [ ] Section header present
- [ ] Duration is positive integer with "ms" suffix
- [ ] Status is one of: completed, error, running
- [ ] Model is one of: haiku, sonnet, opus
- [ ] Turns is non-negative integer
- [ ] Functions is non-negative integer
- [ ] No sensitive data in summary
- [ ] No stack traces or error messages

```python
def validate_execution_summary(summary_text):
    errors = []

    # Check for required metrics
    required_metrics = ['Duration', 'Status', 'Model', 'Turns', 'Functions']
    for metric in required_metrics:
        if metric not in summary_text:
            errors.append(f"Missing metric: {metric}")

    # Validate status value
    status_match = re.search(r'\*\*Status\*\*:\s*(\w+)', summary_text)
    if status_match:
        status = status_match.group(1)
        if status not in ['completed', 'error', 'running']:
            errors.append(f"Invalid status: {status}")

    # Validate numeric fields
    for field in ['Duration', 'Turns', 'Functions']:
        pattern = f'\\*\\*{field}\\*\\*:\\s*(\\d+)'
        if not re.search(pattern, summary_text):
            errors.append(f"Invalid {field} format")

    # Check for sensitive data
    if 'password' in summary_text.lower():
        errors.append("Sensitive data detected in summary")

    return errors
```

### Wiki-Link Validation

All wiki-links must be valid (resolvable or creatable):

```markdown
- [[decision-title]] ← Must exist in vault or be valid path
- [[sensory/paper-slug]] ← Must exist or be valid path
- [[memory/lesson-title]] ← Must exist or be valid path
```

Validation:
- [ ] Links use format `[[path-to-note]]`
- [ ] Paths use valid vault directory structure
- [ ] No broken links (either exist or will be created)
- [ ] No circular references
- [ ] Links are lowercase with hyphens (vault convention)

```python
def validate_wikilinks(content, vault):
    errors = []
    links = re.findall(r'\[\[([^\]]+)\]\]', content)

    for link in links:
        # Check if note exists
        if not vault.note_exists(link):
            # Check if path is valid for creation
            if not is_valid_vault_path(link):
                errors.append(f"Invalid wiki-link path: {link}")
            # Valid for creation, only warn
            else:
                errors.append(f"Link to non-existent note (will create): {link}")

        # Check for circular references
        if is_circular_reference(link):
            errors.append(f"Circular reference detected: {link}")

    return errors
```

### Metrics Validation

Metrics must be valid JSON:

```json
{
  "total_turns": 47,
  "total_functions": 312,
  "errors": 2,
  "recovery_attempts": 1
}
```

Validation:
- [ ] Valid JSON format (no trailing commas, quotes, etc)
- [ ] All numeric fields are numbers (not strings)
- [ ] No negative numbers (except where semantically valid)
- [ ] No missing required fields

```python
def validate_metrics(metrics_json_str):
    errors = []

    try:
        metrics = json.loads(metrics_json_str)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in metrics: {e}")
        return errors

    # Validate required fields
    required = ['total_turns', 'total_functions', 'errors', 'recovery_attempts']
    for field in required:
        if field not in metrics:
            errors.append(f"Missing metrics field: {field}")
        elif not isinstance(metrics[field], int):
            errors.append(f"Metrics field must be integer: {field}")
        elif metrics[field] < 0:
            errors.append(f"Metrics field cannot be negative: {field}")

    return errors
```

### Session ID Validation

```markdown
## Session ID

`sess-abc12345`
```

Validation:
- [ ] Section header present
- [ ] Session ID in code block (backticks)
- [ ] Matches session_id in frontmatter
- [ ] Non-empty, alphanumeric + hyphens

```python
def validate_session_id(session_id_section, frontmatter_id):
    errors = []

    # Extract ID from code block
    match = re.search(r'`([^`]+)`', session_id_section)
    if not match:
        errors.append("Session ID not in code block (missing backticks)")
        return errors

    extracted_id = match.group(1)

    # Validate format
    if not re.match(r'^[a-z0-9\-]+$', extracted_id):
        errors.append(f"Invalid session ID format: {extracted_id}")

    # Match with frontmatter
    if extracted_id != frontmatter_id:
        errors.append(f"Session ID mismatch: frontmatter={frontmatter_id}, content={extracted_id}")

    return errors
```

---

## Full Validation Function

```python
def validate_agent_log(filepath):
    """Validate complete agent log file."""
    errors = []

    # 1. File exists and is readable
    if not os.path.exists(filepath):
        errors.append(f"File not found: {filepath}")
        return errors

    # 2. Read file
    with open(filepath, 'r') as f:
        content = f.read()

    # 3. Parse frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        errors.append("Missing or invalid frontmatter delimiter (---)")
        return errors

    try:
        metadata = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML frontmatter: {e}")
        return errors

    # 4. Validate frontmatter
    errors.extend(validate_frontmatter(metadata))

    # 5. Extract content body
    body = content[fm_match.end():].strip()

    # 6. Validate sections
    errors.extend(validate_execution_summary(body))
    errors.extend(validate_wikilinks(body, vault))
    errors.extend(validate_metrics(extract_metrics_section(body)))
    errors.extend(validate_session_id(
        extract_session_id_section(body),
        metadata['session_id']
    ))

    # 7. Return results
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "filepath": filepath,
        "session_id": metadata.get('session_id')
    }
```

---

## Testing Validation

### Unit Test Examples

```python
def test_valid_agent_log():
    """Valid agent log passes all checks."""
    result = validate_agent_log('daily/agent-logs/2026-02-11T14-30-example.md')
    assert result['valid'] == True
    assert len(result['errors']) == 0

def test_missing_required_field():
    """Missing required frontmatter field raises error."""
    content = """---
date: "2026-02-11T14:30:00Z"
title: "Agent Execution Summary"
tags: [agent, execution, entire.io]
status: archived
source: entire.io
---
"""
    errors = validate_frontmatter(parse_yaml(content))
    assert "Missing required field: session_id" in errors

def test_invalid_status():
    """Invalid status value raises error."""
    metadata = {'status': 'active'}
    errors = validate_frontmatter(metadata)
    assert any("Status must be 'archived'" in e for e in errors)

def test_invalid_metrics_json():
    """Invalid JSON in metrics section raises error."""
    metrics_str = '{"total_turns": 10, "total_functions": 20,}'
    errors = validate_metrics(metrics_str)
    assert len(errors) > 0
```

---

## Daemon Validation (Week 2)

For `entire_sync_daemon.py`:

```python
# Before writing to vault
generated_markdown = generate_agent_log(entire_io_session)
validation_result = validate_agent_log(generated_markdown)

if not validation_result['valid']:
    logger.error(f"Validation failed: {validation_result['errors']}")
    # Move to DLQ for manual review
    dlq.put(entire_io_session, validation_result['errors'])
else:
    # Write to vault
    vault.write(f"daily/agent-logs/{session_id}.md", generated_markdown)
    logger.info(f"Agent log written: {session_id}")
```

---

## Common Issues & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Invalid date format" | Not ISO 8601 | Add timezone: "2026-02-11T14:30:00Z" |
| "Title must contain session_id" | Copy-paste template | Update title to include actual session_id |
| "Missing required tag: entire.io" | Tag list incomplete | Add all 3 tags: [agent, execution, entire.io] |
| "Status must be 'archived'" | Used different status | Always use "archived" for entire.io sessions |
| "Invalid session_id format" | Special characters | Use alphanumeric + hyphens only |
| "agent_names cannot be empty" | No agents in session | Must have at least one agent |
| "Invalid JSON in metrics" | Trailing comma or quotes | Use json.dumps() for generation |
| "Session ID mismatch" | Frontmatter ≠ body | Ensure consistency in generation |

---

## Pre-Commit Checklist

Before committing agent log files:

- [ ] All required frontmatter fields present
- [ ] All field values valid format
- [ ] Section headers in correct order
- [ ] Wiki-links resolvable or valid paths
- [ ] Metrics JSON valid
- [ ] Session ID matches frontmatter
- [ ] No sensitive data (passwords, tokens, API keys)
- [ ] No stack traces or error messages
- [ ] No TODO or placeholder text
- [ ] File permissions correct (644)
- [ ] No trailing whitespace

---

## Related Files

- `daily/agent-logs/_template.md` - Template structure
- `patterns/agent-logs-vault-schema.md` - Schema reference
- `patterns/entire-io-to-vault-mapping.md` - Daemon implementation guide

---

**Last Updated**: 2026-02-11
**Status**: Ready for daemon implementation
**Next Review**: 2026-02-13 (after Week 2 testing)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[agent-logs-vault-schema]] — the schema this validation checklist enforces
- [[concept-validation]] — the broader validation methodology applied here to agent log structure
