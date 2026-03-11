#!/usr/bin/env bash
# PostToolUse hook: Proactive vault keeper checks on .md files.
#
# Two modes, same script:
#   Write/Edit → per-file checks + vault-wide pulse (60s cooldown)
#   Read       → vault-wide pulse only (5 min cooldown)
#
# Any agent touching vault .md files gets health awareness injected.
# Alerts are prefixed with VAULT_KEEPER: so the agent can detect and act on them.

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Prevent parallel execution ──────────────────────────────────────────────
LOCK_FILE="/tmp/vault-keeper-$(id -u).lock"
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

# ── Extract tool info from stdin JSON ─────────────────────────────────────────
stdin_json=$(cat)

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

tool_name=$(echo "$stdin_json" | jq -r '.tool_name // empty' 2>/dev/null)
file_path=$(echo "$stdin_json" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Only run for .md files inside the vault
[[ -z "$file_path" ]] && exit 0
[[ "$file_path" != *.md ]] && exit 0
[[ "$file_path" != "$VAULT_ROOT"* ]] && exit 0

# Skip tooling directories
[[ "$file_path" == *"/obsidian-plugin/"* ]] && exit 0
[[ "$file_path" == *"/mcp-server/"* ]] && exit 0
[[ "$file_path" == *"/tools/"* ]] && exit 0
[[ "$file_path" == *"/.claude/"* ]] && exit 0

# ── Mode-specific cooldown ────────────────────────────────────────────────────
if [[ "$tool_name" == "Read" ]]; then
    COOLDOWN_FILE="/tmp/vault-keeper-read-$(id -u).last"
    COOLDOWN_SECONDS=300
else
    COOLDOWN_FILE="/tmp/vault-keeper-write-$(id -u).last"
    COOLDOWN_SECONDS=60
fi

if [[ -f "$COOLDOWN_FILE" ]]; then
    last_run=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    now=$(date +%s)
    if [[ -n "$last_run" ]] && (( now - last_run < COOLDOWN_SECONDS )); then
        exit 0
    fi
fi

date +%s > "$COOLDOWN_FILE"

# ── Vault-wide checks (both Read and Write/Edit) ─────────────────────────────
alerts=""

# 1. Inbox
inbox_count=$(find "$VAULT_ROOT/inbox" -name '*.md' ! -name '.base' ! -name '_index.md' ! -name '_template.md' 2>/dev/null | wc -l)
if [[ "$inbox_count" -gt 0 ]]; then
    alerts="${alerts}VAULT_KEEPER: inbox has ${inbox_count} items waiting for triage\n"
fi

# 2. Active projects with unchecked P0 tasks
while IFS= read -r file; do
    grep -q '^status: active' "$file" 2>/dev/null || continue
    in_p0=false
    p0_found=false
    while IFS= read -r line; do
        echo "$line" | grep -q '^### P0' && in_p0=true && continue
        if $in_p0; then
            echo "$line" | grep -q '^###' && break
            if echo "$line" | grep -q '^\- \[ \]'; then
                p0_found=true
                break
            fi
        fi
    done < "$file"
    if $p0_found; then
        rel="${file#$VAULT_ROOT/}"
        alerts="${alerts}VAULT_KEEPER: unchecked P0 tasks in ${rel}\n"
    fi
done < <(find "$VAULT_ROOT/projects" -name '*.md' ! -name '_index.md' ! -name '_template.md' 2>/dev/null | sort)

# ── Per-file checks (Write/Edit only) ────────────────────────────────────────
if [[ "$tool_name" != "Read" && -f "$file_path" ]]; then
    rel_path="${file_path#$VAULT_ROOT/}"
    dir_name="${rel_path%%/*}"

    # 2. Frontmatter
    first_line=$(head -1 "$file_path" 2>/dev/null)
    case "$dir_name" in
        concepts|papers|decisions|patterns|experiments|projects|lessons)
            if [[ "$first_line" != "---" ]]; then
                alerts="${alerts}VAULT_KEEPER: note missing frontmatter — ${rel_path}\n"
            else
                tags_line=$(grep '^tags:' "$file_path" 2>/dev/null | head -1)
                if [[ -n "$tags_line" ]] && ! echo "$tags_line" | grep -q '\['; then
                    alerts="${alerts}VAULT_KEEPER: note has tags as string (should be array) — ${rel_path}\n"
                fi
            fi
            ;;
    esac

    # 3. Inbound links (expensive grep -rl — separate 5-minute cooldown)
    LINKS_COOLDOWN_FILE="/tmp/vault-keeper-links-$(id -u).last"
    run_links_check=true
    if [[ -f "$LINKS_COOLDOWN_FILE" ]]; then
        links_last=$(cat "$LINKS_COOLDOWN_FILE" 2>/dev/null)
        links_now=$(date +%s)
        if [[ -n "$links_last" ]] && (( links_now - links_last < 300 )); then
            run_links_check=false
        fi
    fi
    if $run_links_check; then
        basename_md="${file_path##*/}"
        name="${basename_md%.md}"
        if [[ "$name" != "_template" && "$name" != "_index" && "$name" != "MOC-"* ]]; then
            inbound=$(grep -rl "\[\[.*${name}" "$VAULT_ROOT/cortex/" "$VAULT_ROOT/sensory/" "$VAULT_ROOT/prefrontal/" "$VAULT_ROOT/cerebellum/" "$VAULT_ROOT/motor/" 2>/dev/null | grep -v "$file_path" | wc -l)
            if [[ "$inbound" -eq 0 ]]; then
                alerts="${alerts}VAULT_KEEPER: new note has no inbound links — ${rel_path}\n"
            fi
        fi
        date +%s > "$LINKS_COOLDOWN_FILE"
    fi

    # 4. Canvas nudge — high link density suggests visual mapping
    outbound=$(grep -coh '\[\[[^]]*\]\]' "$file_path" 2>/dev/null | awk '{s+=$1} END{print s+0}')
    canvas_path="${file_path%.md}.canvas"
    if [[ "$outbound" -ge 10 && ! -f "$canvas_path" ]]; then
        alerts="${alerts}VAULT_KEEPER: note has ${outbound} outbound links — consider a companion .canvas to visualize relationships\n"
    fi

    # 5. Callout nudge — decisions and lessons benefit from structured callouts
    case "$dir_name" in
        decisions|lessons|patterns)
            if ! grep -q '> \[!' "$file_path" 2>/dev/null; then
                case "$dir_name" in
                    decisions) alerts="${alerts}VAULT_KEEPER: decision has no callouts — consider > [!warning] for consequences, > [!tip] for rationale\n" ;;
                    lessons)   alerts="${alerts}VAULT_KEEPER: lesson has no callouts — consider > [!danger] for the mistake, > [!success] for the fix\n" ;;
                    patterns)  alerts="${alerts}VAULT_KEEPER: pattern has no callouts — consider > [!example] for code, > [!warning] for anti-patterns\n" ;;
                esac
            fi
            ;;
    esac

    # 6. Alias nudge — concepts benefit from alternative names
    if [[ "$dir_name" == "concepts" && "$name" != "_template" && "$name" != "_index" && "$name" != "MOC-"* ]]; then
        if ! grep -q '^aliases:' "$file_path" 2>/dev/null; then
            alerts="${alerts}VAULT_KEEPER: concept has no aliases — consider adding aliases: [\"alt name\"] for discoverability\n"
        fi
    fi
fi

# ── Output alerts ─────────────────────────────────────────────────────────────
if [[ -n "$alerts" ]]; then
    echo -e "$alerts"
fi

exit 0
