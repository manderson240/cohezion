---
name: playwright-webgl-testing
description: |
  Testing Next.js/React Three Fiber (R3F) apps with Playwright MCP tools.
  Use when: (1) `browser_snapshot` throws "RangeError: Maximum call stack
  size exceeded", (2) testing pages that contain a Three.js <Canvas> element,
  (3) verifying 3D dashboard UI state without crashing the accessibility tree.
  The crash is NOT a recursion bug in your code — it is Playwright's
  accessibility serializer overflowing on Three.js's deep object graph.
author: Claude Code (session 2026-03-08)
version: 1.0.0
---

# Playwright + WebGL / React Three Fiber Testing

## Problem

`mcp__plugin_playwright_playwright__browser_snapshot` crashes with:

```
RangeError: Maximum call stack size exceeded
```

on any page that contains a Three.js `<Canvas>` element (R3F, raw Three.js,
Babylon.js, etc.). The error is misleading — it is **not** a recursion bug in
your code. Playwright's accessibility tree serializer recursively walks the DOM
and overflows the call stack on Three.js's deeply nested instanced-mesh / buffer
geometry object graph (thousands of nodes).

## Context / Trigger Conditions

- Anima Dashboard at `localhost:3000` uses React Three Fiber (`TensorBeamVisualizer`)
- `browser_snapshot` → immediate crash with stack overflow
- `browser_take_screenshot` still works (renders pixels, no tree traversal)
- Production build: zero console errors. Dev build: R3F SVG attribute warnings (normal)

## Solution

### Option A — `browser_evaluate` (preferred for data extraction)

Run targeted JavaScript in the browser process instead of requesting a full DOM snapshot:

```js
// Check connection status
mcp__plugin_playwright_playwright__browser_evaluate({
  expression: "document.querySelector('[data-testid=\"connection-status\"]')?.textContent"
})

// Read a specific value from a React Context (if exposed to window)
mcp__plugin_playwright_playwright__browser_evaluate({
  expression: "window.__UNIVERSE_STATE__?.coherence"
})

// Check for visible text without traversing Three.js subtree
mcp__plugin_playwright_playwright__browser_evaluate({
  expression: `[...document.querySelectorAll('.font-mono')].map(el => el.textContent).filter(Boolean).slice(0, 10)`
})

// Verify HUD overlay text (the overlay is outside the Canvas)
mcp__plugin_playwright_playwright__browser_evaluate({
  expression: `document.querySelector('footer')?.textContent?.trim()`
})
```

### Option B — `browser_take_screenshot` (preferred for visual verification)

Screenshots render the full page including the 3D canvas without any tree traversal:

```js
mcp__plugin_playwright_playwright__browser_take_screenshot({})
```

Save to file and parse with Python if you need to extract text:

```bash
# Take screenshot, save to /tmp, then OCR with tesseract if needed
```

### Option C — Restrict snapshot to a non-Canvas container

Playwright's `browser_snapshot` optionally accepts an element ref. Navigate to
it first by using `browser_evaluate` to get a non-Canvas ref, then snapshot only
that element. (Effectiveness varies — avoid if Canvas is in the same subtree.)

## Workflow for Anima Dashboard E2E Tests

```python
# 1. Navigate
browser_navigate(url="http://localhost:3000")

# 2. Wait for SSE connection (avoid Canvas snapshot)
browser_evaluate(expression="""
  await new Promise(resolve => {
    const check = () => {
      const dot = document.querySelector('[data-sse-connected]');
      if (dot) resolve(true);
      else setTimeout(check, 200);
    };
    check();
  })
""")

# 3. Verify UI state with targeted selectors (not snapshot)
browser_evaluate(expression="""({
  narration: document.querySelector('footer.fixed')?.textContent?.trim(),
  mode: document.querySelector('[data-mode]')?.dataset?.mode,
  connected: !!document.querySelector('[data-sse-connected]')
})""")

# 4. Screenshot for visual confirmation
browser_take_screenshot({})

# 5. Interact (click, fill) — these work fine, no snapshot needed
browser_click(element="FETCH SYNTHESIS REPORT button")

# 6. Verify result via evaluate, not snapshot
browser_evaluate(expression="document.querySelector('.hiho-status')?.textContent")
```

## Verification

Test passes when:
- No `RangeError` in browser console
- `browser_evaluate` returns expected DOM values
- `browser_take_screenshot` shows correct visual state

## Key Insight

The Three.js Canvas is an *opaque pixel buffer* from the DOM's perspective.
All interactive UI (nav, buttons, narration bar, HUD overlays) exists in
**regular HTML elements outside the Canvas**. Test those — the canvas can only
be verified visually via screenshot.

## References

- React Three Fiber: https://docs.pmnd.rs/react-three-fiber
- Frontend rules (this project): `.claude/rules/frontend.md`
- TensorBeamVisualizer: `src/web/anima_dashboard/src/components/TensorBeamVisualizer.tsx`
