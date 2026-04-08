# Genesis Engine Design System

## Overview

The Genesis Engine is a physics-grounded visualization platform for monitoring and controlling agentic training environments. It visualizes 12-dimensional Riemannian manifolds, quantum spinor states, and distributed training across multiple GPUs.

**Design Philosophy**: Dark matter aesthetic with neon data accents - like watching the universe compute.

---

## Design Tokens

### Colors

```yaml
core:
  void: "#020208"         # Deepest background
  matter: "#0a0a12"     # Panels
  fabric: "#1a1a2e"     # Cards
  
accents:
  coherence: "#00d4aa"    # HIHO equilibrium
  energy: "#ff6b35"       # Thermodynamic heat
  quantum: "#9d4edd"      # Spinor states
  fabric_space: "#3a86ff" # Space fabric
  fabric_field: "#f72585" # Field fabric
  
states:
  healthy: "#00d4aa"
  warning: "#ffb703"
  error: "#e63946"
  info: "#3a86ff"
```

### Typography

```yaml
font_family:
  mono: "JetBrains Mono, Fira Code, monospace"
  sans: "Inter, system-ui, sans-serif"
  
hierarchy:
  h1: { size: "2xl", weight: 700, tracking: "tight" }
  h2: { size: "xl", weight: 600, tracking: "tight" }
  h3: { size: "lg", weight: 500 }
  metric: { size: "2xl", weight: 700, mono: true }
  label: { size: "xs", weight: 400, mono: true, uppercase: true }
```

### Spacing

```yaml
grid:
  base: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  
border_radius:
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
```

---

## Component Library

### GenesisCard

```markdown
Container for data visualization.

Props:
- title: string         # Card header
- accent: color_token   # Border/top accent color  
- glow: boolean         # Subtle inner glow
- padding: "sm" | "md" | "lg"

Structure:
┌─────────────────────────────┐
│ Title                  ▸    │  ← Header with expand action
├─────────────────────────────┤
│                             │
│    [Visualization Area]     │  ← Main content
│                             │
├─────────────────────────────┤
│ metric: value  unit  trend  │  ← Footer metrics
└─────────────────────────────┘
```

### MetricGrid

```markdown
Grid of real-time metrics.

Layout:
  mobile:  1 column
  tablet:  2 columns  
  desktop: 4 columns

Each cell:
┌──────────────┐
│ LABEL        │  ← Uppercase, gray-500
│ 2,847        │  ← Large number, mono
│ units        │  ← Small, gray-400
└──────────────┘
```

### CoherenceIndicator

```markdown
HIHO coherence visualization.

Visual:
  [====|====] 0.517
  
  - Dial shows distance from 0.5 (HIHO equilibrium)
  - Green when |δ| < 0.1 (stable)
  - Yellow when |δ| < 0.3 (approaching)
  - Red when |δ| > 0.3 (unstable)
```

### GPUGrid

```markdown
Multi-GPU utilization display.

Layout: 2x2 for 4 GPUs, 4x4 for 16

Each GPU:
  ┌──────────┐
  │ GPU 0    │  ← ID
  │ ████░░░░ │  ← Bar, 0-100%
  │ 67% 74°C │  ← Util, temp
  └──────────┘
  
Colors:
  - <70%: green
  - 70-90%: yellow
  - >90%: red
```

---

## Pages

### /genesis

**Purpose**: Main cosmology visualization - the "birth of universe" view

**Layout**:
```
┌─────────────────────────────────────────────┐
│  Header: Genesis Engine          [Audio]    │
│       From Nothing to Everything [Narrate]  │
├─────────────────────────────────────────────┤
│  Tab: Genesis | Thermo | Compound | ...   │
├─────────────────────────────────────────────┤
│                                             │
│     [3D Cosmological Visualization]         │
│                                             │
│     Void → Big Bang → Fabric Formation      │
│                                             │
├─────────────────────────────────────────────┤
│  Side Panel:                                │
│  - Cosmogony Timeline (step indicator)     │
│  - Physics State (live numbers)            │
│  - Free Energy Landscape (mini graph)      │
└─────────────────────────────────────────────┘
```

**Interactions**:
- Click stage in timeline → Jump to cosmological epoch
- Hover over fabric → Show field strength
- Audio on → Sonification of physics state

### /genesis/training

**Purpose**: Real-time distributed training monitor

**Layout**:
```
┌─────────────────────────────────────────────┐
│  Training Dashboard               [LIVE]    │
├──────────┬──────────────────────────────────┤
│          │                              │
│  METRICS │      CHARTS                  │
│  ─────── │      ═══════                  │
│  Steps   │      Loss      Reward      │
│  2.4M    │      [chart]   [chart]     │
│          │                              │
│  Coherence│                            │
│  0.497   │      Throughput             │
│          │      [gauge]                │
│  GPUs    │                              │
│  [grid]  │                              │
│          │                              │
├──────────┴──────────────────────────────┤
│  Tabs: Overview | Distributed | Causal  │
└─────────────────────────────────────────┘
```

**Data Flow**:
- WebSocket connection to training backend
- Update frequency: 10Hz (metrics), 1Hz (charts)
- Historical buffer: Last 1000 steps

---

## Animations

### Transition Timing

```yaml
standard:
  duration: 200ms
  easing: "cubic-bezier(0.4, 0, 0.2, 1)"  # ease-out
  
physics:
  duration: 500ms
  easing: "cubic-bezier(0.34, 1.56, 0.64, 1)"  # spring
  
slow_reveal:
  duration: 1200ms
  easing: "cubic-bezier(0.0, 0, 0.2, 1)"  # ease-out-slow
```

### Micro-interactions

- **Card hover**: Border brightens, subtle Y translate (-2px)
- **Tab switch**: Content fades in (150ms), no slide
- **Metric update**: Number counter animation
- **Status change**: Color pulse (400ms)

---

## Responsive Breakpoints

```yaml
mobile: 640px
  - Single column
  - Stacked visualizations
  - Simplified metrics

tablet: 768px  
  - Two column grid

laptop: 1024px
  - Full layout

monitor: 1400px+
  - Expanded metrics
  - Multi-panel view
```

---

## Accessibility

- All interactive elements: min 44x44px touch target
- Color contrast: WCAG 2.1 AA minimum
- Reduced motion: Respect prefers-reduced-motion
- Screen reader: Semantic HTML, ARIA labels

---

## Stitch Generation Instructions

When generating screens from this DESIGN.md:

1. **Dark theme only** - Never generate light variants
2. **Neon accents** - Use accent colors for data highlights only
3. **Monospace for data** - All numbers/metrics in mono font
4. **Subtle glows** - Inner box-shadows, not outer
5. **Glass morphism** - Semi-transparent overlays on void background

**Example Prompts**:
- "Generate a training dashboard card showing GPU utilization"
- "Create the Genesis cosmology page 3D scene"
- "Build the distributed training world topology grid"
