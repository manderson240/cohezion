# UX Design: FLUME VAE Research Showcase

## Document Metadata

- **Project**: FLUME VAE Research Showcase
- **Type**: UX Design Specification (Reverse-Engineered from Implementation)
- **Source**: Production webapp at `src/web/anima_dashboard/`
- **Status**: ✅ IMPLEMENTED (Documenting existing UX patterns)
- **Created**: 2026-03-23
- **Last Updated**: 2026-03-23

## Executive Summary

This document captures the **existing UX design patterns** implemented in Cohezion's FLUME VAE Research Showcase webapp. Unlike forward-looking UX specs, this is a **brownfield documentation artifact** reverse-engineered from production code to inform architectural decisions.

**Key Insight**: The webapp is ALREADY BUILT with sophisticated UX patterns including WebGL 3D visualization, responsive design, error boundaries, and cohesive branding. This document serves as the UX reference for Architecture and Implementation phases.

---

## Brand Identity

### Visual Brand System

**Source**: [`src/cohezion/branding.py`](../../../src/cohezion/branding.py)

#### Core Colors

| Color Name | Hex Value | Usage | Semantic Meaning |
|------------|-----------|-------|------------------|
| **Nexus Green** | `#00FF00` | Primary brand, success states | The Lattice / Life |
| **Neon Cyan** | `#00f2fe` | Interactive elements, highlights | Accents / Attention |
| **Plasma Blue** | `#4facfe` | Header borders, secondary accents | Cool tones |
| **Neon Purple** | `#f093fb` | Gradients, mystery elements | Discovery |
| **Matte Black** | `#0A0A0A` | Backgrounds, cards | The Void / Hardware |
| **Silicon Silver** | `#C0C0C0` | Text, borders | The Chassis |
| **Earth Blue** | `#0077BE` | Data visualization | The Singularity |
| **Critical Red** | `#FF3B3B` | Errors, warnings | Instability |
| **Warning Gold** | `#F6D365` | Pending states | Transient State |

#### Brand Tokens (CSS Variables)

**Source**: [`src/web/anima_dashboard/public/brand-tokens.css`](../../../src/web/anima_dashboard/public/brand-tokens.css)

```css
:root {
  --color-nexus-green: #00FF00;
  --color-neon-cyan: #00f2fe;
  --color-plasma-blue: #4facfe;
  --color-neon-purple: #f093fb;
  --color-matte-black: #0A0A0A;
  --color-silicon-silver: #C0C0C0;
  --color-earth-blue: #0077BE;
  --color-critical-red: #FF3B3B;
  --color-warning-gold: #F6D365;
}
```

### Brand Philosophy

- **Name**: COHEZION
- **Tagline**: "The Nexus of Coherence"
- **Design Philosophy**: **"Organic Modularity"**
- **Visual Style**: Cybernetic minimalism, sci-fi technical aesthetic
- **Typography**: Monospace fonts (technical authenticity)

### Logo Assets

- **Primary Logo**: [`src/web/anima_dashboard/public/cohezion-logo.png`](../../../src/web/anima_dashboard/public/cohezion-logo.png) (780 KB)
- **ASCII Logo**: Defined in `branding.py` for CLI/terminal contexts
- **Format**: PNG with transparency

---

## Information Architecture

### Site Structure

