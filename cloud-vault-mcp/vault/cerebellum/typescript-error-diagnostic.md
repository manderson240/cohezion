---
title: TypeScript Error Diagnostic - Patterns & Quick Fixes
date: 2026-02-17
status: active
tags: [pattern, typescript, compilation, compound-engineering]
aspect: thinker
neural:
  activation: 0.84
  stage: mature
  synapse_in: 8
  synapse_out: 10
---

# TypeScript Error Diagnostic Pattern

**Reference guide for common TypeScript errors found in Phase 2, with quick fixes.**

---

## Error Category 1: TS2802 - Iterator/Downlevel Issues

**Problem**: Using Map/Set iteration with ES6 target

```
TS2802: Type 'Map<string, X>' can only be iterated through
        when using the '--downlevelIteration' flag or with a '--target' of 'es2015' or higher.
```

**Root Cause**:
```typescript
const map = new Map<string, Vector3>();
for (const [key, value] of map.entries()) {  // ← TS2802 error
```

**Quick Fix - Option A (Recommended)**:
In `tsconfig.json`:
```json
{
  "compilerOptions": {
    "downlevelIteration": true  // ← Add this line
  }
}
```

**Quick Fix - Option B**:
```json
{
  "compilerOptions": {
    "target": "ES2015"  // Change from ES6 to ES2015
  }
}
```

**Affected Files in Phase 2**:
- ThreeRenderer.ts (3 errors)
- ReasoningInference.ts (2 errors)
- SemanticContradictionDetector.ts (1 error)
- VaultBridge.ts (2 errors)
- DecisionExplorer.ts (1 error)

**Token Efficiency**: Fix tsconfig once → all 10 errors gone (2 min fix)

---

## Error Category 2: TS2339 - Missing Properties

**Problem**: Type definition missing required properties

```
TS2339: Property 'x' does not exist on type 'PaperNode'.
```

**Root Cause 1: ForceLayout accessing undefined properties**
```typescript
// TS2339: Properties x, y, z don't exist on PaperNode
node.x = position.x;  // ← Error
node.y = position.y;
node.z = position.z;
```

**Fix**:
In `src/types/Paper.ts`, add to PaperNode interface:
```typescript
export interface PaperNode {
  // ... existing fields
  x?: number;
  y?: number;
  z?: number;
}
```

**Root Cause 2: CascadeQueryResult missing length**
```typescript
if (cascadeResult.length > 0) {  // ← TS2339: length doesn't exist
```

**Fix**:
In `src/types/Decision.ts`, add to CascadeQueryResult:
```typescript
export interface CascadeQueryResult {
  // ... existing fields
  cascades: DecisionCascade[];

  // Add helper property for length checking
  get length(): number {
    return this.cascades.length;
  }
}
```

Or use array property directly:
```typescript
if (cascadeResult.cascades.length > 0) {  // ✓ No error
```

**Affected Files**:
- ForceLayout.ts (3 errors - x, y, z)
- DecisionExplorer.ts (2 errors - length)

---

## Error Category 3: TS2554 - Function Argument Mismatch

**Problem**: Function called with wrong number of arguments

```
TS2554: Expected 1 arguments, but got 2.
```

**Root Cause**: Function signature doesn't match call site

```typescript
// Function defined as:
function openModal(modal: Modal): void { }

// Called as:
openModal(myModal, extra);  // ← TS2554: extra argument
```

**Fix**: Either reduce arguments or update function signature:

```typescript
// Option 1: Remove extra argument
openModal(myModal);

// Option 2: Update function signature
function openModal(modal: Modal, options?: any): void { }
```

**Affected Files**:
- DecisionExplorer.ts (1 error at line 418)

---

## Error Category 4: TS2307 - Module Not Found

**Problem**: Import references non-existent file

```
TS2307: Cannot find module '../visualizations/CascadeTimeline'
        or its corresponding type declarations.
```

**Root Cause**: File doesn't exist or wrong path

```typescript
import { CascadeTimeline } from '../visualizations/CascadeTimeline';  // ← File missing
```

**Fix Options**:

1. **Create the missing file**:
   ```bash
   touch src/visualizations/CascadeTimeline.ts
   ```

2. **Fix the import path**:
   ```typescript
   // If file is in different location:
   import { CascadeTimeline } from '../ui/CascadeTimeline';
   ```

3. **Remove unused import**:
   ```typescript
   // If component not used, delete the import
   // delete: import { CascadeTimeline } from '...'
   ```

**Affected Files**:
- DecisionExplorer.ts (1 error at line 741)

---

## Quick Fix Priority for Phase 2

| Priority | Fix | Time | Impact |
|----------|-----|------|--------|
| 1 | Add `downlevelIteration: true` to tsconfig.json | 2 min | Fixes 10 errors |
| 2 | Add x,y,z to PaperNode interface | 3 min | Fixes 3 errors |
| 3 | Add length property to CascadeQueryResult | 2 min | Fixes 2 errors |
| 4 | Fix DecisionExplorer function call | 3 min | Fixes 1 error |
| 5 | Create/fix CascadeTimeline import | 5 min | Fixes 1 error |
| **Total** | **All 16 errors fixed** | **~15 min** | **0 compilation errors** |

---

## Verification After Fixes

```bash
# Run TypeScript compiler
npx tsc --noEmit

# Should output: 0 errors
# Build
npm run build

# Should succeed
```

---

## Prevention in Phase 3+

### Code Review Checklist
- [ ] tsconfig.json includes necessary compiler options for iteration
- [ ] Type definitions include all accessed properties
- [ ] Function signatures match call sites
- [ ] All imports reference existing files
- [ ] Unused imports removed

### CI/CD Integration
```bash
# In build pipeline:
npm run lint    # Catch errors early
npx tsc --noEmit --noEmitOnError  # Fail if errors exist
npm run build   # Verify build succeeds
```

---

## Common TypeScript Mistakes to Avoid

❌ **Mistake 1**: Ignoring TypeScript errors before committing
```bash
# WRONG: Commit code with TS errors
git commit -m "Add feature" # Still has TS2339 errors
```

✓ **Correct**: Fix all errors first
```bash
npx tsc --noEmit  # Check for errors
# Fix errors
npm run build     # Verify build succeeds
git commit        # Only then commit
```

❌ **Mistake 2**: Using `as any` instead of fixing types
```typescript
// WRONG: Bypassing type safety
const node = someValue as any;
```

✓ **Correct**: Define proper types
```typescript
interface Node {
  x: number;
  y: number;
}
const node: Node = someValue;
```

---

## Related Patterns

- [[service-initialization-checklist]] (Preventing integration gaps)
- [[2026-02-17-phase-2-service-initialization-gap-discovery]] (Phase 2 post-mortem)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
- [[2026-02-14-wave-1-overnight-completion-report]]
- [[2026-02-14-compound-engineering-team-execution-retrospective]]
