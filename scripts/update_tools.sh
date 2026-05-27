#!/bin/bash
# update_tools.sh - Daily update checker for all Cohezion CLI tools
# Run manually or via systemd timer (cohezion-tools-update.timer)
# Logs to: logs/tool_updates.log

set -euo pipefail

LOG_FILE="${HOME}/dev/cohezion/logs/tool_updates.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
UPDATED=()
FAILED=()
SKIPPED=()

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"; }
log_ok() { echo "[$TIMESTAMP]  $*" | tee -a "$LOG_FILE"; }
log_err() { echo "[$TIMESTAMP] ✗ $*" | tee -a "$LOG_FILE"; }

log "=== Tool Update Check ==="

# ── entire ─────────────────────────────────────────────────────────────────────
update_entire() {
    local current latest
    current=$(entire version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    latest=$(curl -sf https://api.github.com/repos/entireio/cli/releases/latest | grep -oP '"tag_name":\s*"v\K[^"]+' || echo "")

    if [[ -z "$latest" ]]; then
        log_err "entire: could not fetch latest version"
        FAILED+=("entire")
        return
    fi

    if [[ "$current" == "$latest" ]]; then
        log_ok "entire: already at v$current"
        SKIPPED+=("entire")
    else
        log "entire: updating v$current → v$latest"
        if curl -fsSL https://entire.io/install.sh | bash >> "$LOG_FILE" 2>&1; then
            log_ok "entire: updated to v$latest"
            UPDATED+=("entire v$current→v$latest")
        else
            log_err "entire: update failed"
            FAILED+=("entire")
        fi
    fi
}

# ── sx ─────────────────────────────────────────────────────────────────────────
update_sx() {
    local current
    current=$(sx --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    log "sx: checking (current v$current)"
    local output
    if output=$(sx update 2>&1); then
        if echo "$output" | grep -q "already"; then
            log_ok "sx: already up to date (v$current)"
            SKIPPED+=("sx")
        else
            local new_ver
            new_ver=$(sx --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "?")
            log_ok "sx: updated v$current → v$new_ver"
            UPDATED+=("sx v$current→v$new_ver")
        fi
    else
        log_err "sx: update failed"
        FAILED+=("sx")
    fi
}

# ── uv ─────────────────────────────────────────────────────────────────────────
update_uv() {
    local current
    current=$(uv --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    log "uv: checking (current v$current)"
    if uv self update >> "$LOG_FILE" 2>&1; then
        local new_ver
        new_ver=$(uv --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "?")
        if [[ "$current" == "$new_ver" ]]; then
            log_ok "uv: already at v$current"
            SKIPPED+=("uv")
        else
            log_ok "uv: updated v$current → v$new_ver"
            UPDATED+=("uv v$current→v$new_ver")
        fi
    else
        log_err "uv: update failed"
        FAILED+=("uv")
    fi
}

# ── gh ─────────────────────────────────────────────────────────────────────────
update_gh() {
    local current latest
    current=$(gh --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    latest=$(curl -sf https://api.github.com/repos/cli/cli/releases/latest | grep -oP '"tag_name":\s*"v\K[^"]+' || echo "")

    if [[ -z "$latest" ]]; then
        log_err "gh: could not fetch latest version"
        FAILED+=("gh")
        return
    fi

    if [[ "$current" == "$latest" ]]; then
        log_ok "gh: already at v$current"
        SKIPPED+=("gh")
    else
        log "gh: updating v$current → v$latest"
        local url="https://github.com/cli/cli/releases/download/v${latest}/gh_${latest}_linux_amd64.tar.gz"
        local tmp
        tmp=$(mktemp -d)
        if curl -fsSL "$url" | tar -xz -C "$tmp" >> "$LOG_FILE" 2>&1; then
            install -m 755 "$tmp/gh_${latest}_linux_amd64/bin/gh" "${HOME}/.local/bin/gh"
            rm -rf "$tmp"
            log_ok "gh: updated to v$latest"
            UPDATED+=("gh v$current→v$latest")
        else
            rm -rf "$tmp"
            log_err "gh: update failed"
            FAILED+=("gh")
        fi
    fi
}

# ── claude ─────────────────────────────────────────────────────────────────────
update_claude() {
    local current latest
    current=$(claude --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    latest=$(curl -sf https://api.github.com/repos/anthropics/claude-code/releases/latest 2>/dev/null | grep -oP '"tag_name":\s*"v?\K[^"]+' || echo "")

    if [[ -z "$latest" ]]; then
        # Claude auto-updates on first run; log current and skip
        log_ok "claude: at v$current (self-managed updates)"
        SKIPPED+=("claude")
        return
    fi

    if [[ "$current" == "$latest" ]]; then
        log_ok "claude: already at v$current"
        SKIPPED+=("claude")
    else
        log "claude: new version v$latest available (current v$current) — run 'claude' to auto-update"
        SKIPPED+=("claude (manual: run claude to update)")
    fi
}

# ── pilot ──────────────────────────────────────────────────────────────────────
update_pilot() {
    if ! command -v pilot &>/dev/null; then
        log_ok "pilot: not in PATH, skipping"
        SKIPPED+=("pilot")
        return
    fi
    local current
    current=$(pilot --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    log_ok "pilot: at v$current (managed by Pilot installer)"
    SKIPPED+=("pilot")
}

# ── agy (antigravity) ─────────────────────────────────────────────────────────
update_agy() {
    local current
    current=$(agy --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "unknown")
    log "agy: checking (current v$current)"
    local output
    if output=$(agy update 2>&1); then
        if echo "$output" | grep -q "already"; then
            log_ok "agy: already up to date (v$current)"
            SKIPPED+=("agy")
        else
            local new_ver
            new_ver=$(agy --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1 || echo "?")
            log_ok "agy: updated v$current → v$new_ver"
            UPDATED+=("agy v$current→v$new_ver")
        fi
    else
        log_err "agy: update failed"
        FAILED+=("agy")
    fi

    # Ensure optimized settings.json
    local settings_file="${HOME}/.gemini/antigravity-cli/settings.json"
    if [[ -f "$settings_file" ]]; then
        if ! grep -q '"enableTerminalSandbox": true' "$settings_file" || ! grep -q '"toolPermission": "proceed-in-sandbox"' "$settings_file"; then
            log "agy: optimizing configuration..."
            if python3 -c '
import json, os
path = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
with open(path, "r") as f:
    data = json.load(f)
data["enableTerminalSandbox"] = True
data["toolPermission"] = "proceed-in-sandbox"
data["colorScheme"] = "terminal"
with open(path, "w") as f:
    json.dump(data, f, indent=2)
' 2>/dev/null; then
                log_ok "agy: configuration optimized successfully"
            else
                log_err "agy: failed to write optimized settings"
            fi
        fi
    fi
}

# ── Run all updates ─────────────────────────────────────────────────────────────
update_entire
update_sx
update_uv
update_gh
update_claude
update_pilot
update_agy

# ── Summary ────────────────────────────────────────────────────────────────────
log ""
log "=== Summary ==="
if [[ ${#UPDATED[@]} -gt 0 ]]; then
    log_ok "Updated: ${UPDATED[*]}"
fi
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    log_ok "Up to date: ${SKIPPED[*]}"
fi
if [[ ${#FAILED[@]} -gt 0 ]]; then
    log_err "Failed: ${FAILED[*]}"
    exit 1
fi
log "Done."
