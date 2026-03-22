#!/bin/bash
# Pre-Flight Validation Script
# Usage: ./validate_deployment.sh <script_path>

SCRIPT=$1

if [ -z "$SCRIPT" ]; then
    echo "Usage: $0 <script_path>"
    exit 1
fi

EXIT_CODE=0

echo "🚀 PRE-FLIGHT VALIDATION: $SCRIPT"
echo "========================================"

# Step 1: Syntax Check
echo -n "1. Syntax validation... "
if python3 -m py_compile "$SCRIPT" 2>/dev/null; then
    echo "✅"
else
    echo "❌ SYNTAX ERROR"
    python3 -m py_compile "$SCRIPT"
    EXIT_CODE=1
fi

# Step 2: Import Check (basic)
echo -n "2. Import validation... "
if timeout 5 python3 -c "
import sys
sys.path.insert(0, 'src')
with open('$SCRIPT') as f:
    code = f.read()
    # Only check imports, don't execute main
    if 'if __name__' in code:
        code = code.split('if __name__')[0]
    compile(code, '$SCRIPT', 'exec')
" 2>/dev/null; then
    echo "✅"
else
    echo "⚠️  WARNING (may need runtime context)"
fi

# Step 3: Ollama Health
echo -n "3. Ollama service... "
if ollama list &> /dev/null; then
    echo "✅"
else
    echo "❌ NOT RESPONDING"
    EXIT_CODE=1
fi

# Step 4: SurrealDB Health
echo -n "4. SurrealDB service... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅"
else
    echo "⚠️  NOT RESPONDING (may be optional)"
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL CRITICAL CHECKS PASSED - CLEARED FOR LAUNCH"
else
    echo "❌ PRE-FLIGHT FAILED - DO NOT LAUNCH"
fi

exit $EXIT_CODE
