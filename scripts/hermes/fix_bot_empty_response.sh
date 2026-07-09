#!/usr/bin/env bash
# Fix the Hermes bot "empty content after retries" failure (2026-06-07).
#
# ROOT CAUSE (diagnosed from ~/.hermes/logs/agent.log:9285): the Telegram session
# 20260604_200952_1bd75fc4 grew to history=281 messages / tool_turns=123 because
# `compression.enabled` was FALSE — history compression off → unbounded session → the model
# (Qwen3.6-35B-A3B-NoThinking) chokes on the bloated context and returns EMPTY content.
# Inference itself is healthy (a plain curl returns "Hello!"); the model + cheap_model config
# are correct. Compounded by 5 corrupted junk config keys ('"compression' etc.) from botched
# write-back edits (hermes-skill #4).
#
# THE FIX (verified on a config copy before shipping):
#   1. compression.enabled = True  (THE root cause)
#   2. compression.hygiene_hard_message_limit = 120  (trip before the model chokes ~281;
#      protect_last_n=15 keeps recent turns)
#   3. remove the 5 corrupted '"…' junk keys
#   Restarting the gateway also clears the bloated 281-msg IN-MEMORY session → immediate relief.
#
# WHY a script you run (not the agent): editing config.yaml must happen while the gateway is
# STOPPED (it writes config back on shutdown — hermes-skill #4), and the gateway is a --user
# systemd unit needing YOUR session bus (the sandboxed agent cannot reach it).
#
# Usage:  bash scripts/hermes/fix_bot_empty_response.sh
set -euo pipefail

CONFIG="$HOME/.hermes/config.yaml"
PY="$HOME/.hermes/hermes-agent/venv/bin/python"   # has ruamel
[ -x "$PY" ] || PY="python3"

echo "==> backing up $CONFIG"
cp "$CONFIG" "$CONFIG.bak.$(date -u +%Y%m%dT%H%M%SZ)"

echo "==> stopping hermes-gateway (config write-back race: must edit while stopped)"
systemctl --user stop hermes-gateway.service
sleep 2

echo "==> editing config (ruamel, format-preserving): compression on + hard-limit 120 + drop junk keys"
"$PY" - "$CONFIG" <<'PYEOF'
import sys
from pathlib import Path
from ruamel.yaml import YAML

p = Path(sys.argv[1])
yaml = YAML(); yaml.preserve_quotes = True
cfg = yaml.load(p)

comp = cfg["compression"]
comp["enabled"] = True
comp["hygiene_hard_message_limit"] = 120

junk = [k for k in list(cfg.keys()) if isinstance(k, str) and k.startswith('"')]
for k in junk:
    del cfg[k]

yaml.dump(cfg, p)
print(f"   compression.enabled=True, hygiene_hard_message_limit=120; removed junk keys: {junk}")
PYEOF

echo "==> starting hermes-gateway (also clears the bloated in-memory session)"
systemctl --user start hermes-gateway.service
sleep 5

echo "==> verify AFTER start (write-back race means verify post-start, not pre):"
"$PY" - "$CONFIG" <<'PYEOF'
import sys
from pathlib import Path
from ruamel.yaml import YAML
cfg = YAML().load(Path(sys.argv[1]))
comp = cfg["compression"]
junk = [k for k in cfg if isinstance(k, str) and k.startswith('"')]
assert comp["enabled"] is True, "compression.enabled did not stick — check the write-back race"
assert not junk, f"junk keys still present: {junk}"
print(f"   OK: compression.enabled={comp['enabled']}, hard_limit={comp['hygiene_hard_message_limit']}, junk={junk}")
print("   Message the bot ('what is cohezion?') — it should reply now (fresh session + compression on).")
PYEOF

systemctl --user is-active hermes-gateway.service && echo "==> gateway active. Done."
