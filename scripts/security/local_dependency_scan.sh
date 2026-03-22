#!/usr/bin/env bash
# Cohezion Local Dependency Security Scan
# Automated via cron to identify vulnerable packages

set -uo pipefail

PROJECT_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$PROJECT_DIR/logs"
REPORT_DIR="$PROJECT_DIR/reports/security"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/dependency_scan_$TIMESTAMP.md"

mkdir -p "$LOG_DIR" "$REPORT_DIR"

echo "# Cohezion Dependency Security Report" > "$REPORT_FILE"
echo "**Date**: $(date -Iseconds)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

cd "$PROJECT_DIR"

# Ensure tools are in PATH
export PATH=$PATH:/usr/local/bin:/usr/bin:/bin:/home/mike-anderson/.local/bin

# 1. Python (Root)
echo "## 🐍 Python (Root)" >> "$REPORT_FILE"
echo '```text' >> "$REPORT_FILE"
# uv audit checks the project's lockfile
uv audit >> "$REPORT_FILE" 2>&1 || true
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. Python (Cloud Vault MCP)
echo "## 🔐 Cloud Vault MCP" >> "$REPORT_FILE"
if [ -d "cloud-vault-mcp" ]; then
    cd cloud-vault-mcp
    echo '```text' >> "$REPORT_FILE"
    # uv audit checks the project's lockfile
    uv audit >> "$REPORT_FILE" 2>&1 || true
    echo '```' >> "$REPORT_FILE"
    cd ..
else
    echo "⚠️  Directory cloud-vault-mcp not found" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 3. Node.js (Plugins)
echo "## 🎨 Node.js Plugins" >> "$REPORT_FILE"

for plugin in "cohezion-3d-graph-plugin" "hyperdim-viz-plugin"; do
    echo "### $plugin" >> "$REPORT_FILE"
    if [ -d "$plugin" ]; then
        cd "$plugin"
        echo '```text' >> "$REPORT_FILE"
        # npm audit checks for vulnerabilities in installed packages
        npm audit >> "$REPORT_FILE" 2>&1 || true
        echo '```' >> "$REPORT_FILE"
        cd ..
    else
        echo "⚠️  Directory $plugin not found" >> "$REPORT_FILE"
    fi
    echo "" >> "$REPORT_FILE"
done

# Cleanup old reports (keep last 30)
find "$REPORT_DIR" -name "dependency_scan_*.md" -mtime +30 -delete 2>/dev/null || true

# Summary output to log
echo "[$(date -Iseconds)] Cohezion Dependency Scan Complete. Report: $REPORT_FILE" >> "$LOG_DIR/cron_runs.log"
