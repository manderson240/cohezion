#!/bin/bash
"""
Setup pre-commit hooks for credential and security scanning.

This script:
1. Installs pre-commit framework
2. Configures git pre-commit hooks
3. Initializes detect-secrets baseline
4. Validates hook configuration

Usage:
    bash scripts/setup_pre_commit_hooks.sh
"""

set -e

echo "Setting up pre-commit hooks for credential detection..."
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit framework..."
    pip install pre-commit
fi

# Check if detect-secrets is installed
if ! command -v detect-secrets &> /dev/null; then
    echo "Installing detect-secrets..."
    pip install detect-secrets
fi

echo "Installing git hooks..."
pre-commit install
pre-commit install --hook-type pre-push

echo ""
echo "Configuring detect-secrets baseline..."
if [ ! -f ".secrets.baseline" ]; then
    echo "Initializing .secrets.baseline..."
    detect-secrets scan > .secrets.baseline
    echo "✓ Created .secrets.baseline (initial scan)"
else
    echo "✓ .secrets.baseline already exists"
fi

echo ""
echo "Validating pre-commit configuration..."
pre-commit run --all-files --hook-stage commit || {
    echo "Note: Some hooks may need initial configuration."
    echo "This is normal on first setup."
}

echo ""
echo "✓ Pre-commit hooks setup complete!"
echo ""
echo "To manually run hooks:"
echo "  pre-commit run --all-files              # All checks, all files"
echo "  pre-commit run --all-files --hook-stage=commit  # Fast checks only"
echo "  pre-commit run --all-files --hook-stage=push    # Safety checks only"
echo ""
echo "To update secrets baseline after adding new legitimate secrets:"
echo "  detect-secrets scan > .secrets.baseline"
echo ""
echo "Hooks installed:"
echo "  - On commit: Quick syntax checks, credential detection"
echo "  - On push: Safety checks, security scanning"
echo ""
