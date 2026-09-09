r"""High-Fidelity SVG Vector Diagram Generator for the Cohezion Story.
====================================================================
Generates vector infographics and dark-theme SVG illustrations of the
10-step New Science invariant chain and HIHO Reality Precipitation.
"""

from __future__ import annotations

from pathlib import Path


def generate_10_step_story_svg(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <linearGradient id="neonCyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#06B6D4" />
      <stop offset="100%" stop-color="#3B82F6" />
    </linearGradient>
    <linearGradient id="neonGold" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#EF4444" />
    </linearGradient>
    <linearGradient id="neonGreen" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1000" height="650" fill="url(#bgGrad)" rx="16" />

  <!-- Header -->
  <text x="500" y="55" text-anchor="middle" fill="#38BDF8" font-family="system-ui, sans-serif" font-size="24" font-weight="bold" letter-spacing="2">
    THE NEW SCIENCE: THE 10-STEP INVARIANT ONTOLOGY
  </text>
  <text x="500" y="85" text-anchor="middle" fill="#94A3B8" font-family="system-ui, sans-serif" font-size="14">
    From Pure Nothingness to Reality Precipitation (HIHO Stability = 0.5)
  </text>

  <!-- Central Toroidal Wave Guide -->
  <path d="M 100 325 C 250 150, 400 500, 500 325 C 600 150, 750 500, 900 325" fill="none" stroke="url(#neonCyan)" stroke-width="4" filter="url(#glow)" opacity="0.6"/>

  <!-- 10 Invariant Nodes -->
  <!-- 1. Nothingness -->
  <g transform="translate(100, 325)">
    <circle r="26" fill="#1E293B" stroke="#64748B" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#F8FAFC" font-family="sans-serif" font-size="11" font-weight="bold">1. Void</text>
  </g>

  <!-- 2. Quadrature -->
  <g transform="translate(188, 220)">
    <circle r="26" fill="#1E293B" stroke="#38BDF8" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#38BDF8" font-family="sans-serif" font-size="11" font-weight="bold">2. Quad</text>
  </g>

  <!-- 3. 12 Parameters -->
  <g transform="translate(277, 200)">
    <circle r="26" fill="#1E293B" stroke="#818CF8" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#818CF8" font-family="sans-serif" font-size="11" font-weight="bold">3. 12-P</text>
  </g>

  <!-- 4. 4 Fabrics -->
  <g transform="translate(366, 260)">
    <circle r="26" fill="#1E293B" stroke="#A855F7" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#A855F7" font-family="sans-serif" font-size="11" font-weight="bold">4. Fabric</text>
  </g>

  <!-- 5. Sqrt(-1) Phase -->
  <g transform="translate(455, 390)">
    <circle r="26" fill="#1E293B" stroke="#EC4899" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#EC4899" font-family="sans-serif" font-size="11" font-weight="bold">5. √-1</text>
  </g>

  <!-- 6. Symmetry Breaking -->
  <g transform="translate(544, 430)">
    <circle r="26" fill="#1E293B" stroke="#F43F5E" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#F43F5E" font-family="sans-serif" font-size="11" font-weight="bold">6. SymBrk</text>
  </g>

  <!-- 7. Spin / Torsion -->
  <g transform="translate(633, 380)">
    <circle r="26" fill="#1E293B" stroke="#FB923C" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#FB923C" font-family="sans-serif" font-size="11" font-weight="bold">7. Spin</text>
  </g>

  <!-- 8. HIHO Coherence (0.5) -->
  <g transform="translate(722, 260)">
    <circle r="32" fill="#3B0764" stroke="#F59E0B" stroke-width="3" filter="url(#glow)"/>
    <text y="5" text-anchor="middle" fill="#FDE047" font-family="sans-serif" font-size="12" font-weight="bold">8. HIHO 0.5</text>
  </g>

  <!-- 9. Cohezion Attractor -->
  <g transform="translate(811, 230)">
    <circle r="28" fill="#064E3B" stroke="#34D399" stroke-width="2" />
    <text y="5" text-anchor="middle" fill="#6EE7B7" font-family="sans-serif" font-size="11" font-weight="bold">9. Cohezion</text>
  </g>

  <!-- 10. Reality Precipitates -->
  <g transform="translate(900, 325)">
    <circle r="30" fill="#022C22" stroke="#10B981" stroke-width="3" filter="url(#glow)"/>
    <text y="5" text-anchor="middle" fill="#A7F3D0" font-family="sans-serif" font-size="11" font-weight="bold">10. Reality</text>
  </g>

  <!-- Bottom Legend -->
  <rect x="150" y="540" width="700" height="70" fill="#1E293B" rx="10" stroke="#334155" stroke-width="1" />
  <text x="500" y="568" text-anchor="middle" fill="#38BDF8" font-family="sans-serif" font-size="13" font-weight="bold">
    HIHO Stability Rule: Coherence overlap at exactly 50% (c = 0.5) enables lossless manifestation.
  </text>
  <text x="500" y="592" text-anchor="middle" fill="#94A3B8" font-family="sans-serif" font-size="11">
    4 Fabrics: Space Fabric • Field Fabric • Control Fabric • Precipitation Fabric
  </text>
</svg>
"""
    out_path.write_text(svg, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    out_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/10_step_ontology.svg")
    generate_10_step_story_svg(out_path)
    print(f"SVG Diagram rendered to: {out_path} ({out_path.stat().st_size} bytes)")
