# SurrealQL Python repr() Injection

## Description

Identifies and fixes SQL injection vulnerabilities specific to SurrealDB when queries are built with Python f-strings. Two subtle injection vectors exist that standard SQL escaping does not cover:

1. **Bare identifier injection** -- SurrealQL UPSERT/RELATE uses unquoted record IDs (`UPSERT neuron:slug SET ...`). If the identifier comes from user input, an attacker can inject `neuron:x; DELETE neuron;--` and execute arbitrary statements.

2. **Python `repr()` tag-list injection** -- Interpolating a Python list into SurrealQL via `tags = {tags}` calls `list.__repr__()`, which wraps strings in double quotes. SurrealQL string literals use single quotes. A tag value like `'); DELETE neuron; --` breaks out of the SQL context because `repr()` does not escape single quotes.

A third, related issue: naive `escape_sql()` implementations that only handle `\` and `'` miss null bytes (`\0`) and newlines (`\n`, `\r`), which can bypass WAF-style filters or cause truncation in some query parsers.

## Trigger Conditions

Apply this skill when you encounter ANY of:

- Building SurrealQL queries with Python f-strings or `.format()`
- Interpolating identifiers in `table:id` format into UPSERT, RELATE, UPDATE, DELETE, or SELECT statements
- Using Python `list.__repr__()` (implicit via `f"{tags}"`) to embed lists in SQL
- Security review of any SurrealDB integration code
- Reviewing `escape_sql()` or `sanitize_*` functions for SurrealQL

## Fixes

### 1. Validate bare identifiers with allowlist regex

```python
import re

def validate_surreal_id(identifier: str) -> str:
    """Validate a SurrealDB record identifier (e.g. 'neuron:some_slug').

    Prevents SQL injection via bare identifiers in UPSERT/RELATE statements.
    Only allows alphanumeric characters, underscores, hyphens, colons, and dots.
    """
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_:.\-]*$", identifier):
        raise ValueError(f"Invalid SurrealDB identifier: {identifier!r}")
    return identifier
```

**Usage:** Call before every f-string interpolation of a record ID.

```python
safe_id = validate_surreal_id(neuron_id)
sql = f"UPSERT {safe_id} SET title = '{escape_sql(title)}';"
```

### 2. Escape tag lists element-by-element

Never rely on `repr()` for SQL values. Build the SurrealQL array literal manually:

```python
def escape_tag_list(tags: list[str]) -> str:
    """Safely serialize a tag list for SurrealQL.

    Escapes each tag as a single-quoted string literal instead of
    relying on Python list repr interpolation.
    """
    escaped = [f"'{escape_sql(str(t))}'" for t in tags]
    return f"[{', '.join(escaped)}]"
```

**Before (vulnerable):**
```python
sql = f"UPSERT neuron:x SET tags = {tags};"
# tags = ["safe", "'); DELETE neuron; --"]
# Produces: tags = ["safe", "'); DELETE neuron; --"]
#           ^^^ double quotes -- SurrealQL uses single quotes
#           The single quote in the value breaks out of context
```

**After (safe):**
```python
sql = f"UPSERT neuron:x SET tags = {escape_tag_list(tags)};"
# Produces: tags = ['safe', '\'); DELETE neuron; --']
#           ^^^ single quotes, inner single quote escaped
```

### 3. Harden escape_sql() for completeness

```python
def escape_sql(text: str) -> str:
    """Escape for SurrealQL string literals."""
    return text.replace("\\", "\\\\").replace("'", "\\'")[:2000]
```

Consider also escaping null bytes and newlines if your threat model includes binary injection or multi-line query manipulation:

```python
def escape_sql_strict(text: str) -> str:
    """Strict escape for SurrealQL string literals."""
    return (
        text
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\0", "")       # strip null bytes
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )[:2000]
```

### 4. Credential hygiene

Hardcoded `root/root` credentials are acceptable for `localhost` development but should trigger a warning or validation when the SurrealDB URL points to a remote host:

```python
SURREALDB_URL = os.environ.get("SURREALDB_URL", "http://localhost:8001")
AUTH = (
    os.environ.get("SURREALDB_USERNAME", "root"),
    os.environ.get("SURREALDB_PASSWORD", "root"),
)

if not SURREALDB_URL.startswith(("http://localhost", "http://127.0.0.1")):
    if AUTH == ("root", "root"):
        logger.warning("Using default root/root credentials with remote SurrealDB URL")
```

## Verification Checklist

- [ ] Every record ID interpolated into SQL passes through `validate_surreal_id()`
- [ ] Every string value interpolated into SQL passes through `escape_sql()`
- [ ] No Python `list.__repr__()` used in SQL context -- use `escape_tag_list()` instead
- [ ] `escape_sql()` handles at minimum `\` and `'`; consider `\0`, `\n`, `\r`
- [ ] Default credentials warn when URL is not localhost

## Reference Implementation

`cloud-vault-mcp/src/mcp_server/graph_writer.py` -- see `validate_surreal_id()` (line 47), `escape_tag_list()` (line 58), and `escape_sql()` (line 42).

## Why This Matters

SurrealDB's HTTP SQL endpoint accepts raw SurrealQL strings. Unlike PostgreSQL or MySQL drivers, there is no parameterized query API for SurrealDB's HTTP interface -- all escaping must be done application-side. This makes Python f-string query building especially dangerous because Python's `repr()` and SurrealQL's string syntax use different quoting conventions.
