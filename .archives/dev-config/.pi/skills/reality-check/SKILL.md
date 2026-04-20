---
name: reality-check
description: Prevent hallucination spirals with mandatory verification steps for syntax, imports, instantiation, and execution.
---

# Skill: Reality Check Protocol  
**Created:** 2026-04-11  
**Source:** Hallucination Recovery Session  
**Priority:** Critical

---

## Overview

This skill prevents the "hallucination spiral" by enforcing proactive reality verification before claiming feature completion. It is based on the critical learning from session 2026-04-11 where code claimed to be "working" when only imports succeeded.

---

## The Problem (What This Prevents)

### The Hallucination Spiral
```
1. Create file with code
2. Code imports without errors
3. Assume code works
4. Claim feature complete
5. Build on false foundation
6. Errors compound
7. Reality diverges from claims
```

### Symptoms of Hallucination
- Claims of massive completion percentages (>100%)
- Features "working" without test execution output
- Vague "ready for next phase" without concrete validation
- Excessive emojis instead of actual metrics
- Documentation claiming success before verification

---

## The Solution (Reality Check Protocol)

### Mandatory Verification Steps

#### Step 1: Syntax Verification
```bash
# Check file exists and has valid Python syntax
python -m py_compile src/module/file.py
echo "✅ Syntax OK"
```

#### Step 2: Import Verification
```bash
# Ensure imports work
uv run python -c "from cohezion.module.class import Class"
echo "✅ Import OK"
```

#### Step 3: Instantiation Verification
```bash
# Ensure class can be instantiated
uv run python -c "from cohezion.module.class import Class; c = Class()"
echo "✅ Instantiation OK"
```

#### Step 4: Method Verification
```bash
# Ensure critical methods exist
uv run python -c "
from cohezion.module.class import Class
c = Class()
assert hasattr(c, 'critical_method')
"
echo "✅ Methods OK"
```

#### Step 5: Execution Verification (MOST IMPORTANT)
```bash
# Actually run the code with real input
timeout 10 uv run python -c "
from cohezion.module.class import Class
c = Class()
result = c.run_actual_method('test_input')
assert result is not None
print('Result:', result)
"
echo "✅ Execution OK"
```

#### Step 6: Demo Verification
```bash
# Run the demo function if it exists
timeout 30 uv run python src/module/file.py 2>&1 | tail -20
echo "✅ Demo OK"
```

---

## Automated Reality Check Command

Add this function to `.pi/skills/reality-check/SKILL.md`:

```bash
reality_check() {
    local file=$1
    local class=$2
    local module=$3
    
    echo "=== REALITY CHECK: $file ==="
    
    # Step 1: Syntax
    python -m py_compile $file && echo "✅ Syntax OK" || echo "❌ Syntax FAIL"
    
    # Step 2-4: Import, Instantiation, Methods
    uv run python -c "
from $module import $class
c = $class()
print('✅ Import/Instantiation OK')
" 2>&1 || echo "❌ Import/Instantiation FAIL"
    
    # Step 5-6: Execution and Demo
    if grep -q "def demo" $file; then
        timeout 10 uv run python $file && echo "✅ Demo OK" || echo "❌ Demo FAIL"
    else
        echo "⚠️ No demo function found"
    fi
}
```

Usage:
```bash
reality_check "src/cohezion/swarm/my_module.py" "MyClass" "cohezion.swarm.my_module"
```

---

## Anti-Pattern Detection

### Check for These Warning Signs

| Warning Sign | Detection Method | Severity |
|--------------|------------------|----------|
| Percentage claims without metrics | grep -i "[0-9]\+%" | High |
| "Working" claims without test output | grep -i "✅.*work" | High |
| No demo runs in session | grep -c "timeout.*demo" | Medium |
| Ellipsis in __init__ | grep "def __init__" -A 5 | Critical |
| Vault exports without verification | Check before .md creation | Medium |

---

## Recovery Protocol

### When User Says "Recover from hallucination"

1. **Acknowledge immediately**
   ```
   "ACKNOWLEDGED. Implementing reality check."
   ```

2. **Stop all forward progress**
   - Cancel speculative code generation
   - Stop claiming completions
   - Document current actual state

3. **Verify existing claims**
   ```bash
   # For each claimed working module:
   uv run python -c "from module import Class; c=Class(); c.run()"
   ```

4. **Fix bugs found**
   - Document each bug found
   - Fix with surgical edits
   - Re-verify after fix

5. **Report honest status**
   - Files that exist
   - Tests that pass
   - Bugs found and fixed
   - Actual completion percentage

6. **Get user confirmation before continuing**
   - Show real status
   - Ask if recovery is complete
   - Only then proceed

---

## Integration with Skills

### Use This Skill When:
- Session exceeds 30 minutes
- Claiming >80% completion
- Creating new modules
- Before vault documentation
- User expresses concern about progress

### Combine With:
- `experiment-tracking` - Run experiments before claiming results
- `tdd-integration` - Write tests before implementation claims
- `production-dogfooding` - Use code before claiming production-ready

---

## Success Metrics

### For This Skill
- **Hallucination Prevention Rate:** >90%
- **False Claim Detection:** >95%
- **Bug Discovery Before Merge:** >80%
- **User Trust:** Maintained

### Session Metrics (Target)
- **Import Success:** 100%
- **Execution Success:** >95%
- **Demo Success:** >90%
- **Test Pass Rate:** >95%
- **Documentation Accuracy:** >98%

---

## Known Limitations

1. **Time Cost:** Reality checks add 10-30s per module
2. **Not Exhaustive:** May miss edge cases
3. **User Intervention:** Requires trigger from user
4. **False Negatives:** May flag working code as broken

---

## References

- **Retrospective:** `cloud-vault-mcp/vault/cortex/retrospective-hallucination-recovery-2026-04-11.md`
- **SurrealDB Export:** `surrealdb_export_retrospective_2026-04-11.json`
- **Session Learnings:** captured in vault under `session_learning` table

---

## Skill Application

### Quick Check (30 seconds)
```bash
# For a single file
timeout 10 uv run python -c "
from cohezion.module import Class
c = Class()
result = c.method()
print('✅ Working - result:', result[:50] if isinstance(result, str) else result)
"
```

### Full Protocol (2 minutes)
```bash
# Run full checklist for all new files
for file in $(git diff --name-only | grep '.py$'); do
    reality_check "$file"
done
```

---

## Example Output

### BEFORE (Hallucination)
```
✅ Parser v3 Validation Oracle - WORKS
✅ Unified Thinker - ACHIEVED 122% completion
✅ Triune Integration - COMPLETE
```

### AFTER (Reality Check)
```
=== REALITY CHECK RESULTS ===
✅ unified_thinker.py - Syntax OK, Import OK, Execution OK
   Note: Had bug (embed_dim uninitialized), FIXED
✅ parser_v3_validation_oracle.py - Syntax OK, Import OK, Execution OK
   Note: Method is parse_with_validation not fuzzy_parse
✅ triune_integration.py - Syntax OK, Import OK, Execution OK
   Demo: 10 recursive steps, HIHO coherence 0.50

Bugs Found: 2
Bugs Fixed: 2/2 (100%)
Honest Status: 3/3 modules working, 2 bugs fixed, tests needed
```

---

## Maintenance

This skill should be:
- **Reviewed:** After each major hallucination event
- **Updated:** With new detection methods
- **Practiced:** On small features before major work
- **Enforced:** By user for sessions >1 hour
