---
name: lemonade-ctx-size-investigation
version: 2.0.0
status: superseded
superseded_by: "harness.md N3"
description: >
  SUPERSEDED (2026-06-09). Original skill claimed ctx-size hardcoded at 4096 with all overrides failing.
  FALSE for lemonade 10.6.0+. See harness.md N3 for the corrected fix: pre-load with bounded ctx_size
  via POST :13305/api/v1/load {ctx_size:16384, save_options:true}. Kept for historical reference only.
trigger: "lemonade ctx-size | ctx_size=0 crash | 2026-06-09 oom"
---

# ⚠️ SUPERSEDED: lemond ctx-size Investigation (See harness.md N3)

**Status:** Superseded 2026-06-09. Original claim (ctx-size hardcoded=4096, all overrides fail) is FALSE for lemonade 10.6.0+.

**Corrected Fix (harness.md N3, verified 2026-06-09):**
```bash
# Pre-load with bounded ctx AND persist:
curl -s -X POST http://localhost:13305/api/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "Qwen3.6-35B-A3B-ThinkingCoder", "ctx_size": 16384, "save_options": true}'
# Verify:
curl -s http://localhost:13305/api/v1/models/Qwen3.6-35B-A3B-ThinkingCoder \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('ctx_size:', d.get('recipe_options',{}).get('ctx_size'))"
# Expected: ctx_size: 16384
```

---

## Original Investigation (Historical Reference, OUTDATED)

# lemond ctx-size — Hardcoded 4096 (All Overrides Fail)

**Confirmed on:** lemond Vulkan backend, Strix Halo gfx1151, 2026-04-29

## The Hard Truth

lemond's Vulkan-backend invocation of `llama-server` **always** passes `--ctx-size 4096`.
No configuration surface changes this. Verified exhaustively:

| Method | Result |
|--------|--------|
| `"ctx_size": 16384` in `~/.cache/lemonade/config.json` | Stored, not forwarded to llama-server |
| `lemonade load --ctx-size 16384` | CLI accepts it; mgmt API ignores it; process still starts at 4096 |
| `LEMONADE_CTX_SIZE=16384` in `/etc/lemonade/conf.d/zz-ctx-size.conf` | Not read by lemond auto-loader |
| `"llamacpp.args": "--ctx-size 16384"` in config.json | lemond strips `--ctx-size`; only unknown flags (e.g. `--no-mmap`) pass through |
| `lemonade load --llamacpp-args "--ctx-size 16384"` | Management API returns HTTP 500 |
| `lemonade config set llamacpp.args="--no-mmap --ctx-size 16384"` | Saves only `--no-mmap`; `--ctx-size` silently dropped |

## Why It's Acceptable

`--context-shift` **is** enabled in all lemond Vulkan invocations. Long conversations
slide the window — early tokens are evicted but generation continues. No crash.
For Eigent agent tasks (write a file, run a command, web search), 4096 is adequate.

## Diagnostic Approach (If You Need to Verify)

```bash
# Check what ctx-size a running model actually has
ps aux | grep "llama-server" | grep -v grep | grep -oP -- '--ctx-size \K\d+'

# Check full llama-server cmdline
cat /proc/$(pgrep -f "Qwen3-8B|gemma-4-26B" | head -1)/cmdline | tr '\0' ' '

# Lemond management API — available endpoints
curl -s http://localhost:13305/api/v0/models | python3 -m json.tool | head -20
curl -s http://localhost:13305/api/v1/health | python3 -m json.tool
```

## Lemond Management API Reference

- **Port 13305**: Web UI SPA + JSON API (via `/api/v0/` and `/api/v1/` prefixes)
- **GET** `/api/v0/models` — list all available models (not just loaded)
- **GET** `/api/v0/models/{id}` — model details
- **GET** `/api/v1/health` — version + loaded_models list
- **POST load**: only basic `lemonade load <model>` works; `--ctx-size`, `--llamacpp-args` return 500

## Workaround (Future)

If a future lemond version exposes ctx-size control, it will likely be via:
```bash
lemonade load <model> --llamacpp-args "--ctx-size 16384"
```
Track [lemonade-sdk/lemonade](https://github.com/lemonade-sdk/lemonade) for updates.
