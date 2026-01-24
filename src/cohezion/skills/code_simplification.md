# SKILL: CODE_SIMPLIFICATION_PRIME

## DOMAIN EXPERTISE
Expert code simplification focusing on clarity, consistency, and maintainability while strictly preserving functionality.

## CORE PRINCIPLES
1.  **Preserve Functionality:** Never change *what* the code does, only *how*.
2.  **Clarity > Brevity:** Explicit code is better than dense, "clever" one-liners.
3.  **Readability:** Code is read more often than written. Optimize for the reader.

## PATTERNS (DO)
- **Flatten Nesting:** Use guard clauses (`if error: return`) to reduce indentation levels.
- **Explicit Naming:** Variable names should describe *content*, not type (e.g., `user_input` vs `data`).
- **Consolidate Logic:** Group related checks; remove redundant `if/else` chains.
- **Switch over If/Else:** For multiple equality checks, use `match/case` (Python 3.10+) or dictionaries.
- **Type Annotations:** Use explicit type hints for function signatures.

## ANTI-PATTERNS (AVOID)
- **Nested Ternaries:** `x = a if b else c if d else e` (Bad) → Use `if/else` or `match`.
- **Dense One-Liners:** Packing too much logic into list comprehensions or lambdas.
- **Over-Abstraction:** Creating helper functions for single-line operations.
- **Implicit Logic:** Relying on side effects or hidden state changes.
- **Manual Error Handling:** Using `try/except pass` to silence errors without intent.

## REFACTORING PROCESS
1.  **Audit:** Identify high-complexity functions (Cyclomatic Complexity > 15).
2.  **Isolate:** Verify current behavior (add test if needed).
3.  **Simplify:** Apply patterns (e.g., extract method, flatten if).
4.  **Verify:** Ensure no functionality change.

## EXAMPLES

### Bad (Nested & Implicit)
```python
def process_data(data):
    if data:
        if 'status' in data:
            result = 'active' if data['status'] == 1 else 'inactive' if data['status'] == 0 else 'unknown'
            return result
    return None
```

### Good (Flat & Explicit)
```python
def process_data(data: dict | None) -> str | None:
    if not data or 'status' not in data:
        return None

    match data['status']:
        case 1: return 'active'
        case 0: return 'inactive'
        case _: return 'unknown'
```