```
Portfolio Landing (/)
├── Hero Section
│   ├── Title: "Self-Improving AI Infrastructure"
│   ├── Stats Grid (4,658 tests, 55+ cycles, etc.)
│   └── CTA Buttons (Live Demo, View Portfolio)
├── Problem/Solution Section
│   └── Compound Engineering Thesis
├── Five Portfolio Pillars
│   ├── FLUME VAE (LIVE) ←─── PRIMARY FOCUS
│   ├── Compound Loop (BUILDING)
│   ├── Universe Simulation (LIVE)
│   ├── Multi-Agent Swarm (BUILDING)
│   └── Evaluation Infrastructure (PLANNED)
├── Technical Highlights Grid
└── Footer (Contact, Social Links)

FLUME Detail Page (/portfolio/flume)
├── Navigation
│   ├── Back to Portfolio
│   ├── Tab Switcher (Demo | Explanation)
│   └── Blog Post Link
├── Title Section
│   └── "PILLAR #1 — CONTINUOUS LATENT NAVIGATION"
├── Demo Tab
│   ├── FlumeNavigator (3D WebGL Visualization)
│   ├── Quick Stats (256D, ~32D, ∞)
│   └── How to Use Guide
└── Explanation Tab
    ├── What is FLUME?
    ├── Technical Architecture
    └── Anthropic Universes Relevance
```

### Navigation Patterns

1. **Primary Navigation**: Sticky header with logo, portfolio link, GitHub icon
2. **Secondary Navigation**: Tab switcher (Demo/Explanation) on FLUME page
3. **Breadcrumb**: "Back to Portfolio" button (visible arrow + label)
4. **External Links**: GitHub, LinkedIn, Email in footer

---

## User Flows

### Flow 1: Hiring Manager (5-Minute Scan)

**Persona**: Alex (Anthropic Universes Team Lead)
**Goal**: Quickly assess technical credibility
**Source**: PRD User Journey for Alex

**Steps**:
1. Land on `/portfolio` → See hero "Self-Improving AI Infrastructure"
2. Scan stats grid → **4,658 tests**, 55+ cycles, 2 live APIs
3. Read "FLUME VAE" pillar card → Status: **LIVE**
4. Click "DEMO" button → `/portfolio/flume`
5. **See 3D WebGL visualization loading** (instant visual proof)
6. Observe coherence-colored point cloud rotating
7. Adjust slider (50-500 samples) → See real-time API response
8. **Decision**: "This person ships working code" → Move to technical review

**Success Criteria**: <5 minutes from landing to decision

### Flow 2: Technical Evaluator (40-Minute Deep Assessment)

**Persona**: Sarah (Senior Research Engineer)
**Goal**: Validate technical depth and research rigor
**Source**: PRD User Journey for Sarah

**Steps**:
1. Start at `/portfolio/flume` from Alex's referral
2. **Demo Tab** (10 min):
   - Interact with 3D visualization (drag, zoom, pan)
   - Test edge cases (max samples, rapid resampling)
   - Inspect browser DevTools for API calls
   - Verify WebGL context loss recovery
3. **Explanation Tab** (15 min):
   - Read "What is FLUME?" → Understand VAE approach
   - Study "Technical Architecture" (encoder, latent space, decoder)
   - Assess "Anthropic Universes Relevance" section
4. **Blog Post** (10 min):
   - Click "BLOG POST" button → Read technical deep-dive
   - Verify claims (MSE 0.023, KL divergence, 5.5M trajectories)
5. **Codebase** (5 min):
   - Click GitHub link → Browse `src/cohezion/flume/`
   - Check test coverage → Confirm 4,658 tests claim
6. **Decision**: "Novel approach, production-ready implementation" → Recommend interview

**Success Criteria**: 100% claims verifiable, <40 min total time

### Flow 3: Error Recovery

**Trigger**: WebGL not available, API timeout, context loss
**Goal**: Graceful degradation without breaking user experience

