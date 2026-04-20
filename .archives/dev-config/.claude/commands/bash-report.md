# Bash Tool Usage Report

Review which Bash commands should have used dedicated Claude Code tools,
with suggested replacements.

```bash
python3 -c "
import json, collections
from pathlib import Path

log = Path.home() / '.local/share/claude-code/bash-catcher.jsonl'
if not log.exists():
    print('No violations logged yet.')
    raise SystemExit

entries = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
print(f'Total violations logged: {len(entries)}')
print()

# Count by preferred tool
by_tool = collections.Counter()
for e in entries:
    for v in e['violations']:
        by_tool[v['tool']] += 1

print('Violations by preferred tool:')
for tool, count in by_tool.most_common():
    print(f'  {tool}: {count}')

print()
print('Recent violations (last 5) with suggested replacements:')
for e in entries[-5:]:
    print(f'  [{e[\"ts\"][:16]}] {e[\"command_preview\"][:60]}')
    for v in e['violations']:
        call = v.get('suggested_call') or v['suggestion']
        print(f'    → {v[\"tool\"]}: {call}')
"
```
