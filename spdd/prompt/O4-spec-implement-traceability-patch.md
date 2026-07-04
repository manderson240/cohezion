# Operation 4 Manual Patch — spec-implement.md Traceability Step

`~/.claude/commands/spec-implement.md` is read-only from the Claude Code sandbox.
Insert the following block into Step 2.4 ("Update Plan After EACH Task"), immediately
before the `---` divider that ends that section.

## Snippet to insert in `~/.claude/commands/spec-implement.md`

After "This is NON-NEGOTIABLE." add:

```markdown
**Traceability (fire-and-forget):**

After updating the checkbox, emit a file-touch record to the traceability graph for
each file edited in this task. This runs in the background and never blocks:

```bash
PLAN_SLUG=$(cz plan status --json 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('slug',''))" 2>/dev/null)
STEP_NUM="<current_step_number>"
# Repeat for each file touched in this task:
uv run python -m cohezion.traceability.record_touch "$PLAN_SLUG" "$STEP_NUM" "<file_path>" &
```

If SurrealDB is offline or the module is unavailable, these calls fail silently.
```

## How to apply

```bash
! nano ~/.claude/commands/spec-implement.md
# or
! code ~/.claude/commands/spec-implement.md
```
