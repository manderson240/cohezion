# SurrealDB timestamp-dash bug — caught live 2026-06-03

## What broke

The MyceliumRegistry._promote_pattern path (added in WS6) generated
SurrealDB record IDs with the format:

    mycelium_patterns:mycelium_0_20260604-032226

SurrealDB's SQL parser interprets the first dash in the ID as a
**subtraction operator**, so this gets parsed as

    mycelium_patterns:mycelium_0_20260604 - 32226

which fails type validation with:
    Cannot perform subtraction with 'mycelium_patterns:mycelium_0_20260604' and '32226'

The HTTP response was a 200 OK with `status: "ERR"` in the JSON body,
which the registry did not parse. Result: the auto-promote path
silently failed for **every** invocation between WS6 (2026-06-03) and
this fix (also 2026-06-03 — caught the same day by live end-to-end
verification of WS1).

The vault write was unaffected (filesystem, no parser involved).

## How it was caught

The WS1 wiring test verified the bus emit path works end-to-end.
Manually running the test against a live SurrealDB instance showed
that the registry's auto-promote *thought* it was writing (it logged
"wrote mycelium pattern to surrealdb") but the table had only 1 row
(an older manually-ingested record). Drilling in: parsed the response
body, saw the `status: "ERR"` field, traced to the subtraction bug.

## Fix

Two changes in `_promote_pattern`:

1. **`ts_compact = ts.replace("-", "")`** when building the SurrealDB
   record ID. The vault filename still uses the human-readable
   `YYYYMMDD-HHMMSS` format. Only the DB ID is compacted.

2. **Parse the response body** and check for `status == "ERR"`. Log
   at debug level and return silently (preserves the best-effort
   contract, but now the failure mode is observable).

## Lesson: best-effort writes need response checking

`urllib.request.urlopen().read()` succeeds (no exception) on a 200
response even when the server returns a logical error in the body.
The previous code assumed "no exception = success" — but the body
might say "ERR". For any "best-effort" write, parse the response
and check semantic status.

## Related

- Commit: `9c75c9018` (fix(mycelium): strip dashes from timestamp in
  SurrealDB record ID)
- Live verification artifact: 4 mycelium_patterns rows in SurrealDB
  (1 prior + 3 from the live verification)
- See also: docs/ops/two-mycelium-systems.md (the broader
  auto-promote architecture)
