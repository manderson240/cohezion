#!/usr/bin/env bash
# BMAD Method Recovery Script
#
# Reinstalls the BMAD Method if it's missing or corrupted,
# then restores Cohezion's custom agents and workflows.
#
# Usage:
#   ./scripts/ci/recover_bmad.sh           # Check and recover if needed
#   ./scripts/ci/recover_bmad.sh --force   # Force reinstall

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BMAD_DIR="$PROJECT_ROOT/_bmad"
CUSTOM_DIR="$PROJECT_ROOT/_bmad-custom"
MODULES="bmm,bmb,cis,gds,tea"
TOOLS="claude-code"

# Minimum expected file count (core + all modules)
MIN_FILES=200

# Custom Cohezion components that live alongside the BMAD install.
# These are restored from _bmad-custom/ after a fresh install.
CUSTOM_AGENTS=(
    "bmm/agents/auto-implementer.md"
    "bmm/agents/code-review-assistant.md"
    "bmm/agents/documentation-curator.md"
    "bmm/agents/security-monitor.md"
)

CUSTOM_WORKFLOWS=(
    "bmm/workflows/cohezion/security-monitoring/workflow.yaml"
)

CUSTOM_ROOT_FILES=(
    "agent-status.json"
)

check_bmad() {
    if [[ ! -d "$BMAD_DIR" ]]; then
        echo "BMAD directory missing: $BMAD_DIR"
        return 1
    fi

    local file_count
    file_count=$(find "$BMAD_DIR" -type f | wc -l)

    if [[ "$file_count" -lt "$MIN_FILES" ]]; then
        echo "BMAD installation incomplete: $file_count files (expected >= $MIN_FILES)"
        return 1
    fi

    # Check that all module directories exist
    for module in bmm bmb cis gds tea core; do
        if [[ ! -d "$BMAD_DIR/$module" ]]; then
            echo "BMAD module missing: $module"
            return 1
        fi
    done

    # Check custom agents exist
    for agent in "${CUSTOM_AGENTS[@]}"; do
        if [[ ! -f "$BMAD_DIR/$agent" ]]; then
            echo "Custom agent missing: $agent"
            return 1
        fi
    done

    echo "BMAD installation OK: $file_count files, all modules present, custom agents intact"
    return 0
}

backup_custom() {
    echo "Backing up custom components..."
    rm -rf "$CUSTOM_DIR"
    mkdir -p "$CUSTOM_DIR"

    for f in "${CUSTOM_AGENTS[@]}" "${CUSTOM_WORKFLOWS[@]}" "${CUSTOM_ROOT_FILES[@]}"; do
        if [[ -f "$BMAD_DIR/$f" ]]; then
            mkdir -p "$CUSTOM_DIR/$(dirname "$f")"
            cp "$BMAD_DIR/$f" "$CUSTOM_DIR/$f"
        fi
    done

    echo "  Backed up to $CUSTOM_DIR"
}

restore_custom() {
    if [[ ! -d "$CUSTOM_DIR" ]]; then
        echo "No custom backup found at $CUSTOM_DIR, skipping restore."
        return
    fi

    echo "Restoring custom components..."
    for f in "${CUSTOM_AGENTS[@]}" "${CUSTOM_WORKFLOWS[@]}" "${CUSTOM_ROOT_FILES[@]}"; do
        if [[ -f "$CUSTOM_DIR/$f" ]]; then
            mkdir -p "$BMAD_DIR/$(dirname "$f")"
            cp "$CUSTOM_DIR/$f" "$BMAD_DIR/$f"
            echo "  Restored: $f"
        fi
    done

    rm -rf "$CUSTOM_DIR"
    echo "Custom components restored."
}

install_bmad() {
    echo "Installing BMAD Method (modules: $MODULES)..."

    if ! command -v npx &>/dev/null; then
        echo "ERROR: npx not found. Install Node.js >= 20."
        exit 1
    fi

    # Back up custom components before removing
    if [[ -d "$BMAD_DIR" ]]; then
        backup_custom
        echo "Removing broken installation..."
        rm -rf "$BMAD_DIR"
    fi

    npx bmad-method install \
        --directory "$PROJECT_ROOT" \
        --modules "$MODULES" \
        --tools "$TOOLS" \
        --yes

    # Restore custom agents and workflows
    restore_custom

    echo "BMAD Method installed successfully with custom components."
}

main() {
    local force=false
    if [[ "${1:-}" == "--force" ]]; then
        force=true
    fi

    if $force; then
        echo "Force reinstall requested."
        install_bmad
    elif ! check_bmad; then
        install_bmad
    fi
}

main "$@"
