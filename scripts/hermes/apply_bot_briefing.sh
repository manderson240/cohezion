#!/usr/bin/env bash
# Apply the Cohezion briefing to the Hermes bot's system prompt (agent.environment_hint),
# so the bot inherits this session's learnings and is "on the same page".
#
# WHY a script you run (not the agent): editing ~/.hermes/config.yaml must happen while the gateway
# is STOPPED (it writes config back on shutdown — an edit applied while running is clobbered,
# hermes-skill #4), and the gateway is a `--user` systemd unit that needs YOUR session bus. The agent
# cannot reach it. This script does the stop → edit (ruamel, format-preserving) → start → verify
# sequence in one shot. Re-run it any time the briefing changes.
#
# Usage:  bash scripts/hermes/apply_bot_briefing.sh
set -euo pipefail

REPO="/home/mike-anderson/dev/cohezion"
BRIEFING="$REPO/docs/ops/COHEZION_BOT_BRIEFING.md"
CONFIG="$HOME/.hermes/config.yaml"
PY="$HOME/.hermes/hermes-agent/venv/bin/python"   # has ruamel + hermes deps
[ -x "$PY" ] || PY="python3"

echo "==> backing up $CONFIG"
cp "$CONFIG" "$CONFIG.bak.$(date -u +%Y%m%dT%H%M%SZ)"

echo "==> stopping hermes-gateway (config write-back race: must edit while stopped)"
systemctl --user stop hermes-gateway.service
sleep 2

echo "==> setting agent.environment_hint from the briefing (ruamel, format-preserving)"
"$PY" - "$CONFIG" "$BRIEFING" <<'PYEOF'
import sys
from pathlib import Path
from ruamel.yaml import YAML

cfg_path, briefing_path = Path(sys.argv[1]), Path(sys.argv[2])
briefing = briefing_path.read_text(encoding="utf-8")

yaml = YAML()
yaml.preserve_quotes = True
cfg = yaml.load(cfg_path)
agent = cfg.get("agent")
if agent is None:
    cfg["agent"] = agent = {}
agent["environment_hint"] = briefing
yaml.dump(cfg, cfg_path)
print(f"   environment_hint set ({len(briefing)} chars)")
PYEOF

echo "==> starting hermes-gateway"
systemctl --user start hermes-gateway.service
sleep 5

echo "==> verify (after start — the write-back race means verify POST-start, not pre):"
"$PY" - "$CONFIG" <<'PYEOF'
import sys
from pathlib import Path
from ruamel.yaml import YAML
cfg = YAML().load(Path(sys.argv[1]))
hint = (cfg.get("agent") or {}).get("environment_hint", "") or ""
print(f"   environment_hint now {len(hint)} chars; starts: {hint[:60]!r}")
assert "Cohezion" in hint, "environment_hint did not stick — check the write-back race"
print("   OK: briefing applied. Message the bot and ask 'what is Cohezion?' to confirm grounding.")
PYEOF

systemctl --user is-active hermes-gateway.service && echo "==> gateway active. Done."
