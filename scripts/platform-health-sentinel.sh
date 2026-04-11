#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Platform Health Sentinel — Cross-Platform Compound Engineering
# ═══════════════════════════════════════════════════════════════════════════════
#
# First-principles design from Session 101 disasters:
#   1. Silent failures are the root cause — make ALL failures loud
#   2. Accumulation without cleanup compounds into crises
#   3. Validation must happen at boundaries (startup, before ops)
#   4. Shared state without coordination corrupts everything
#
# Modes:
#   --proactive    Run at session start (non-blocking, warns only)
#   --reactive     Run after failure (diagnoses + suggests fixes)
#   --heal         Run with auto-fix (repairs what it can)
#   --platform X   Target specific platform (claude|gemini|pi|all)
#
# Usage:
#   platform-health-sentinel.sh --proactive --platform all
#   platform-health-sentinel.sh --reactive --platform claude
#   platform-health-sentinel.sh --heal --platform pi
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

MODE="${1:---proactive}"
PLATFORM="${3:-all}"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
REPORT=""
HEAL_ACTIONS=""
EXIT_CODE=0

# Colors (if terminal supports it)
RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'; NC='\033[0m'

warn()  { REPORT="${REPORT}[WARN]  $1\n"; }
fail()  { REPORT="${REPORT}[FAIL]  $1\n"; EXIT_CODE=1; }
pass()  { REPORT="${REPORT}[OK]    $1\n"; }
heal()  { HEAL_ACTIONS="${HEAL_ACTIONS}$1\n"; }

# ─── TIER 1: Shared Infrastructure ─────────────────────────────────────────

check_shared() {
    # --- Git repo health ---
    if git rev-parse --git-dir >/dev/null 2>&1; then
        GIT_SIZE_MB=$(( $(du -sk .git/ 2>/dev/null | awk '{print $1}') / 1024 ))
        if [ "$GIT_SIZE_MB" -gt 5120 ]; then
            fail ".git/ is ${GIT_SIZE_MB}MB (>5GB) — bloat detected"
            heal "git reflog expire --expire=now --all && git gc --prune=now"
        elif [ "$GIT_SIZE_MB" -gt 2048 ]; then
            warn ".git/ is ${GIT_SIZE_MB}MB — consider pruning"
        else
            pass ".git/ size: ${GIT_SIZE_MB}MB"
        fi

        # Entire.io branch accumulation
        ENTIRE_COUNT=$(git branch 2>/dev/null | grep -c 'entire/' || echo 0)
        if [ "$ENTIRE_COUNT" -gt 500 ]; then
            fail "${ENTIRE_COUNT} entire/ shadow branches — accumulation crisis"
            heal "entire clean --all --force"
        elif [ "$ENTIRE_COUNT" -gt 200 ]; then
            warn "${ENTIRE_COUNT} entire/ shadow branches accumulating"
        else
            pass "entire/ branches: ${ENTIRE_COUNT}"
        fi

        # Remote configured
        if [ "$(git remote 2>/dev/null | wc -l)" -eq 0 ]; then
            fail "No git remote — local-only repo has no backup"
            heal "git remote add origin git@github.com:manderson240/cohezion.git"
        else
            pass "Git remote: $(git remote -v 2>/dev/null | head -1 | awk '{print $2}')"
        fi

        # LFS active
        if [ -f .gitattributes ] && grep -q "filter=lfs" .gitattributes 2>/dev/null; then
            if ! command -v git-lfs >/dev/null 2>&1; then
                fail "LFS patterns in .gitattributes but git-lfs not installed"
                heal "sudo apt-get install -y git-lfs && git lfs install"
            elif ! git config --get filter.lfs.clean >/dev/null 2>&1; then
                fail "git-lfs installed but not initialized"
                heal "git lfs install"
            else
                LFS_COUNT=$(git lfs ls-files 2>/dev/null | wc -l)
                pass "LFS active: ${LFS_COUNT} files tracked"
            fi
        fi

        # Quick fsck (tree corruption check)
        FSCK_ERRORS=$(git fsck --no-dangling 2>&1 | grep -c "error\|badTree" || true)
        if [ "$FSCK_ERRORS" -gt 0 ]; then
            fail "git fsck: ${FSCK_ERRORS} errors — tree corruption detected"
        else
            pass "git fsck: clean"
        fi
    fi

    # --- Shared services ---
    if curl -sf http://localhost:8001/health >/dev/null 2>&1; then
        pass "SurrealDB: healthy (port 8001)"
    else
        warn "SurrealDB: unreachable (port 8001)"
    fi

    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        MODEL_COUNT=$(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
        pass "Ollama: healthy (${MODEL_COUNT} models)"
    else
        warn "Ollama: unreachable (port 11434)"
    fi
}

# ─── TIER 2: Claude Code ──────────────────────────────────────────────────

check_claude() {
    # Settings schema validation
    if [ -f "$HOME/.claude/settings.json" ]; then
        SCHEMA_ERRORS=$(python3 -c "
import json, sys
cfg = json.load(open('$HOME/.claude/settings.json'))
errors = []
sl = cfg.get('statusLine')
if sl is not None:
    if not isinstance(sl, dict): errors.append('statusLine not object')
    elif sl.get('type') != 'command': errors.append('statusLine.type invalid')
    elif not isinstance(sl.get('command'), str): errors.append('statusLine.command missing')
for event, matchers in cfg.get('hooks', {}).items():
    for i, m in enumerate(matchers):
        for j, h in enumerate(m.get('hooks', [])):
            if h.get('type') != 'command': errors.append(f'hooks.{event}[{i}][{j}].type')
            if not isinstance(h.get('command'), str): errors.append(f'hooks.{event}[{i}][{j}].command')
print(len(errors))
for e in errors: print(e, file=sys.stderr)
" 2>/tmp/sentinel-claude-errors.txt)
        if [ "$SCHEMA_ERRORS" -gt 0 ]; then
            fail "settings.json: ${SCHEMA_ERRORS} schema errors (ALL settings silently disabled!)"
            cat /tmp/sentinel-claude-errors.txt 2>/dev/null | while read err; do
                warn "  → $err"
            done
        else
            pass "Claude settings.json: valid schema"
        fi
        rm -f /tmp/sentinel-claude-errors.txt
    fi

    # Hooks executable
    HOOK_DIR="$HOME/.claude/hooks"
    if [ -d "$HOOK_DIR" ]; then
        NON_EXEC=$(find "$HOOK_DIR" -name "*.sh" ! -perm -u+x 2>/dev/null | wc -l)
        if [ "$NON_EXEC" -gt 0 ]; then
            warn "${NON_EXEC} hook scripts not executable"
            heal "chmod +x $HOOK_DIR/*.sh"
        else
            HOOK_COUNT=$(find "$HOOK_DIR" -name "*.sh" -perm -u+x 2>/dev/null | wc -l)
            pass "Claude hooks: ${HOOK_COUNT} executable"
        fi
    fi

    # MCP servers parseable
    if [ -f "$PROJECT_ROOT/.claude/mcp.json" ]; then
        if python3 -c "import json; json.load(open('$PROJECT_ROOT/.claude/mcp.json'))" 2>/dev/null; then
            MCP_COUNT=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.claude/mcp.json')); print(len(d.get('mcpServers',{})))" 2>/dev/null)
            pass "Claude MCP config: ${MCP_COUNT} servers defined"
        else
            fail "Claude mcp.json: invalid JSON"
        fi
    fi
}

# ─── TIER 3: Gemini CLI ───────────────────────────────────────────────────

check_gemini() {
    GEMINI_SETTINGS="$PROJECT_ROOT/.gemini/settings.json"
    if [ -f "$GEMINI_SETTINGS" ]; then
        if python3 -c "import json; json.load(open('$GEMINI_SETTINGS'))" 2>/dev/null; then
            MCP_COUNT=$(python3 -c "import json; d=json.load(open('$GEMINI_SETTINGS')); print(len(d.get('mcpServers',{})))" 2>/dev/null)
            pass "Gemini settings.json: valid (${MCP_COUNT} MCP servers)"
        else
            fail "Gemini settings.json: invalid JSON"
        fi

        # Check MCP server command paths exist
        BROKEN_COUNT=$(python3 -c "
import json, os, shutil, sys
d = json.load(open('$GEMINI_SETTINGS'))
broken = 0
for name, cfg in d.get('mcpServers', {}).items():
    cmd = cfg.get('command', '')
    if cmd and not os.path.exists(cmd) and not shutil.which(cmd):
        broken += 1
print(broken)
" 2>/dev/null)
        if [ "${BROKEN_COUNT:-0}" -eq 0 ]; then
            pass "Gemini MCP commands: all paths valid"
        else
            warn "Gemini MCP: ${BROKEN_COUNT} command paths unresolvable"
        fi
    else
        warn "Gemini settings.json: not found"
    fi

    # Agent definitions
    AGENT_DIR="$PROJECT_ROOT/.gemini/agents"
    if [ -d "$AGENT_DIR" ]; then
        AGENT_COUNT=$(ls "$AGENT_DIR"/*.md 2>/dev/null | wc -l)
        pass "Gemini agents: ${AGENT_COUNT} defined"
    fi
}

# ─── TIER 4: Pi Agent ─────────────────────────────────────────────────────

check_pi() {
    PI_SETTINGS="$PROJECT_ROOT/.pi/settings.json"
    if [ -f "$PI_SETTINGS" ]; then
        if python3 -c "import json; json.load(open('$PI_SETTINGS'))" 2>/dev/null; then
            pass "Pi settings.json: valid"
        else
            fail "Pi settings.json: invalid JSON"
        fi
    fi

    # package.json required for Pi extensions
    PKG="$PROJECT_ROOT/package.json"
    if [ -f "$PKG" ]; then
        PKG_SIZE=$(stat -c%s "$PKG" 2>/dev/null || stat -f%z "$PKG" 2>/dev/null || echo 0)
        if [ "$PKG_SIZE" -lt 3 ]; then
            fail "package.json is empty/invalid — Pi extensions will fail to load"
            heal "echo '{\"private\":true,\"type\":\"module\"}' > $PKG"
        elif python3 -c "import json; json.load(open('$PKG'))" 2>/dev/null; then
            HAS_TYPE=$(python3 -c "import json; d=json.load(open('$PKG')); print('yes' if d.get('type') else 'no')" 2>/dev/null)
            if [ "$HAS_TYPE" = "yes" ]; then
                pass "package.json: valid (type=$(python3 -c "import json; print(json.load(open('$PKG')).get('type','?'))" 2>/dev/null))"
            else
                warn "package.json: missing 'type' field — Pi ESM resolution may fail"
            fi
        else
            fail "package.json: invalid JSON — Pi extensions will fail"
            heal "echo '{\"private\":true,\"type\":\"module\"}' > $PKG"
        fi
    else
        fail "package.json: missing — Pi extensions cannot load"
        heal "echo '{\"private\":true,\"type\":\"module\",\"description\":\"Pi extension support\"}' > $PKG"
    fi

    # Pi extensions exist and are TypeScript
    EXT_DIR="$PROJECT_ROOT/.pi/extensions"
    if [ -d "$EXT_DIR" ]; then
        EXT_COUNT=$(ls "$EXT_DIR"/*.ts 2>/dev/null | wc -l)
        pass "Pi extensions: ${EXT_COUNT} TypeScript files"

        # Check for import resolution
        for ext in "$EXT_DIR"/*.ts; do
            if grep -q "@mariozechner/pi-coding-agent" "$ext" 2>/dev/null; then
                if ! command -v pi >/dev/null 2>&1; then
                    warn "Extension $(basename $ext) imports pi-coding-agent but pi not installed"
                fi
            fi
        done
    fi

    # Pi MCP config
    PI_MCP="$PROJECT_ROOT/.pi/mcp.json"
    if [ -f "$PI_MCP" ]; then
        if python3 -c "import json; json.load(open('$PI_MCP'))" 2>/dev/null; then
            PI_MCP_COUNT=$(python3 -c "import json; d=json.load(open('$PI_MCP')); print(len(d.get('mcpServers',{})))" 2>/dev/null)
            pass "Pi MCP config: ${PI_MCP_COUNT} servers"
        else
            fail "Pi mcp.json: invalid JSON"
        fi
    fi

    # Skill index health
    SKILL_IDX="$PROJECT_ROOT/.pi/skills/skill_index.json"
    if [ -f "$SKILL_IDX" ]; then
        if python3 -c "import json; json.load(open('$SKILL_IDX'))" 2>/dev/null; then
            SKILL_COUNT=$(python3 -c "import json; print(len(json.load(open('$SKILL_IDX'))))" 2>/dev/null)
            pass "Pi skill index: ${SKILL_COUNT} skills indexed"
        else
            fail "Pi skill_index.json: corrupted JSON"
            heal "cd $PROJECT_ROOT && python3 .pi/integrations/index_skills.py"
        fi
    fi
}

# ─── TIER 5: Cross-Platform Drift Detection ───────────────────────────────

check_drift() {
    # Compare MCP server counts across platforms
    CLAUDE_MCP=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.claude/mcp.json')); print(len(d.get('mcpServers',{})))" 2>/dev/null || echo 0)
    GEMINI_MCP=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.gemini/settings.json')); print(len(d.get('mcpServers',{})))" 2>/dev/null || echo 0)
    PI_MCP=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.pi/mcp.json')); print(len(d.get('mcpServers',{})))" 2>/dev/null || echo 0)

    if [ "$CLAUDE_MCP" != "$GEMINI_MCP" ] || [ "$CLAUDE_MCP" != "$PI_MCP" ]; then
        warn "MCP server drift: Claude=${CLAUDE_MCP}, Gemini=${GEMINI_MCP}, Pi=${PI_MCP}"
    else
        pass "MCP config aligned: ${CLAUDE_MCP} servers across all platforms"
    fi
}

# ─── EXECUTION ─────────────────────────────────────────────────────────────

echo "═══ Platform Health Sentinel ═══"
echo "Mode: $MODE | Platform: $PLATFORM | Root: $PROJECT_ROOT"
echo ""

# Run checks based on platform
case "$PLATFORM" in
    all)
        echo "── Shared Infrastructure ──"
        check_shared
        echo ""
        echo "── Claude Code ──"
        check_claude
        echo ""
        echo "── Gemini CLI ──"
        check_gemini
        echo ""
        echo "── Pi Agent ──"
        check_pi
        echo ""
        echo "── Cross-Platform ──"
        check_drift
        ;;
    claude)  check_shared; check_claude ;;
    gemini)  check_shared; check_gemini ;;
    pi)      check_shared; check_pi ;;
esac

# Output report
echo ""
echo "── Report ──"
echo -e "$REPORT"

# Auto-heal mode
if [ "$MODE" = "--heal" ] && [ -n "$HEAL_ACTIONS" ]; then
    echo ""
    echo "── Auto-Heal Actions ──"
    echo -e "$HEAL_ACTIONS" | while IFS= read -r action; do
        if [ -n "$action" ]; then
            echo "Executing: $action"
            eval "$action" 2>&1 | tail -3
        fi
    done
elif [ -n "$HEAL_ACTIONS" ]; then
    echo ""
    echo "── Suggested Fixes (run with --heal to auto-apply) ──"
    echo -e "$HEAL_ACTIONS"
fi

exit $EXIT_CODE
