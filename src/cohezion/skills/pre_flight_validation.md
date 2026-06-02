---
name: pre_flight_validation
description: Preventing false starts in autonomous system launches through systematic
  pre-flight validation. Ensures code compiles, imports resolve, and critical dependencies
  are met before claiming "launch successful."
keywords:
- dependency checks
- dry run
- fail fast
- fail_fast
- flight
- import resolution
- persistent_quality
- pre
- r_zero
- syntax validation
- validation
---

# SKILL: PRE_FLIGHT_VALIDATION_PRIME

## DOMAIN EXPERTISE
Preventing false starts in autonomous system launches through systematic pre-flight validation. Ensures code compiles, imports resolve, and critical dependencies are met before claiming "launch successful."

## KEY TEXTS & CONCEPTS
- **Syntax Validation**: `python -m py_compile` catches syntax errors before runtime
- **Import Resolution**: Verify all imports load without ModuleNotFoundError
- **Dependency Checks**: Confirm external services (Ollama, SurrealDB) are responsive
- **Dry Run**: Test with minimal input before full execution
- **Fail Fast**: Catch errors in development, not production

## INSTRUCTION

### 1. Pre-Flight Checklist (Run BEFORE launch)

```bash
#!/bin/bash
# validate_deployment.sh
# Usage: ./validate_deployment.sh <script_path>

SCRIPT=$1
EXIT_CODE=0

echo "🚀 PRE-FLIGHT VALIDATION"
echo "========================"

# Step 1: Syntax Check
echo -n "1. Syntax validation... "
if python3 -m py_compile "$SCRIPT" 2>/dev/null; then
    echo "✅"
else
    echo "❌ SYNTAX ERROR"
    python3 -m py_compile "$SCRIPT"
    EXIT_CODE=1
fi

# Step 2: Import Check
echo -n "2. Import validation... "
if python3 -c "import sys; sys.path.insert(0, 'src'); exec(open('$SCRIPT').read().split('if __name__')[0])" 2>/dev/null; then
    echo "✅"
else
    echo "❌ IMPORT ERROR"
    python3 -c "import sys; sys.path.insert(0, 'src'); exec(open('$SCRIPT').read().split('if __name__')[0])"
    EXIT_CODE=1
fi

# Step 3: Type Checking (if mypy available)
if command -v mypy &> /dev/null; then
    echo -n "3. Type checking... "
    if mypy "$SCRIPT" --ignore-missing-imports 2>/dev/null; then
        echo "✅"
    else
        echo "⚠️  Type issues found (non-blocking)"
    fi
fi

# Step 4: Dependency Health
echo -n "4. Ollama service... "
if ollama list &> /dev/null; then
    echo "✅"
else
    echo "❌ NOT RESPONDING"
    EXIT_CODE=1
fi

echo -n "5. SurrealDB service... "
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅"
else
    echo "⚠️  NOT RESPONDING (may be optional)"
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED - CLEARED FOR LAUNCH"
else
    echo "❌ PRE-FLIGHT FAILED - DO NOT LAUNCH"
fi

exit $EXIT_CODE
```

### 2. Integration with Launch Process

```bash
# BEFORE: Blind launch (false starts)
nohup python script.py > logs/output.log 2>&1 &

# AFTER: Validated launch (reliable)
if ./validate_deployment.sh script.py; then
    nohup uv run python script.py > logs/output.log 2>&1 &
    echo "✅ Launched successfully"
else
    echo "❌ Pre-flight checks failed. Fix errors before launch."
    exit 1
fi
```

### 3. Python Module Template

Always include this header in new Python modules:

```python
#!/usr/bin/env python3
"""
Module: my_module.py
Description: What this does
Pre-flight: ./validate_deployment.sh scripts/my_module.py
"""

# Standard library imports
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
import numpy as np

# Local imports
from cohezion.module import Component

# Type checking
if __name__ != "__main__":
    # Verify imports work
    pass

# ... rest of code ...
```

### 4. Automated CI/CD Integration

Add to `.github/workflows/pre-flight.yml`:

```yaml
name: Pre-Flight Validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Syntax check all Python files
        run: find . -name "*.py" -exec python3 -m py_compile {} \;
      - name: Type check with mypy
        run: mypy src/ --ignore-missing-imports
```

## VERSION
v1.0

## SEE ALSO
- FAIL_FAST_PRIME (Learning 57)
- PERSISTENT_QUALITY_PRIME
- R_ZERO_PRIME (difficulty should decrease)
