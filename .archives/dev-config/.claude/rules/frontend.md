---
paths:
  - "src/web/**"
  - "apps/**"
---

# Frontend Development Rules (Anima Dashboard)

## Stack
- **Framework:** Next.js 16 (App Router, Turbopack)
- **3D:** React Three Fiber (R3F) + drei + postprocessing
- **Styling:** Tailwind v4, CSS custom properties for HIHO theming
- **State:** React Context (UniverseProvider) fed by SSE

## Critical Patterns

### Three.js/R3F in Next.js
**Always use `dynamic(() => import(...), { ssr: false })` for R3F components.**
Never use `useState(mounted)` inside the component — it still causes hydration mismatches.
```tsx
// CORRECT
const TensorBeam = dynamic(() => import("@/components/TensorBeamVisualizer"), { ssr: false });

// WRONG — causes 190+ console errors
export default function TensorBeam() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return <Canvas>...</Canvas>;
}
```

### React Hooks Ordering
**Never place early returns before hook calls.** Compute values conditionally, call hooks unconditionally, then return conditionally.
```tsx
// WRONG — changes hook count between renders
if (!data) return <Loading />;
useEffect(() => { ... }, [data]);  // skipped when data is null!

// CORRECT — hooks always called in same order
const value = data ? computeFrom(data) : "";
useEffect(() => { if (value) { ... } }, [value]);
if (!data) return <Loading />;
```

### SSE Single Context
**One SSE connection shared via React Context.** Never create per-component polling hooks.
- `UniverseProvider` holds the single EventSource connection
- All components use `useUniverse()` hook
- Reconnection with exponential backoff is centralized

### Division Guards
**Always check `array.length > 0` before computing density/average.**
```tsx
// WRONG — NaN when array is empty
const density = grid.reduce((s, v) => s + v, 0) / grid.length;

// CORRECT
const density = grid.length > 0 ? grid.reduce((s, v) => s + v, 0) / grid.length : 0;
```

### Unmount Hidden Panels
**Use conditional rendering for expensive hidden components, not CSS translate.**
```tsx
// CORRECT — unmounts component, stops hooks
{chatOpen && <AnimaChatPanel />}

// WRONG — still in DOM, hooks still fire
<div className={open ? "translate-x-0" : "translate-x-full"}>
  <AnimaChatPanel />  {/* useAnima() fires even when hidden */}
</div>
```

### HIHO CSS Bridge
Coherence value drives CSS custom properties on `document.documentElement`:
- `--hiho-hue`: 0 (red) to 200 (blue)
- `--hiho-glow-color`: hex color for the current zone
- `--hiho-pulse-speed`: 2s (critical) to 12s (stable)
- `--hiho-particle-density`: 0.3 to 1.0

All components inherit mood through CSS inheritance — no prop drilling needed.

## Playwright Testing
- Three.js Canvas causes `RangeError: Maximum call stack size exceeded` on `browser_snapshot`
- Use `browser_evaluate` with focused queries instead of full snapshots
- Extract large results via file + python3 parsing
- Production build has zero console errors; dev-mode shows R3F SVG attribute warnings
