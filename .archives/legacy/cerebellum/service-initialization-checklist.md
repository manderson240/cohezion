---
title: Service Initialization Checklist - Reusable Pattern
date: 2026-02-17
status: active
tags: [pattern, architecture, obsidian-plugin, lifecycle, compound-engineering]
aspect: thinker
neural:
  activation: 0.87
  stage: mature
  synapse_in: 5
  synapse_out: 11
---

# Service Initialization Checklist

**Use this checklist when adding a new service to an Obsidian plugin to prevent integration gaps.**

## Quick Reference

```
Phase 1: Design Service ✓ → Phase 2: Wire to Plugin → Phase 3: Connect Events → Phase 4: Test Real Functionality
```

---

## Phase 1: Service Design ✓

- [ ] **Service class** created with clear public interface
- [ ] **Constructor** accepts required dependencies (App, Vault, etc.)
- [ ] **Lifecycle methods** defined:
  - `start()` or `initialize()` - Begin operations
  - `stop()` or `cleanup()` - Graceful shutdown
- [ ] **Type definitions** complete (TypeScript interfaces)
- [ ] **Error handling** in place (what happens if setup fails?)

**Example**:
```typescript
export class MyService {
  constructor(private app: App, private vault: Vault) {}

  async start(): Promise<void> {
    // Initialize service
  }

  async stop(): Promise<void> {
    // Cleanup
  }
}
```

---

## Phase 2: Wire to Plugin Lifecycle ⚠️ (Most Commonly Missed)

**File**: `src/main.ts`

### 2a. Import the Service
```typescript
// At top of file with other imports
import { MyService } from './services/MyService';
```
- [ ] Import statement added

### 2b. Create Plugin Property
```typescript
export default class MyPlugin extends Plugin {
  // Add as class property
  private myService: MyService | null = null;

  // ... rest of class
}
```
- [ ] Property declared in plugin class

### 2c. Instantiate in onload()
```typescript
async onload(): Promise<void> {
  // After settings load, before anything else
  this.myService = new MyService(this.app, this.app.vault);

  // CRITICAL: Call start/initialize method!
  await this.myService.start();
}
```
- [ ] Service instantiated in `onload()`
- [ ] `start()`/`initialize()` method called

### 2d. Cleanup in onunload()
```typescript
async onunload(): Promise<void> {
  if (this.myService) {
    await this.myService.stop();
  }
}
```
- [ ] Cleanup called in `onunload()`

---

## Phase 3: Connect Event Listeners (If Service Emits Events)

### 3a. Service Emits Events
In `MyService`:
```typescript
private onChangeCallbacks: Array<(data: DataType) => void> = [];

public onChange(callback: (data: DataType) => void): void {
  this.onChangeCallbacks.push(callback);
}

private emitChange(data: DataType): void {
  this.onChangeCallbacks.forEach(cb => cb(data));
}
```
- [ ] Service has event emission mechanism

### 3b. UI Component Registers Listener
In UI component or plugin:
```typescript
// During initialization
if (this.myService) {
  this.myService.onChange((data) => {
    // Handle event
    console.log('Service emitted:', data);
  });
}
```
- [ ] Listener registered during initialization
- [ ] Callback executes when service emits

### 3c. Verify No Orphaned Events
```bash
# In browser console while plugin running:
# If service emits but nothing happens, listeners aren't wired
```
- [ ] Events have listeners (verify with console.log)
- [ ] No orphaned callbacks (service events don't disappear)

---

## Phase 4: Test Real Functionality

### 4a. Manual Test (Smoke Test)
- [ ] **Trigger service**: Manual action that should activate service
  - Example: Create a file if service watches for changes
  - Example: Click button if service responds to UI
- [ ] **Verify start**: Check console for "Service started" or similar
- [ ] **Verify event**: Check if service emits expected events
- [ ] **Verify result**: Check if UI/data updated correctly

**Example Commands**:
```bash
# In Obsidian console:
# Check if service is running
window.__plugin?.myService?.isRunning()  // Should return true

# Force trigger event
window.__plugin?.myService?.emitChange({ test: true })

# Check event listeners
window.__plugin?.myService?.callbacks?.length  // Should be > 0
```

### 4b. Integration Test
- [ ] **Full workflow**: End-to-end test with real vault data
- [ ] **Error recovery**: Service handles missing/invalid data
- [ ] **Memory**: Service doesn't leak memory (doesn't grow unbounded)
- [ ] **Performance**: Service operations complete < 500ms

### 4c. Real Data Test (Not Synthetic)
- [ ] Load **actual vault files** (not mocked)
- [ ] Query **actual database** (not mocked)
- [ ] Use **real Obsidian API** (not mocked)
- [ ] Verify **actual output** matches expectations

---

## Debugging Checklist (If Service Doesn't Work)

| Symptom | Check |
|---------|-------|
| Service never starts | 1. Is `onload()` called? 2. Is `start()` called? 3. Any errors in console? |
| Service starts but nothing happens | 1. Are events emitted? 2. Are listeners registered? 3. Does callback execute? |
| Service crashes on vault change | 1. Is vault API used correctly? 2. Error handling in place? 3. Async/await correct? |
| UI doesn't update | 1. Is event listener registered? 2. Is callback executed? 3. Is UI component listening? |
| Memory leak | 1. Is `stop()` cleaning up callbacks? 2. Are timers cleared? 3. Are listeners removed? |

---

## Common Mistakes (Prevent These!)

❌ **Mistake 1: Service created but never started**
```typescript
// WRONG - Service sits unused
this.myService = new MyService(this.app, this.app.vault);
// Missing: await this.myService.start();
```

❌ **Mistake 2: No cleanup on unload**
```typescript
// WRONG - File watchers continue after plugin unload
async onunload(): Promise<void> {
  // Missing: this.myService?.stop()
}
```

❌ **Mistake 3: Events registered but not triggered**
```typescript
// WRONG - Listener registered but service never emits
this.myService.onChange(() => { /* this never runs */ });
// In service: // Missing: this.emitChange(data);
```

❌ **Mistake 4: Only synthetic tests, no real verification**
```typescript
// WRONG - Tests pass but feature doesn't work
test('should extract links', () => {
  const result = service.extract(['[[test]]']);
  expect(result.length).toBeGreaterThan(0); // Passes
});
// But real test: Load actual vault file → Link extraction fails
```

---

## Verification Signoff

Before marking service "complete":

- [ ] **Code review**: All checklist items verified
- [ ] **Manual test**: Service works with real vault
- [ ] **Integration test**: Full workflow tested
- [ ] **Error test**: Service handles failures gracefully
- [ ] **Commit message**: Includes service initialization details

---

## Related

- [[2026-02-17-phase-2-service-initialization-gap-discovery]] (Post-mortem from Phase 2)
- [[verification-strategy-template]] (Real vs synthetic testing)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[3d-graph-plugin-selection]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
