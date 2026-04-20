#!/bin/bash
#
# Cohezion Pi Features Demo
# Walks through all 0.67.2+ features with practical examples
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    Cohezion Pi 0.67.2+ Feature Demo                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# ============================================
# DEMO STEP 1: Version Check
# ============================================
print_section "Step 1: Version Check"

echo "Checking pi-coding-agent version..."
PI_VERSION=$(npm list @mariozechner/pi-coding-agent 2>/dev/null | grep pi-coding-agent | sed 's/.*@//' | head -1)

if [ -n "$PI_VERSION" ]; then
    print_success "Pi coding agent version: $PI_VERSION"
    if [[ "$PI_VERSION" =~ ^0\.67\. ]]; then
        print_success "Version 0.67.2+ confirmed ✓"
    else
        print_info "Consider upgrading to 0.67.2+ for new features"
    fi
else
    echo "⚠ Pi coding agent not installed in current directory"
fi

# ============================================
# DEMO STEP 2: JSON Validation
# ============================================
print_section "Step 2: Configuration Validation"

echo "Validating JSON configurations..."
python3 << 'PYTHON_EOF'
import json
import sys

files = [
    '.pi/settings.json',
    '.pi/keybindings.json', 
    'package.json'
]

all_valid = True
for f in files:
    try:
        with open(f) as fp:
            data = json.load(fp)
        print(f"✓ {f} - Valid JSON")
    except Exception as e:
        print(f"✗ {f} - Error: {e}")
        all_valid = False

sys.exit(0 if all_valid else 1)
PYTHON_EOF

if [ $? -eq 0 ]; then
    print_success "All configuration files valid"
else
    echo "✗ Configuration errors found"
    exit 1
fi

# ============================================
# DEMO STEP 3: Keybindings Demo
# ============================================
print_section "Step 3: Keybindings Configuration"

echo "Configured shortcuts in .pi/keybindings.json:"
echo ""
python3 << 'PYTHON_EOF'
import json

with open('.pi/keybindings.json') as f:
    data = json.load(f)

# Filter out metadata keys
shortcuts = {k: v for k, v in data.items() if not k.startswith('_')}

print(f"{'Action':<40} {'Shortcut'}")
print("-" * 60)
for action, keys in sorted(shortcuts.items()):
    key_str = ", ".join(keys) if isinstance(keys, list) else keys
    print(f"{action:<40} {key_str}")
PYTHON_EOF

echo ""
print_info "Try these in Kitty terminal:"
echo "  • super+n → New session"
echo "  • super+t → Open tree"
echo "  • super+k → Cancel/abort"

# ============================================
# DEMO STEP 4: Multi-Prompt Demo
# ============================================
print_section "Step 4: Multiple --append-system-prompt Demo"

echo "Example command that pi-cohezion.sh generates:"
echo ""
echo "  pi \\"
echo "    --append-system-prompt 'Cohezion project context...' \\"
echo "    --append-system-prompt 'FLUME-First rules...' \\"
echo "    --append-system-prompt 'Vault-First persistence...'"
echo ""

print_info "Each --append-system-prompt is separated by double newlines in the final prompt"
echo ""

# Show wrapper script
if [ -f "pi-cohezion.sh" ]; then
    echo "Wrapper script exists: pi-cohezion.sh"
    print_success "Executable: $(test -x pi-cohezion.sh && echo 'Yes' || echo 'No (run: chmod +x pi-cohezion.sh)')"
fi

# ============================================
# DEMO STEP 5: SDK Extension Demo
# ============================================
print_section "Step 5: SDK Inline Extension Factory"

echo "Example from .pi/examples/sdk-embedded.ts:"
echo ""
head -60 .pi/examples/sdk-embedded.ts | tail -50

echo ""
print_info "Run with: uv run tsx .pi/examples/sdk-embedded.ts"

# ============================================
# DEMO STEP 6: Settings Overview
# ============================================
print_section "Step 6: Settings Overview"

echo "Current configuration:"
echo ""
python3 << 'PYTHON_EOF'
import json

with open('.pi/settings.json') as f:
    data = json.load(f)

print(f"Version metadata: {data.get('_version', 'N/A')}")
print(f"Telemetry enabled: {data.get('enableInstallTelemetry', True)}")
print(f"Extensions loaded: {len(data.get('extensions', []))}")
for ext in data.get('extensions', []):
    print(f"  • {ext}")
print(f"Cohezion skills dir: {data.get('cohezion', {}).get('skillsDir', 'N/A')}")
print(f"Vault enabled: {data.get('cohezion', {}).get('vaultEnabled', False)}")
PYTHON_EOF

# ============================================
# DEMO STEP 7: File Summary
# ============================================
print_section "Step 7: Created/Updated Files"

echo "Configuration files:"
ls -la .pi/{settings.json,keybindings.json,FEATURES_0.67.2.md,RELEASE_HISTORY.md,APPEND_SYSTEM.md} 2>/dev/null | awk '{printf "  %-8s %s\n", $5, $9}'

echo ""
echo "Guide files:"
ls -la .pi/guides/*.md 2>/dev/null | awk '{printf "  %-8s %s\n", $5, $9}'

echo ""
echo "Example files:"
ls -la .pi/examples/*.ts 2>/dev/null | awk '{printf "  %-8s %s\n", $5, $9}'

echo ""
echo "Root scripts:"
ls -la pi-cohezion.sh package.json 2>/dev/null | awk '{printf "  %-8s %s\n", $5, $9}'

# ============================================
# DEMO COMPLETE
# ============================================
print_section "Demo Complete!"

echo "Next steps:"
echo ""
echo "  1. Start interactive session:"
echo -e "     ${GREEN}./pi-cohezion.sh${NC}"
echo ""
echo "  2. Run SDK example:"
echo -e "     ${GREEN}uv run tsx .pi/examples/sdk-embedded.ts${NC}"
echo ""
echo "  3. Read guides:"
echo -e "     ${GREEN}cat .pi/guides/00_QUICKSTART.md${NC}"
echo ""
echo "  4. View complete release history:"
echo -e "     ${GREEN}cat .pi/RELEASE_HISTORY.md${NC}"
echo ""
echo "All features documented in .pi/guides/"
echo ""
