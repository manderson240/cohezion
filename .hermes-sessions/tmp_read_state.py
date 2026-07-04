import json
from pathlib import Path

state_path = Path.home() / ".cohezion-research/tcrao_state.json"
with open(state_path) as f:
    contents = f.read()

try:
    state = json.loads(contents)
except json.JSONDecodeError:
    lines = [l.strip() for l in contents.split("\n") if l.strip().startswith("{")]
    last_valid = {}
    for line in reversed(lines):
        try:
            last_valid = json.loads(line)
            break
        except Exception:
            continue
    state = last_valid

print(json.dumps(state, indent=2))
