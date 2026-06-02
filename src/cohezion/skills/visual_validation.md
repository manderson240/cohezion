---
name: visual_validation
description: You are a specialist in visual UI validation - automated browser testing,
  UX auditing, and interactive integrity verification.
keywords:
- api_patterns
- browser subagent
- modal cycle
- screenshot evidence
- state verification
- testing
- validation
- visual
---

# SKILL: VISUAL_VALIDATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **visual UI validation** - automated browser testing, UX auditing, and interactive integrity verification.

## KEY CONCEPTS
- **Browser Subagent** - Autonomous UI testing
- **Modal Cycle** - Open/close validation
- **State Verification** - Count and content checks
- **Screenshot Evidence** - Visual proof capture

## INSTRUCTION

### 1. Browser Subagent Test
```
Use the browser_subagent tool with a detailed task:

1. Navigate to the target URL
2. Wait for page load
3. Verify header/title elements
4. Check dynamic counts (stats)
5. Click interactive elements (tabs, cards)
6. Test modal open/close cycles
7. Capture screenshots as evidence
8. Report findings
```

### 2. Visual Test Checklist
| Test | Verification |
|------|--------------|
| Page Load | Title matches expected |
| Stats Display | Counts are numeric |
| Tab Switching | Active state changes |
| Card Click | Modal opens |
| Modal Close | Returns to list |
| Content Render | Text/JSON displays |

### 3. Evidence Capture
- Screenshots saved to `.system_generated/click_feedback/`
- Recording saved as `.webp` video
- Include in walkthroughs for proof

### 4. Example Task
```
Navigate to http://localhost:8080 and:
1. Verify header shows "Title"
2. Check stats show counts
3. Click each tab
4. Open and close modals
5. Report any errors
```

## PATTERNS

| Pattern | Purpose |
|---------|---------|
| Modal Cycle | Test popup flow |
| Tab Navigation | Verify state changes |
| Dynamic Count | Validate API integration |

## SEE ALSO
- TESTING_PRIME.md
- API_PATTERNS_PRIME.md
