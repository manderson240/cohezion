# Genesis Design Skill

**Agent Skill**: Design Genesis Engine interfaces using Stitch  
**Category**: UI/UX Design  
**Scope**: React/Next.js + Three.js visualization  
**Compatibility**: Claude Code, Cursor, Gemini CLI  

---

## Mission

When working with Genesis Engine UI components, follow the Stitch design system in `.stitch/DESIGN.md`. Generate dark-matter aesthetic interfaces with physics-grounded data visualization.

This skill ensures consistency across all Genesis Engine UI components.

---

## Activation Patterns

**Primary**:
- "Design the Genesis training dashboard"
- "Create a visualization for cosmology data"
- "Build the GPU monitoring grid"
- "Generate the Bloch sphere component"

**Secondary**:
- "Make it look better" (when context is Genesis)
- "Add a new panel to genesis/page.tsx"

---

## Workflow

### Phase 1: Read Design System
1. Load `.stitch/DESIGN.md`
2. Extract relevant tokens (colors, spacing, components)
3. Check for existing components in `src/components/genesis/`

### Phase 2: Design Component
1. Choose appropriate base component (GenesisCard, MetricGrid, etc.)
2. Apply color tokens from DESIGN.md
3. Ensure mono font for data, sans for labels
4. Add accessibility attributes

### Phase 3: Generate Code
1. TypeScript with strict types
2. Tailwind CSS classes only (no inline styles)
3. Responsive breakpoints
4. Animation specifications from DESIGN.md

### Phase 4: Validate
1. Run `scripts/validate-design.ts`
2. Check contrast ratios
3. Verify component exports
4. Test responsive behavior

---

## Component Patterns

### Pattern 1: Data Card

```typescript
// For real-time metrics

interface MetricCardProps {
  title: string;        // "Coherence"
  value: number;        // 0.517
  target?: number;      // 0.500
  unit?: string;        // "HIHO"
  trend?: "up" | "down" | "stable";
  accent: "coherence" | "energy" | "quantum";
}

// Visual:
// ╭──────────────────╮
// │ COHERENCE    ▲   │  // Label + trend indicator
// │                  │
// │ 0.517            │  // Large mono number
// │ target: 0.500    │  // Small gray target
// │ [    |====]      │  // Progress to target
// ╰──────────────────╯
// Border-top: accent color (3px)
```

### Pattern 2: 3D Visualization Container

```typescript
// For Three.js scenes

interface SceneContainerProps {
  title: string;
  height: number;       // px
  children: ReactNode;  // Three.js canvas
  controls?: boolean;   // Show camera controls
}

// Visual:
// ╭──────────────────╮
// │ Title       [?]  │  // Help tooltip
// ├──────────────────┤
// │                  │
// │   [3D Scene]     │  // Full bleed
// │                  │
// ├──────────────────┤
// │ fps: 60  ░░░░    │  // Footer stats
// ╰──────────────────╯
```

### Pattern 3: Metric Grid

```typescript
// For GPU clusters, distributed status

interface MetricGridProps {
  items: Array<{
    id: string;
    value: number;
    max: number;
    label: string;
    status: "healthy" | "warning" | "error";
  }>;
  columns: number;  // 2, 4, or responsive
}

// Visual:
// ╭──────────┬──────────┬──────────┬──────────╮
// │ GPU 0    │ GPU 1    │ GPU 2    │ GPU 3    │
// │ ████░░░░ │ ██████░░ │ ███░░░░░ │ ███████░ │  // Bars
// │ 67% 74°C │ 85% 76°C │ 45% 68°C │ 92% 78°C │  // Values
// ╰──────────┴──────────┴──────────┴──────────╯
```

---

## Color Combinations

### Safe Pairs (WCAG AA)

```
Text on Background:
- #00d4aa (coherence) on #020208 → ✓
- #ff6b35 (energy) on #020208 → ✓
- #9d4edd (quantum) on #020208 → ✓
- #ffffff on #1a1a2e → ✓ (headlines)
- #a0a0b0 on #0a0a12 → ✓ (body)
- #6b7280 on #020208 → ✓ (captions)

NOT Safe:
- #ffb703 on #020208 → ✗ (too low contrast)
- #3a86ff on #020208 → ⚠️ (marginal, use larger size)
```

---

## Typography Scale

```typescript
// Tailwind classes to use:

// Labels, captions
text-xs font-mono uppercase text-gray-500

// Metrics, key numbers
text-xl font-mono font-bold text-white

// Headlines
text-lg font-sans font-semibold text-white

// Descriptions
text-sm font-sans text-gray-400

// Warning/error states
text-sm font-mono text-red-400
```

---

## Common Mistakes to Avoid

### ❌ Don't
- Use light mode for anything
- Mix multiple accent colors in one component
- Use serif fonts
- Add drop shadows (use inner glows instead)
- Show raw JSON data

### ✅ Do
- Layer backgrounds (void < matter < fabric)
- Use monospace for any numeric data
- Include loading states for async data
- Add error boundaries for Three.js scenes
- Use `will-change` for animated elements

---

## Examples in Repository

### Good Example
```typescript
// From BlochSphere.tsx
<div className="bg-[#020208] rounded-lg border border-gray-800 p-4">
  <div className="flex justify-between items-center mb-2">
    <span className="text-xs font-mono uppercase text-gray-500">
      Bloch Sphere
    </span>
    <span className="text-xs font-mono text-cyan-400">
      {coherence.toFixed(3)}
    </span>
  </div>
  {/* Canvas here */}
</div>
```

### Bad Example
```typescript
// ❌ Don't do this
<div style={{ backgroundColor: "white" }}>  // Light mode!
  <span style={{ fontFamily: "Times" }}>  // Serif!
    Coherence: {coherence}
  </span>
</div>
```

---

## Integration with Existing Components

When modifying existing Genesis components:

1. **Stitch compatibility check**:
   ```bash
   npx stitch check src/components/genesis/BlochSphere.tsx
   ```

2. **Design system validation**:
   ```bash
   python skills/genesis-design/scripts/validate_colors.py
   ```

3. **Accessibility audit**:
   ```bash
   npx axe-core src/app/genesis/page.tsx
   ```

---

## Stitch Generation Command

To generate screens using this skill:

```bash
# Using Stitch CLI
npx stitch generate \
  --design ./.stitch/DESIGN.md \
  --skill ./skills/genesis-design \
  --output ./src/components/genesis/ \
  --prompt "Create a distributed training status grid"
```

---

## Resources

- [DESIGN.md](../.stitch/DESIGN.md) - Full design tokens
- [examples/](examples/) - Reference implementations
- [Tailwind Config](/tailwind.config.ts) - Custom theme

---

**License**: Apache-2.0  
**Stitch Version**: v0.1  
**Last Updated**: 2026-04-08
