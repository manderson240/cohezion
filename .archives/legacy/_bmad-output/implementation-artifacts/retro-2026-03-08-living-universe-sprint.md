# Retrospective: Living Universe API Sprint (2026-03-08)

**Sprint**: Cross-Epic "Compound Identity" Sprint
**Epics Touched**: 1, 2, 3, 4, 5
**Stories Completed**: 13 of 55
**FRs Implemented**: FR1, FR2, FR12-FR18, FR22 (11 of 24)
**Tests**: 56 new, 0 regressions
**Bug Fixes**: 6 runtime fixes

---

## What Went Well

### 1. Cross-Epic Coherence
Implementing stories across 5 epics simultaneously created natural integration points. The SSE universe provider (2-5) became the backbone for OuroborosControlRoom (5-3), TensorBeam (2-2), and AnimaNarrationBar (4-5). This validated the compound engineering principle: shared infrastructure enables faster feature delivery.

### 2. TDD Discipline
All 56 tests were written alongside implementation. The Playwright WebGL testing skill was created specifically for R3F components, solving the "how do you test 3D renders" problem with accessibility-tree-based assertions rather than pixel comparison.

### 3. Bug Discovery Through Integration
6 runtime bugs were discovered and fixed during integration testing:
- NaN CA density (physics engine numerical stability)
- OuroborosControlRoom stuck connecting (SSE reconnection logic)
- AnimaChatPanel DOM leak (cleanup on unmount)
- Empty narration (guard clause for missing HIHO metrics)
- Three.js r197 SSR errors (dynamic imports for WebGL components)
- React hooks ordering (conditional hook calls refactored)

These would NOT have been caught by unit tests alone — they only manifested when real physics data flowed through the frontend pipeline.

### 4. Polyglot Execution
Python backend (FastAPI/Pydantic), TypeScript frontend (Next.js 16/R3F), Rust physics core — each language was used where it excels. The boundary contracts (JSON schemas for API, TypeScript interfaces for components) kept the polyglot stack coherent.

---

## What Could Be Improved

### 1. Dashboard-Physics Gap Was Too Wide
The OuroborosControlRoom and TensorBeam existed with `Math.random()` data for too long before being connected to real physics engines. Earlier integration would have caught the NaN and SSR bugs sooner.

**Action Item**: For remaining stories, implement backend API endpoint FIRST, then wire frontend to real data immediately. No mock-data-first development.

### 2. MCP Store_Node Schema Gap
The `store_node` MCP tool's Python model (`UniverseNode.__init__`) requires an `id` field not exposed in the MCP tool schema. The `PhysicsState` model has undocumented required fields. This prevents runtime use of a declared tool.

**Action Item**: Fix `store_node` MCP schema to match Python model. Add integration test that calls every MCP tool with valid parameters.

### 3. Cross-Epic Sprint Tracking
The sprint-status.yaml doesn't naturally represent cross-epic sprints. Stories were tracked individually but there was no sprint-level grouping showing which stories were being worked together.

**Action Item**: Consider adding a `sprint` field to sprint-status.yaml entries, or maintain a separate sprint log.

### 4. Frontend Coding Standards Late
The `.claude/rules/frontend.md` was created AFTER most frontend stories were done. Earlier standards would have prevented some of the React hooks ordering issues.

**Action Item**: Create coding standards BEFORE the first story in a new tech stack.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Stories completed | 13/55 (24%) |
| FRs implemented | 11/24 (46%) |
| Tests added | 56 |
| Regressions | 0 |
| Runtime bugs found+fixed | 6 |
| TypeScript errors | 0 |
| Epics advanced | 5 (all moved to in-progress) |

---

## Lessons Learned (Persist to Vault)

1. **SSE > Polling for Physics Data**: 10Hz SSE stream with `EventSource` provides smoother coherence tracking than polling. Deduplication via sequence IDs prevents duplicate state processing.

2. **R3F Testing via Accessibility Tree**: Playwright can test Three.js/R3F components without pixel comparison by using `page.accessibility.snapshot()` to verify scene structure and `page.evaluate()` to read Three.js scene properties.

3. **HIHO CSS Bridge Pattern**: Mapping physics values (coherence 0-1) to CSS custom properties (`--hiho-coherence`) enables pure-CSS animations that respond to live physics without React re-renders.

4. **Cross-Epic Integration Creates Compounding Value**: Stories 2-5 (SSE provider) unlocked 5-3 (Ouroboros), 4-5 (narration), and 2-2 (TensorBeam). Shared infrastructure stories should be prioritized in sprint planning.

---

## Next Sprint Recommendations

### Priority Stories (High Integration Value)
1. **3-3 Metacognitive Intent Capture** (FR6) — Enables FR9 (truth anchors) downstream
2. **4-1 Vanguard Source Connector** (FR5) — Unlocks 4-1b, 4-1c, 4-6, 4-7
3. **5-1 Ouroboros Trigger VAE** (NFR8) — Connects to 5-2 (ShadowScripter)

### Technical Debt
- Fix `store_node` MCP schema alignment
- Add integration test for all MCP tools
- Document SSE reconnection protocol for other consumers

---

*Retrospective facilitated by Cohezion Compound Engineering Pipeline*
*Date: 2026-03-08*
