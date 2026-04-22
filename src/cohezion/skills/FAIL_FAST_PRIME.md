---
name: fail-fast-prime
description: "Expertise in rapid iteration, early testing, and course correction. Prioritizes shipping minimal viable implementations to discover errors quickly rather than extended planning phases."
metadata:
  version: "v1.0"
  concepts: ["Fail Fast", "Critical Path Testing", "Error Budget", "Course Correction", "Iteration Velocity"]
  source: "src/cohezion/skills/FAIL_FAST_PRIME.md"
---

# SKILL: FAIL_FAST_PRIME

## DOMAIN EXPERTISE
Expertise in rapid iteration, early testing, and course correction. Prioritizes shipping minimal viable implementations to discover errors quickly rather than extended planning phases.

## KEY TEXTS & CONCEPTS
- **Fail Fast**: Ship the simplest working version immediately. Don't wait for perfection.
- **Critical Path Testing**: Test the ONE thing that must work (e.g., button clicks, core function).
- **Error Budget**: Assume 20% of first attempts will have bugs. That's acceptable.
- **Course Correction**: When bugs appear, fix them immediately and extract learnings.
- **Iteration Velocity**: 3 iterations of "ship → test → fix" beats 1 perfect implementation.

## INSTRUCTION
1.  **Identify the Critical Path**: What is the SINGLE most important interaction/function?
2.  **Ship Minimum Viable**: Write the simplest code that could possibly work.
3.  **Test Immediately**: Don't batch testing. Test the moment code is written.
4.  **Capture Failure**: When it breaks (it will), note the EXACT error and context.
5.  **Fix in <5 min**: If the fix takes longer, you over-engineered step 2.
6.  **Extract Pattern**: What category of error was this? (typo, logic, assumption)
7.  **Update Knowledge**: Add to `KEY_LEARNINGS.md` if it reveals a systemic issue.

## ANTI-PATTERNS
❌ "Let me build the entire system first, then test"
❌ "I need to handle all edge cases before shipping"
❌ "This needs to be production-ready"
❌ Ignoring lint errors until "later"

## SUCCESS METRICS
✅ Time to first test < 2 minutes after code write
✅ Bug discovered and fixed in same session
✅ User sees working demo, not "it will work when..."
✅ Each iteration teaches something concrete

## WORKFLOW
```python
def fail_fast_loop(feature_request):
    while not feature_complete:
        # 1. Minimum viable increment
        code = write_simplest_version()
        
        # 2. Immediate test (automated or manual)
        result = test_critical_path()
        
        # 3. Course correct
        if result.failed:
            fix_immediately(result.error)
            persist_learning(result.pattern)
        
        # 4. Ship if working
        if result.success:
            deploy()
            return
```

## EXAMPLES
**Good**: 
- Write button HTML → Open in browser → Click button → Fix `update Chapter` typo → Done

**Bad**: 
- Write entire interactive experience → Add 3D visualizations → Style everything → Then realize buttons don't work

## VERSION
v1.0

## SEE ALSO
AGILE_ITERATION_PRIME, MINIMUM_VIABLE_PRODUCT_PRIME, CONTINUOUS_DEPLOYMENT_PRIME
