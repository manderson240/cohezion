# Pi Agent Repair Guide — Cohezion Project

> **For:** Any Pi agent session that encounters startup or extension errors.
> **Last updated:** 2026-04-12 (Session 101)
> **Project:** `/home/mike-anderson/dev/cohezion`

---

## Quick Diagnosis

Run this first to see what's broken:

```bash
bash scripts/platform-health-sentinel.sh --proactive --platform pi
```

---

## Issue 1: Extension Load Failure — "Invalid package config"

**Error:**
```
Error: Failed to load extension ".pi/extensions/cohezion-kg-optimized.ts": 
Failed to load extension: Invalid package config /home/mike-anderson/dev/cohezion/package.json
```

**Root Cause:** Pi (v0.66.1+) uses ESM module resolution. It reads the project root `package.json` to determine module type. If `package.json` is missing, empty (0 bytes), or lacks `"type": "module"`, all TypeScript extensions fail to load.

**Fix:**

```bash
# Check current state
cat package.json

# If empty, missing, or has no "type" field:
cat > package.json << 'EOF'
{
  "private": true,
  "type": "module",
  "description": "Pi agent extension support — ESM module resolution for .pi/extensions/*.ts"
}
EOF
```

**Verify:** Restart Pi — extensions should load without error.

---

## Issue 2: Extension Load Failure — "Cannot find module"

**Error:**
```
Error: Cannot find module '@sinclair/typebox'
```

**Root Cause:** The optimized extensions (`cohezion-kg-optimized.ts`, `cohezion-bridge-v4-optimized.ts`) import `@sinclair/typebox` which ships with Pi but may not resolve if Pi was installed in a non-standard location.

**Fix:** Use the simpler extensions that don't require external type imports:

```bash
# Edit .pi/settings.json — change extensions list
# FROM:
"extensions": [
    ".pi/extensions/cohezion-kg-optimized.ts",
    ".pi/extensions/cohezion-bridge-v4-optimized.ts"
]

# TO (use the lightweight versions):
"extensions": [
    ".pi/extensions/cohezion-kg.ts",
    ".pi/extensions/cohezion-bridge-v3.ts"
]
```

**Note:** `cohezion-kg.ts` is a no-op stub (KG tools come from MCP servers). `cohezion-bridge-v3.ts` has fewer features than v4 but no external dependencies.

---

## Issue 3: "Agent is already processing" Runtime Error

**Error:**
```
Extension "<runtime>" error: Agent is already processing. 
Specify streamingBehavior ('steer' or 'followUp') to queue the message.
```

**Root Cause:** An extension calls `pi.sendMessage()` or `pi.sendUserMessage()` while the agent is mid-response. Pi requires explicit streaming behavior specification.

**Fix:** In any extension that sends messages:

```typescript
// WRONG — throws during streaming
pi.sendUserMessage("Some message");

// CORRECT — waits for current turn to finish
pi.sendUserMessage("Some message", { deliverAs: "followUp" });

// CORRECT — interrupts current turn
pi.sendUserMessage("Some message", { deliverAs: "steer" });
```

**Current extensions are safe:** Both `cohezion-kg.ts` and `cohezion-bridge-v3.ts` only use `pi.exec()` and `ctx.ui.notify()`, which don't trigger this error. If you see this error, it's from the MCP bridge layer or a newly added extension.

---

## Issue 4: Skill Conflicts / Duplicate Skills

**Error:**
```
Warning: Duplicate skill name 'kaggle' found in multiple directories
```

**Root Cause:** Skills exist in 3 directories with overlapping names:
- `.pi/skills/` — Pi-specific
- `.agent/skills/` — Agent-level  
- `src/cohezion/skills/` — PRIME skills (212+)

**Fix:**

```bash
# Remove broken symlinks
find .pi/skills -type l ! -exec test -e {} \; -print -delete

# Check for actual name collisions
find .pi/skills .agent/skills src/cohezion/skills -name "SKILL.md" 2>/dev/null | \
  xargs -I{} dirname {} | xargs -I{} basename {} | sort | uniq -d
```

---

## Issue 5: MCP Server Connection Failures

**Error:**
```
MCP server 'cohezion-vault' failed to start
```

