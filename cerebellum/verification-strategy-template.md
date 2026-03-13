---
title: Verification Strategy Template - Real vs Synthetic Testing
date: 2026-02-17
status: active
tags: [pattern, testing, compound-engineering, verification]
aspect: thinker
neural:
  activation: 0.92
  stage: mature
  synapse_in: 2
  synapse_out: 13
---

# Verification Strategy Template: Real vs Synthetic Testing

**Use this template to prevent synthetic testing from creating false confidence.**

---

## Core Problem (Phase 2 Case Study)

| Testing Approach | Code Compiles | Synthetic Test Passes | Real Functionality | Result |
|---|---|---|---|---|
| **Synthetic** | ✓ Yes | ✓ 18/18 pass | ✗ 0% works | False confidence |
| **Real** | ✓ Yes | N/A | ✓ 100% works | Actual verification |

**Lesson**: A synthetic test passing means the test is correct, not the code.

---

## Real Verification Checklist

For every feature, ask these questions:

### 1. **Actual Files & Data**
- [ ] Using real files from the vault (not mocked)
- [ ] Loading actual vault structure (not test stubs)
- [ ] Processing actual content (not fixtures)
- [ ] Storing in actual database (not memory)

### 2. **Actual APIs**
- [ ] Using real Obsidian App instance (not mock)
- [ ] Calling actual SurrealDB queries (not mocked responses)
- [ ] Using real THREE.js renderer (not stubbed)
- [ ] Handling actual API errors (not ignoring them)

### 3. **Actual Workflows**
- [ ] User performs the exact action that triggers feature
- [ ] System processes end-to-end (not just one function)
- [ ] Data flows from input → processing → storage → display
- [ ] User sees the result (verified visually, not assumed)

### 4. **Actual Errors**
- [ ] What happens if vault file is missing? (Error or graceful fallback?)
- [ ] What happens if database is offline? (Error or retry?)
- [ ] What happens if API call fails? (Error or fallback?)
- [ ] What happens with invalid input? (Error or validation?)

---

## Template: Component Verification Checklist

Use this for EVERY component before marking "complete":

### Component: `[ComponentName]`

**Purpose**: [What does it do?]

#### Real Verification Questions

- [ ] **Can I trigger it manually?**
  - Describe exact user action: _______________
  - Does it work? Yes / No / Partial

- [ ] **Does it use real data?**
  - Source: Vault file? Database? API? _______________
  - Is it actually loaded? Yes / No
  - What happens if source is offline? _______________

- [ ] **Does it integrate with other systems?**
  - Depends on: _______________
  - Other systems also verified? Yes / No
  - Do they communicate correctly? Yes / No / Untested

- [ ] **Does it fail gracefully?**
  - Error scenario 1: _______________
  - System response: _______________
  - Error scenario 2: _______________
  - System response: _______________

- [ ] **Can I see the result?**
  - Expected user-facing outcome: _______________
  - Is outcome visible? Yes / No / Not testable yet
  - Does it look correct? Yes / No / Didn't test

#### Real Verification Evidence

Document actual test results (not assumptions):

```
TEST: Paper extraction from decision
  Input: Actual file: decisions/2026-02-17-test.md
  Expected: Extract 3 paper references
  Actual: Extracted 3 papers [list them]
  Status: ✓ PASS

TEST: Service initialization
  Action: Plugin loads
  Expected: DynamicPaperIngestor.start() called
  Actual: [checked console.log, saw "Service started"]
  Status: ✓ PASS

TEST: Error handling - missing file
  Action: Try to process deleted file
  Expected: Graceful error + user notice
  Actual: [describe what happened]
  Status: ✓ PASS / ✗ FAIL
```

---

## Phase 2 Application

### What Was Wrong (Synthetic Testing)

```typescript
// SYNTHETIC TEST - Gave false confidence
test('should extract paper links', () => {
  const result = service.extractReferences(['[[test]]']);
  expect(result.length).toBeGreaterThan(0);  // ✓ PASSES
});

// But in reality:
// 1. Service was never initialized (test never called)
// 2. Vault files were never loaded (test mocked them)
// 3. Integration never happened (test didn't verify wiring)
// Result: 18/18 tests pass, 0% actual functionality
```

### What's Right (Real Verification)

```
MANUAL TEST: Paper extraction from real decision
  File: 2026-02-17-phase-2-decision.md (actual vault file)
  Action: Load decision, extract paper links
  Expected: Find all `[[paper-id]]` patterns
  Actual: Found 5 papers, all correct
  Status: ✓ VERIFIED

INTEGRATION TEST: Service startup
  Action: Plugin loads
  Check: Is DynamicPaperIngestor created?
  Check: Is startWatching() called?
  Check: Are file watchers active?
  Actual: ✓ All working, console shows "Watcher started"
  Status: ✓ VERIFIED

ERROR TEST: Missing decision file
  Action: Delete a decision file
  Expected: Service handles gracefully
  Actual: Event fires, service updates state, no crash
  Status: ✓ VERIFIED
```

---

## Decision Tree: Real vs Synthetic?

```
Am I testing:

├─ A single function?
│  ├─ Does it depend on external data? → REAL test (load actual file)
│  ├─ Does it depend on external API? → REAL test (call actual API)
│  └─ Pure logic only? → Synthetic OK (mock inputs)
│
├─ A service/component?
│  ├─ Integration with other services? → REAL test
│  ├─ Lifecycle (start/stop)? → REAL test
│  └─ Event emission/listening? → REAL test
│
├─ A user workflow?
│  └─ ALWAYS REAL - Simulate exact user actions
│
└─ An error scenario?
   └─ REAL - Test with actual error conditions
```

---

## Converting Synthetic to Real

### Synthetic Test (Before)
```typescript
test('should load decisions', () => {
  const decisions = [{ id: '1', title: 'Test' }]; // Mocked
  const result = service.filter(decisions);
  expect(result.length).toBe(1);
});
```

### Real Test (After)
```typescript
test('should load decisions from vault', async () => {
  // Use ACTUAL vault, not mock
  const vault = app.vault;

  // Load ACTUAL decision files
  const decisions = await vaultBridge.loadAllDecisions();

  // Process with REAL data
  const result = service.filter(decisions);

  // Verify ACTUAL result
  expect(result.length).toBeGreaterThan(0);
  expect(result[0].title).toBeDefined();
});
```

---

## Verification Completion Checklist

Before marking component "complete":

- [ ] **Real data**: Used actual vault files/DB, not mocks
- [ ] **Real APIs**: Called actual Obsidian/SurrealDB APIs, not stubs
- [ ] **Real integration**: Verified wiring between components
- [ ] **Real errors**: Tested error scenarios with actual failures
- [ ] **Real result**: Verified user sees the expected outcome
- [ ] **Evidence**: Documented actual test results (not assumed)

---

## Prevention in Phase 3+

**Code Review Policy**:
- [ ] Reviewer asks: "Is this synthetic or real test?"
- [ ] If synthetic: "Does it test real integration points?"
- [ ] If real: "Does it use actual vault/DB/API?"
- [ ] If neither: "What user workflow is verified?"

**Requirement**: Every feature must have at least one real verification before merge.

---

## Related

- [[service-initialization-checklist]] (Integration wiring)
- [[typescript-error-diagnostic]] (Compilation verification)
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
