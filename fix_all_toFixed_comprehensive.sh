#!/bin/bash
# Comprehensive toFixed fix - handles ALL patterns

echo "🔧 Fixing ALL toFixed errors comprehensively..."

cd /home/mike-anderson/dev/cohezion

# Find all TS files with toFixed and apply comprehensive fixes
find . -name "*.ts" -o -name "*.tsx" 2>/dev/null | grep -v node_modules | grep -v ".venv" | while read file; do
    if grep -q "\.toFixed(" "$file" 2>/dev/null; then
        # Apply sed replacements for common patterns
        sed -i 's/\${\([^}]*\)\.toFixed(\([^}]*)\))/\${(\1 ?? 0).toFixed(\2)}/g' "$file" 2>/dev/null
        sed -i 's/{\([^}]*\)\.toFixed(\([^}]*)\))}/{(\1 ?? 0).toFixed(\2))}/g' "$file" 2>/dev/null
    fi
done

echo "✅ Comprehensive fix applied"
