# Concept: SurrealDB InMemoryStore Mocking

## Abstract
A persistence mocking pattern to simulate the exact client result wrapping behavior of SurrealDB. It ensures mock query implementations return structured results matching production databases.

## Context & Motivation
SurrealDB clients expect query response outputs to follow the JSON structure:
`[{"result": [...], "status": "OK"}]`

When mocks return flat python dictionaries or list structures directly, consumer queries calling `.get("result")` raise `AttributeError`. Standardizing the query mock layer to wrap data inside a dictionary with a `"result"` key prevents silent integration errors in mock environments.

## Implementation Pattern
```python
def query(self, sql: str, vars: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    # 1. Parse update/select operations from SQL string.
    # 2. Mutate or query local in-memory store.
    # 3. Wrap outcomes inside standard structure.
    return [{"result": query_results, "status": "OK"}]
```

## Related
* [[LLM-Wiki]]
