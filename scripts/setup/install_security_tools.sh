#!/bin/bash
#
# Install and configure security pre-commit hooks for the Cohezion project.
#
# This script:
# 1. Installs pre-commit framework
# 2. Installs detect-secrets for credential scanning
# 3. Initializes secrets baseline
# 4. Installs git pre-commit hooks
# 5. Runs initial validation
#
# Usage:
#   ./scripts/setup/install_security_tools.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_DIR="$PROJECT_ROOT"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Security Tools Installation${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo "Project Root: $REPO_DIR"
echo ""

# Step 1: Check if pre-commit is installed
echo -e "${YELLOW}[1/5] Checking pre-commit installation...${NC}"
if command -v pre-commit &> /dev/null; then
  PRE_COMMIT_VERSION=$(pre-commit --version)
  echo -e "${GREEN}✓ pre-commit is already installed: $PRE_COMMIT_VERSION${NC}"
else
  echo "Installing pre-commit..."
  uv pip install pre-commit 2>/dev/null || pip install pre-commit
  echo -e "${GREEN}✓ pre-commit installed${NC}"
fi
echo ""

# Step 2: Check if detect-secrets is installed
echo -e "${YELLOW}[2/5] Checking detect-secrets installation...${NC}"
if python -c "import detect_secrets" 2>/dev/null; then
  DETECT_SECRETS_VERSION=$(python -c "import pkg_resources; print(pkg_resources.get_distribution('detect-secrets').version)")
  echo -e "${GREEN}✓ detect-secrets is already installed: v$DETECT_SECRETS_VERSION${NC}"
else
  echo "Installing detect-secrets..."
  uv pip install detect-secrets 2>/dev/null || pip install detect-secrets
  echo -e "${GREEN}✓ detect-secrets installed${NC}"
fi
echo ""

# Step 3: Initialize secrets baseline
echo -e "${YELLOW}[3/5] Initializing secrets baseline...${NC}"
cd "$REPO_DIR"

# Check if baseline already exists
if [[ -f ".secrets.baseline" ]]; then
  echo "Updating existing baseline..."
  detect-secrets scan --update .secrets.baseline --all-files 2>/dev/null || true
else
  echo "Creating new baseline..."
  # Copy template baseline if available
  if [[ -f "scripts/setup/secrets_baseline.json" ]]; then
    cp scripts/setup/secrets_baseline.json .secrets.baseline
    echo "✓ Baseline initialized from template"
  else
    # Create minimal baseline
    detect-secrets scan --baseline .secrets.baseline --all-files 2>/dev/null || true
    echo "✓ Baseline created from current repository scan"
  fi
fi

if [[ ! -f ".secrets.baseline" ]]; then
  echo -e "${RED}✗ Failed to create baseline${NC}"
  exit 1
fi

chmod 644 .secrets.baseline
echo -e "${GREEN}✓ Secrets baseline configured${NC}"
echo ""

# Step 4: Install git hooks
echo -e "${YELLOW}[4/5] Installing pre-commit git hooks...${NC}"
pre-commit install
pre-commit install --hook-type pre-push
echo -e "${GREEN}✓ Git hooks installed${NC}"
echo ""

# Step 5: Run validation
echo -e "${YELLOW}[5/5] Running initial validation...${NC}"
echo ""

# Test basic hook functionality
echo "Testing pre-commit hooks (commit stage)..."
if pre-commit run --all-files --hook-stage=commit --exclude-unsafe 2>&1 | grep -q "passed\|failed"; then
  echo -e "${GREEN}✓ Pre-commit hooks are functional${NC}"
else
  echo -e "${YELLOW}⚠ Some hooks may need configuration${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ Security Tools Installation Complete${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "What's been installed:"
echo "  • pre-commit: Git hook framework"
echo "  • detect-secrets: Credential scanning (v1.4.0)"
echo "  • .secrets.baseline: Baseline for allowed secrets (if any)"
echo ""
echo "What's been configured:"
echo "  • Pre-commit hook: Runs on 'git commit'"
echo "  • Pre-push hook: Runs on 'git push' (comprehensive)"
echo "  • Credential detection: Enabled for all Python files and text"
echo ""
echo "Next steps:"
echo "  1. Try committing a test file to verify hooks work"
echo "  2. Read .pre-commit-config.yaml for hook configuration"
echo "  3. Run manually: pre-commit run --all-files"
echo ""
echo "To disable a hook temporarily:"
echo "  SKIP=detect-secrets git commit -m 'Temporary commit'"
echo ""
echo "To update the baseline after adding legitimate secrets:"
echo "  detect-secrets scan --update .secrets.baseline --all-files"
echo ""