**Root Cause:** MCP servers defined in `.pi/mcp.json` require specific environment variables and running services.

**Pre-flight checklist:**

```bash
# 1. Check SurrealDB
curl -sf http://localhost:8001/health && echo "SurrealDB: OK" || echo "SurrealDB: DOWN"

# 2. Check Ollama
curl -sf http://localhost:11434/api/tags && echo "Ollama: OK" || echo "Ollama: DOWN"

# 3. Check Python venv
test -f .venv/bin/python && echo "venv: OK" || echo "venv: MISSING — run 'uv venv && uv pip install -e .'"

# 4. Verify MCP config is valid JSON
python3 -c "import json; json.load(open('.pi/mcp.json')); print('mcp.json: valid')"
```

**Start services if needed:**

```bash
# SurrealDB
surreal start --log info --user root --pass root --bind 127.0.0.1:8001 surrealkv://.surrealdb-data &

# Ollama (if not running)
ollama serve &
```

---

## Issue 6: Bash Tool Errors

**Common bash errors in Pi sessions:**

### `uv: command not found`
```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/home/linuxbrew/.linuxbrew/bin:$PATH"
```

### `python: command not found`  
Always use `python3`, never `python`. Or:
```bash
uv run python3 your_script.py
```

### Permission denied on scripts
```bash
chmod +x scripts/platform-health-sentinel.sh
chmod +x .claude/hooks/*.sh
```

### Git LFS pointer files instead of real binaries
```bash
git lfs pull
# Verify: file vendor/lemonade/bin/librocroller.so.1 should say "ELF 64-bit"
file vendor/lemonade/bin/librocroller.so.1
```

---

## Project-Specific Context for Pi Agent

### Key Commands
```bash
uv run pytest tests/ -q              # Run tests (6,300+)
make format && make lint             # Format + lint
bash scripts/platform-health-sentinel.sh --proactive --platform pi  # Health check
```

### Architecture
- **Language:** Python 3.13+, managed by `uv` (NEVER bare pip)
- **DB:** SurrealDB at ws://localhost:8001
- **API:** FastAPI at :8080
- **Models:** Ollama local (9 models), Lemonade NPU/GPU/CPU
- **Git LFS:** Active — 46 vendor .so/.whl/.pth files are LFS pointers
- **Remote:** git@github.com:manderson240/cohezion.git

### Hardware
- **CPU:** AMD Ryzen AI MAX+ 395 (16C/32T)
- **GPU:** Radeon 8060S (iGPU, ROCm — NOT CUDA)
- **RAM:** 128 GiB LPDDR5X
- **Local inference:** Ollama + Lemonade vendor libs in `vendor/lemonade/bin/`

### File Locations
| What | Where |
|------|-------|
| Pi config | `.pi/settings.json` |
| Pi extensions | `.pi/extensions/*.ts` |
| Pi MCP servers | `.pi/mcp.json` |
| Pi skills | `.pi/skills/` |
| Pi system prompt | `.pi/SYSTEM.md` |
| Package config (ESM) | `package.json` |
| Health sentinel | `scripts/platform-health-sentinel.sh` |
| Git LFS patterns | `.gitattributes` |
| Claude rules | `.claude/rules/` |
| Project instructions | `CLAUDE.md` |

---

## Full Repair Sequence (Nuclear Option)

If multiple things are broken, run this sequence:

```bash
cd /home/mike-anderson/dev/cohezion

# 1. Fix package.json
echo '{"private":true,"type":"module","description":"Pi extension ESM support"}' > package.json

# 2. Fix broken symlinks
find .pi/skills -type l ! -exec test -e {} \; -print -delete

# 3. Ensure venv exists
test -f .venv/bin/python || (uv venv && uv pip install -e .)

# 4. Restore LFS files
git lfs pull

# 5. Validate all configs
python3 -c "import json; json.load(open('.pi/settings.json')); print('settings: OK')"
python3 -c "import json; json.load(open('.pi/mcp.json')); print('mcp: OK')"
python3 -c "import json; json.load(open('package.json')); print('package: OK')"

# 6. Run full health check
bash scripts/platform-health-sentinel.sh --heal --platform pi

# 7. Restart Pi
pi
```