**Implemented Patterns**:
1. **WebGL Context Loss** ([FlumeNavigator.tsx:84-125](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx#L84-L125)):
   - Detect `webglcontextlost` event
   - Display: "WEBGL CONTEXT LOST" with "RELOAD PAGE" button
   - Prevent white screen of death
2. **API Error** ([FlumeNavigator.tsx:246-261](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx#L246-L261)):
   - Show error message with "RETRY" button
   - Preserve user's sample count setting
3. **React Error Boundary** ([FlumeNavigator.tsx:154-174](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx#L154-L174)):
   - Catch component crashes
   - Display "VISUALIZATION ERROR" with "TRY AGAIN" button
   - Provide context: "This may be due to WebGL not being available"

---

## Component Library

### 1. FlumeNavigator (Interactive 3D Visualization)

**Source**: [`src/web/anima_dashboard/src/components/FlumeNavigator.tsx`](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx)

**Purpose**: Primary interactive demo component for FLUME VAE latent space

**Key Features**:
- **3D Point Cloud Rendering**: React Three Fiber + Three.js
- **Color-Coded Coherence**: Blue (low) → Green (medium) → Yellow/Red (high)
- **Real-Time API Integration**: POST `/flume/latent-space` with n_samples, seed
- **Interactive Controls**:
  - Range slider (50-500 samples)
  - Resample button (fetches new data)
  - 3D navigation (drag, zoom, pan)
- **Defensive Programming**:
  - Request cancellation (AbortController)
  - WebGL context loss recovery
  - Error boundaries
  - Loading states

**Visual Specifications**:

```typescript
// Container
className="w-full h-[600px] bg-black/90 rounded-xl border border-cyan-500/20"

// Loading State
text-cyan-400 font-mono text-sm mb-4 animate-pulse
"SAMPLING LATENT SPACE..."

// Error State
text-red-400 font-mono text-sm mb-4
"ERROR"

// Stats Panel
bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-4

// Point Cloud Material
size={highlightedIndex !== null ? 0.03 : 0.05}
vertexColors
transparent
opacity={0.8}
```

**Performance Optimizations**:
- **Issue #11**: Memoized geometry to prevent recreation on every render
- **Issue #14**: Stabilized `fetchLatentSpace` reference to fix infinite loop
- **Issue #19**: Request cancellation for rapid resampling
- **Issue #20**: Clamped rotation speed to prevent motion sickness

### 2. PillarCard (Portfolio Item Card)

**Source**: [`src/web/anima_dashboard/src/app/portfolio/page.tsx:8-82`](../../../src/web/anima_dashboard/src/app/portfolio/page.tsx#L8-L82)

**Purpose**: Display individual portfolio items with status badges

**Props**:
```typescript
interface PillarCardProps {
  title: string;
  description: string;
  icon: string;  // Emoji
  demoPath: string;
  blogPath: string;
  gradient: string;  // TailwindCSS gradient classes
  status: "live" | "building" | "planned";
}
```

**Visual States**:
- **LIVE**: Emerald green badge, "DEMO" + "READ MORE" buttons
- **BUILDING**: Amber badge, "COMING SOON" button
- **PLANNED**: Gray badge, "PLANNED" button

**Interactions**:
- Hover: `scale-[1.02]`, animated border glow
- Gradient border with pulse effect

**Example (FLUME VAE)**:
```typescript
{
  title: "FLUME VAE",
  description: "Continuous latent navigation through 256-dimensional software state space...",
  icon: "🌊",
  demoPath: "/portfolio/flume",
  blogPath: "/portfolio/blog/flume-vae",
  gradient: "from-cyan-500/20 via-blue-500/20 to-purple-500/20",
  status: "live",
}
```

### 3. Stats Grid

**Source**: [`src/web/anima_dashboard/src/app/portfolio/page.tsx:135-232`](../../../src/web/anima_dashboard/src/app/portfolio/page.tsx#L135-L232)

**Purpose**: Display quantified metrics (test count, compound cycles, APIs, type coverage)

**Visual Pattern**:
```typescript
<div className="grid grid-cols-2 md:grid-cols-4 gap-6">
  <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6">
    <div className="text-3xl font-bold font-mono bg-gradient-to-r from-cyan-400 to-purple-400 text-transparent bg-clip-text">
      4,658
    </div>
    <div className="text-xs text-gray-500 font-mono">tests</div>
    <div className="text-[10px] text-gray-600 font-mono">Test Suite</div>
  </div>
</div>
```

**Interaction**: Hover tooltip shows detail ("Comprehensive coverage")

---

## Design System

### Typography

**Primary Font**: System monospace stack
```css
font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
```

**Scale**:
- **Display (Hero)**: `text-6xl md:text-7xl` (72-96px)
- **H1**: `text-5xl` (48px)
- **H2**: `text-4xl` (36px)
- **H3**: `text-2xl` (24px)
- **Body**: `text-base` (16px)
- **Small**: `text-sm` (14px)
- **Tiny**: `text-xs` (12px)
- **Micro**: `text-[10px]` (10px)

**Weight**:
- **Bold**: Headings, stats, labels
- **Normal**: Body text, descriptions

**Letter Spacing**:
- `tracking-widest`: Badges, labels (e.g., "RESEARCH ENGINEER PORTFOLIO")
- `tracking-tight`: Display headings

### Spacing & Layout

**Container Width**: `max-w-7xl` (1280px) for main content, `max-w-4xl` (896px) for text-heavy sections

**Grid Patterns**:
- **2 Columns**: Stats grid on mobile
- **4 Columns**: Stats grid on desktop
- **3 Columns**: Portfolio pillars on large screens
- **2 Columns**: Portfolio pillars on medium screens
- **1 Column**: Portfolio pillars on mobile

**Padding**:
- **Page Sections**: `py-24` (96px vertical)
- **Cards**: `p-6` to `p-12` (24-48px)
- **Buttons**: `px-4 py-2` to `px-8 py-4`

**Rounded Corners**:
- **Large Cards**: `rounded-2xl` (16px)
- **Standard Cards**: `rounded-xl` (12px)
- **Buttons**: `rounded-lg` (8px)
- **Badges**: `rounded-full` (pill shape)

### Glass Morphism Effects

**Pattern**: Transparent backgrounds with backdrop blur

```css
bg-white/[0.02]          /* 2% white opacity */
backdrop-blur-xl          /* Blur background */
border border-white/10    /* 10% white border */
```

**Usage**: All cards, panels, overlays

### Color Application

| Element | Color | Rationale |
|---------|-------|-----------|
| **Background** | `#000000` (Pure Black) | Maximum contrast, sci-fi aesthetic |
| **Primary Text** | `text-white` | Readability on black |
| **Secondary Text** | `text-gray-400` | De-emphasized content |
| **Tertiary Text** | `text-gray-600` | Metadata, captions |
| **Primary CTA** | Cyan to Blue gradient | Matches brand (Neon Cyan) |
| **Success** | `text-emerald-400` | Positive states, "LIVE" badge |
| **Warning** | `text-amber-400` | "BUILDING" badge |
| **Error** | `text-red-400` | Error messages |
| **Data Viz** | `text-cyan-400` | Stats, metrics, technical values |

### Animation & Motion

**Principles**:
- **Subtle**: Animations enhance, don't distract
- **Purpose**: Every animation communicates state change
- **Performance**: Use CSS transitions (GPU-accelerated)

**Patterns**:
1. **Pulse**: `animate-pulse` for loading states, background glows
2. **Hover Scale**: `hover:scale-[1.02]` for cards
3. **Translation**: `hover:translate-x-1` for arrow icons
4. **Color Fade**: `transition-colors` for links, buttons
5. **Background Blur**: Animated gradients in fixed background layer

**3D Rotation** (FlumeNavigator):
```typescript
// Slow, constant rotation when not interacting
useFrame((state) => {
  if (highlightedIndex === null) {
    const rotation = state.clock.elapsedTime * 0.1;
    meshRef.current.rotation.y = rotation % (Math.PI * 2);
  }
});
```

### Responsive Breakpoints

**TailwindCSS Defaults**:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

**Responsive Patterns**:
- **Grid**: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (adaptive columns)
- **Text Size**: `text-6xl md:text-7xl` (larger on desktop)
- **Flex Direction**: `flex-col md:flex-row` (stack on mobile)

---

## Accessibility

### Implemented Patterns

1. **Semantic HTML**: `<nav>`, `<section>`, `<footer>`, `<h1>`-`<h3>`
2. **ARIA Labels**:
   - `aria-label="Number of samples"` on range input
   - `aria-label="Resample latent space"` on button
3. **Keyboard Navigation**: All interactive elements focusable via Tab
4. **Alt Text**: Logo images have descriptive alt attributes
5. **Color Contrast**:
   - White text on black: 21:1 (AAA)
   - Cyan (#00f2fe) on black: 13.5:1 (AAA)
   - Gray 400 on black: 7.8:1 (AA)
6. **Error Messages**: Clear, actionable text ("WebGL not available", "RETRY" button)

### Areas for Improvement (Not Implemented)

- **Screen Reader Announcements**: 3D visualization changes not announced
- **Focus Indicators**: Custom focus rings for brand consistency
- **Reduced Motion**: Respect `prefers-reduced-motion` media query
- **ARIA Live Regions**: For dynamic content updates (stats, errors)

---

## Interaction Design

### Buttons

**Primary CTA**:
```typescript
className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-mono font-bold hover:scale-105 transition-transform"
```
- **Purpose**: Main actions (Explore Live Demo)
- **Visual**: Gradient background, white text, scale on hover

**Secondary CTA**:
```typescript
className="px-8 py-4 bg-white/10 border border-white/20 rounded-xl text-white font-mono font-bold hover:bg-white/20 transition-all"
```
- **Purpose**: Alternative actions (View Portfolio)
- **Visual**: Glass morphism, border, fade on hover

**Destructive/Retry**:
```typescript
className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-red-400 text-xs font-mono transition-all"
```
- **Purpose**: Error recovery (RETRY button)
- **Visual**: Red theme, small size

### Form Controls

**Range Slider**:
```typescript
<input
  type="range"
  min="50"
  max="500"
  step="50"
  value={nSamples}
  onChange={(e) => setNSamples(parseInt(e.target.value))}
  className="flex-1"
  aria-label="Number of samples"
/>
```
- **Purpose**: Adjust visualization sample count
- **Min/Max**: 50-500 samples (performance vs. density trade-off)
- **Step**: 50 (coarse granularity for performance)

### 3D Navigation

**Controls**: OrbitControls from `@react-three/drei`
```typescript
<OrbitControls
  enableDamping
  dampingFactor={0.05}
  autoRotateSpeed={2}
/>
```
- **Drag**: Rotate camera
- **Scroll**: Zoom in/out
- **Right-Click + Drag**: Pan camera
- **Damping**: Smooth deceleration (natural feel)

**Instructions Overlay**:
```typescript
<div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-sm border border-white/10 rounded-lg p-3 text-[10px] font-mono text-gray-400">
  <div>🖱️ Drag to rotate • Scroll to zoom • Right-click to pan</div>
</div>
```

---

## Page Specifications

### Portfolio Landing (`/portfolio`)

**Purpose**: High-level overview of research portfolio for hiring evaluators

**Sections**:
1. **Hero** (Viewport Height):
   - Title: "Self-Improving AI Infrastructure" (gradient)
   - Subtitle: "12D universe simulation, multi-agent swarm, learns from every execution"
   - CTA Buttons: "EXPLORE LIVE DEMO", "VIEW PORTFOLIO"
   - Stats Grid: 4 metrics (tests, cycles, APIs, type coverage)
2. **Compound Engineering Thesis**:
   - Problem: "AI systems don't compound"
   - Solution: "Execute → reflect → refine → repeat"
   - Proof: "579 modules, 4,426 tests, 99.9% pass rate"
3. **Five Portfolio Pillars**:
   - Grid of PillarCard components
   - FLUME VAE: **LIVE** (primary focus)
   - 4 others: BUILDING or PLANNED
4. **Technical Highlights**:
   - 6-item grid (Novel Architecture, Production-Ready, etc.)
5. **Footer**:
   - Contact links (Email, LinkedIn, GitHub)
   - Version info: "COHEZION v1.0.2"

**Key UX Decisions**:
- **Stats First**: Quantified credibility before reading
- **Status Badges**: Honest signaling ("COMING SOON" instead of vaporware)
- **Gradient Borders**: Visual hierarchy (each pillar has unique gradient)

### FLUME Detail Page (`/portfolio/flume`)

**Purpose**: Interactive demo + technical explanation for FLUME VAE

**Sections**:
1. **Navigation**:
   - Back to Portfolio link
   - Tab switcher: Demo | Explanation
   - Blog Post link (external navigation)
2. **Title**:
   - Badge: "PILLAR #1 — CONTINUOUS LATENT NAVIGATION"
   - Heading: "FLUME VAE."
   - Description: "Navigate 256-dimensional software state space..."
3. **Demo Tab** (Default):
   - FlumeNavigator component (3D viz)
   - Quick Stats: 256D input, ~32D latent, ∞ continuous
   - How to Use guide (4 steps)
4. **Explanation Tab**:
   - What is FLUME? (VAE, continuous latent space)
   - Technical Architecture (Encoder, Latent Space, Decoder)
   - Why This Matters (gradient-based navigation, semantic similarity)
   - Anthropic Universes Relevance (scalable simulation environments)

**Key UX Decisions**:
- **Demo First**: Show, don't tell (visual proof immediately visible)
- **Tab Pattern**: Separate interaction from explanation (reduce cognitive load)
- **Anthropic Section**: Directly connects to job requirements
- **Blog Link**: Persistent in header (always accessible)

---

## Technical Implementation Notes

### Tech Stack

- **Framework**: Next.js 16 (App Router)
- **UI Library**: React 19
- **3D Rendering**: React Three Fiber + Three.js
- **Styling**: TailwindCSS 4.0
- **Icons**: Lucide React
- **Language**: TypeScript (strict mode)

### Server-Side Rendering Strategy

**FlumeNavigator**: Dynamically imported with `ssr: false`
```typescript
const FlumeNavigator = dynamic(() => import("@/components/FlumeNavigator"), {
  ssr: false,  // Prevent SSR (WebGL only runs in browser)
  loading: () => (
    <div className="...">
      <span>INITIALIZING FLUME NAVIGATOR...</span>
    </div>
  ),
});
```

**Rationale**: Three.js requires browser APIs (WebGL, Canvas), not available in Node.js SSR

### API Integration

**Endpoint**: `POST /flume/latent-space`

**Request**:
```json
{
  "n_samples": 200,
  "seed": null  // null = random, integer = deterministic
}
```

**Response**:
```typescript
interface LatentSpaceData {
  latent_dim: number;           // 256
  samples: number[][];          // 256D samples
  samples_3d: number[][];       // PCA-projected 3D samples
  variance_explained: number[]; // PCA variance per component
  coherence_scores: number[];   // Coherence per sample
}
```

**Error Handling**:
- HTTP 4xx/5xx: Display error message with "RETRY" button
- Network timeout: AbortController cancels request
- JSON parse error: Fallback to generic error message

### Performance Considerations

1. **Geometry Memoization** (Issue #11):
   - `useMemo` prevents recreation on every render
   - Disposes geometry on unmount (prevent memory leak)
2. **Request Cancellation** (Issue #19):
   - `AbortController` cancels previous request when new one starts
   - Prevents race conditions (slow request finishes after fast request)
3. **Frame Rate Clamping** (Issue #20):
   - Rotation speed: `state.clock.elapsedTime * 0.1` (slow, smooth)
   - Prevents motion sickness from rapid rotation
4. **Vertex Colors**:
   - Colors computed once at geometry creation (not per frame)
   - GPU-accelerated rendering (Three.js buffer attributes)

### Browser Compatibility

**Minimum Requirements**:
- **WebGL 1.0**: Required for 3D visualization
- **ES2020**: Required for Next.js 16
- **Flexbox/Grid**: Required for layout

**Graceful Degradation**:
- **No WebGL**: Error boundary shows message + link to blog post
- **Context Loss**: Detects event, offers reload button
- **Mobile**: Responsive grid, smaller text, touch-friendly controls

---

## Future Enhancements (Not Implemented)

1. **Click Points to Decode** ([FlumeNavigator.tsx:143-145](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx#L143-L145)):
   - Currently shows "(Coming soon)"
   - Would display full 256D vector when point clicked
2. **Interpolation Path Visualization**:
   - Select two points → draw smooth path in latent space
   - Animate traversal along path
3. **Checkpoint Selector**:
   - Dropdown to switch between `flume_vae_ep2.pt`, `ep5.pt`, `ep50.pt`
   - Compare training progress visually
4. **Export Visualization**:
   - Download current view as PNG/SVG
   - Export 3D model as OBJ/GLTF for external tools
5. **Accessibility Improvements**:
   - Screen reader announcements for state changes
   - Keyboard shortcuts for 3D navigation (arrow keys)
   - High-contrast mode toggle

---

## Design Rationale

### Why This Design?

1. **Technical Authenticity**: Monospace fonts, sci-fi aesthetic signals "built by engineers"
2. **Visual Proof Over Claims**: 3D visualization loads immediately (show, don't tell)
3. **Honest Signaling**: "COMING SOON" badges instead of broken links
4. **Evaluator-First**: Optimized for 5-min scan (stats grid) and 40-min deep dive (explanation tab)
5. **Anthropic Alignment**: Dedicated section connects FLUME to Universes role requirements

### Design Constraints

1. **No Backend for Portfolio**: Static Next.js export (except FLUME API)
2. **WebGL Dependency**: Visualization requires modern browser (acceptable for technical audience)
3. **GitHub Visibility**: Entire implementation visible at [`FlumeNavigator.tsx`](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx) (transparency)

---

## Appendix: File Reference

### Core Files

| File | Lines | Purpose |
|------|-------|---------|
| [`FlumeNavigator.tsx`](../../../src/web/anima_dashboard/src/components/FlumeNavigator.tsx) | 375 | Primary 3D visualization component |
| [`portfolio/page.tsx`](../../../src/web/anima_dashboard/src/app/portfolio/page.tsx) | 372 | Portfolio landing page |
| [`portfolio/flume/page.tsx`](../../../src/web/anima_dashboard/src/app/portfolio/flume/page.tsx) | 251 | FLUME detail page |
| [`branding.py`](../../../src/cohezion/branding.py) | 110 | Brand identity constants |
| [`brand-tokens.css`](../../../src/web/anima_dashboard/public/brand-tokens.css) | 12 | CSS variables for colors |
| [`cohezion-logo.png`](../../../src/web/anima_dashboard/public/cohezion-logo.png) | — | 780 KB logo file |

### Design Artifacts

- **Color Palette**: Defined in `branding.py` (9 core colors)
- **Component Library**: React components in `src/web/anima_dashboard/src/components/`
- **Page Layouts**: Next.js App Router pages in `src/web/anima_dashboard/src/app/`

---

## Document Completion

**Status**: ✅ COMPLETE

This UX design document is **reverse-engineered from production code**, not a forward-looking specification. All patterns, components, and interactions described here are **already implemented and deployed**.

**Next Step**: Use this UX document as input to Architecture workflow to define technical implementation details, integration patterns, and data flows.

**Key Takeaway**: The webapp is production-ready with sophisticated UX patterns. The challenge is not to design new UX, but to **integrate existing UX with real checkpoint data** (replacing synthetic samples in FlumeNavigator).
