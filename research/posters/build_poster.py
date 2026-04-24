"""Cohezion 12D Universe + Compound Loop — 24x36 portrait poster.

Renders both PDF and PNG. Visual philosophy: "Instrument Cosmography" —
a scientific schematic in the language of an imagined discipline.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

# ----- palette --------------------------------------------------------------
NAVY = "#0a0e1a"
NAVY2 = "#0f1424"
INK = "#f1f5f9"
INK_DIM = "#cbd5e1"
GRAY = "#475569"
GRAY_DIM = "#1e293b"
CYAN = "#22d3ee"
CYAN_DIM = "#0891b2"
MAGENTA = "#e879f9"
MAGENTA_DIM = "#a21caf"
AMBER = "#fbbf24"
GREEN = "#34d399"
WARN = "#fb7185"

# ----- fonts ---------------------------------------------------------------
SKILL_FONTS = Path(
    "/home/mike-anderson/.claude/plugins/cache/anthropic-agent-skills/claude-api/b0cbd3df1533/skills/canvas-design/canvas-fonts"
)


def fp(name: str, size: float) -> FontProperties:
    p = SKILL_FONTS / name
    if p.exists():
        return FontProperties(fname=str(p), size=size)
    return FontProperties(size=size)


F_TITLE = lambda s: fp("BigShoulders-Bold.ttf", s)
F_DISPLAY = lambda s: fp("BigShoulders-Regular.ttf", s)
F_SANS = lambda s: fp("Outfit-Regular.ttf", s)
F_SANS_B = lambda s: fp("Outfit-Bold.ttf", s)
F_MONO = lambda s: fp("IBMPlexMono-Regular.ttf", s)
F_MONO_B = lambda s: fp("IBMPlexMono-Bold.ttf", s)
F_HAND = lambda s: fp("NothingYouCouldDo-Regular.ttf", s)
F_SERIF_I = lambda s: fp("IBMPlexSerif-Italic.ttf", s)

# ----- canvas --------------------------------------------------------------
W_IN, H_IN = 24.0, 36.0
DPI_PNG = 120

fig = plt.figure(figsize=(W_IN, H_IN), facecolor=NAVY)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 24)
ax.set_ylim(0, 36)
ax.set_axis_off()
ax.set_facecolor(NAVY)


def text(x, y, s, *, font, color=INK, ha="left", va="baseline", rotation=0, alpha=1.0):
    return ax.text(
        x,
        y,
        s,
        fontproperties=font,
        color=color,
        ha=ha,
        va=va,
        rotation=rotation,
        alpha=alpha,
        zorder=10,
    )


# ============================================================================
# 1. BACKGROUND PLATE — register grid
# ============================================================================


def draw_register_grid():
    """Faint dotted graph reseaux beneath everything."""
    step = 0.25
    for x in [i * step for i in range(int(24 / step) + 1)]:
        ax.plot([x, x], [0, 36], color="#111827", lw=0.25, zorder=0.1)
    for y in [i * step for i in range(int(36 / step) + 1)]:
        ax.plot([0, 24], [y, y], color="#111827", lw=0.25, zorder=0.1)
    # heavier lines on a coarser grid
    for x in range(0, 25, 2):
        ax.plot([x, x], [0, 36], color="#16213a", lw=0.4, zorder=0.15)
    for y in range(0, 37, 2):
        ax.plot([0, 24], [y, y], color="#16213a", lw=0.4, zorder=0.15)
    # corner registration crosses
    for cx, cy in [(1.0, 1.0), (23.0, 1.0), (1.0, 35.0), (23.0, 35.0)]:
        ax.plot([cx - 0.4, cx + 0.4], [cy, cy], color=GRAY, lw=0.6, zorder=0.4)
        ax.plot([cx, cx], [cy - 0.4, cy + 0.4], color=GRAY, lw=0.6, zorder=0.4)
        ax.add_patch(Circle((cx, cy), 0.18, fill=False, ec=GRAY, lw=0.5, zorder=0.4))


def draw_outer_frame():
    """Hairline frame + inner frame — like a printer's plate."""
    for off, lw, c in [(0.55, 0.8, GRAY), (0.65, 0.4, GRAY_DIM)]:
        ax.add_patch(
            Rectangle((off, off), 24 - 2 * off, 36 - 2 * off, fill=False, ec=c, lw=lw, zorder=0.6)
        )
    # tick marks along the frame
    for i in range(0, 25):
        ax.plot([i, i], [0.55, 0.75], color=GRAY, lw=0.4, zorder=0.7)
        ax.plot([i, i], [35.25, 35.45], color=GRAY, lw=0.4, zorder=0.7)
    for j in range(0, 37):
        ax.plot([0.55, 0.75], [j, j], color=GRAY, lw=0.4, zorder=0.7)
        ax.plot([23.25, 23.45], [j, j], color=GRAY, lw=0.4, zorder=0.7)


# ============================================================================
# 2. HEADER — title block
# ============================================================================


def draw_header():
    # plate number at far top
    ax.text(
        1.2,
        35.0,
        r"PLATE  $\Omega$ · XIV",
        color=GRAY,
        fontsize=11,
        va="center",
        family="monospace",
        zorder=10,
    )
    text(
        22.8,
        35.0,
        "ED. 2026  ·  PORTRAIT  ·  24×36",
        font=F_MONO(11),
        color=GRAY,
        ha="right",
        va="center",
    )

    # the rule
    ax.plot([1.2, 22.8], [34.55, 34.55], color=CYAN, lw=0.8, zorder=2)
    ax.add_patch(Circle((1.2, 34.55), 0.07, color=CYAN, zorder=2))
    ax.add_patch(Circle((22.8, 34.55), 0.07, color=CYAN, zorder=2))

    # eyebrow
    text(
        1.2,
        34.05,
        "AN  INSTRUMENT  FOR  THE  STUDY  OF  COMPOUND  AGENTIC  SYSTEMS",
        font=F_MONO(11.5),
        color=INK_DIM,
        va="center",
    )

    # main title — single confident gesture
    text(12.0, 33.0, "COHEZION", font=F_TITLE(150), color=INK, ha="center", va="center")
    # subtitle, monospace
    text(
        12.0,
        31.65,
        "12-DIMENSIONAL  UNIVERSE  ·  COMPOUND  LOOP  ·  ARCHITECTURAL  ATLAS",
        font=F_MONO(13.5),
        color=CYAN,
        ha="center",
        va="center",
    )

    # sub-rule
    ax.plot([8.0, 16.0], [31.18, 31.18], color=GRAY, lw=0.4, zorder=2)


# ============================================================================
# 3. TOP THIRD — the 11-step compound ring
# ============================================================================

STEPS = [
    ("01", "PRIME  SKILL", "ingest"),
    ("02", "INSTRUCTION  EXPANDER", "parse"),
    ("03", "PLAN  EXECUTOR", "tactical"),
    ("04", "REQUEST  ALIGNMENT", "coherence"),
    ("05", "GLOBAL  METRICS", "record"),
    ("06", "DEGRADATION  DETECTOR", "thermal·quality"),
    ("07", "JOURNEY  TRACKER  12D", "position"),
    ("08", "OUROBOROS  ·  MYCELIUM", "physics·corr"),
    ("09", "RETROSPECTION", "extract"),
    ("10", "SKILL  REFINER", "update"),
    ("11", "CONSENSUS  VOTER", "validate"),
]


def draw_compound_ring():
    cx, cy = 12.0, 25.90
    R_OUTER = 4.55
    R_RING = 3.95
    R_INNER = 3.30
    R_CORE = 1.80

    # decorative outer ticks (degree marks like a sextant)
    for i in range(72):
        a = math.radians(i * 5)
        x1 = cx + (R_OUTER + 0.18) * math.cos(a)
        y1 = cy + (R_OUTER + 0.18) * math.sin(a)
        x2 = cx + (R_OUTER + 0.32 if i % 9 == 0 else R_OUTER + 0.25) * math.cos(a)
        y2 = cy + (R_OUTER + 0.32 if i % 9 == 0 else R_OUTER + 0.25) * math.sin(a)
        ax.plot([x1, x2], [y1, y2], color=GRAY, lw=0.4, zorder=2)

    # outer ring (faint)
    ax.add_patch(Circle((cx, cy), R_OUTER, fill=False, ec=GRAY_DIM, lw=0.6, zorder=2))
    ax.add_patch(Circle((cx, cy), R_RING, fill=False, ec=CYAN, lw=1.2, zorder=2))
    ax.add_patch(Circle((cx, cy), R_INNER, fill=False, ec=GRAY_DIM, lw=0.6, zorder=2))

    # core inner ring — 12D state vector
    ax.add_patch(Circle((cx, cy), R_CORE, fill=False, ec=MAGENTA, lw=0.8, zorder=2))
    ax.add_patch(Circle((cx, cy), R_CORE - 0.65, fill=False, ec=MAGENTA_DIM, lw=0.5, zorder=2))

    # 12 spokes inside the core for the 12D vector
    for i in range(12):
        a = math.radians(i * 30 - 90)
        x1 = cx + 0.25 * math.cos(a)
        y1 = cy + 0.25 * math.sin(a)
        x2 = cx + (R_CORE - 0.05) * math.cos(a)
        y2 = cy + (R_CORE - 0.05) * math.sin(a)
        ax.plot([x1, x2], [y1, y2], color=MAGENTA, lw=0.55, alpha=0.85, zorder=3)
        # dimension labels (D1..D12)
        rl = R_CORE - 0.42
        text(
            cx + rl * math.cos(a),
            cy + rl * math.sin(a),
            f"D{i + 1:02}",
            font=F_MONO(7.0),
            color=INK_DIM,
            ha="center",
            va="center",
            alpha=0.85,
        )

    # central glyph — a small spinor mark + label (mathtext for Greek)
    ax.text(
        cx,
        cy + 0.20,
        r"$\mathbf{\Psi}$",
        color=CYAN,
        ha="center",
        va="center",
        fontsize=72,
        zorder=10,
    )
    text(
        cx,
        cy - 0.60,
        "12D  STATE  VECTOR",
        font=F_MONO(8.5),
        color=INK_DIM,
        ha="center",
        va="center",
    )
    text(
        cx,
        cy - 0.98,
        "JourneyTracker.position(t)",
        font=F_MONO(7.5),
        color=GRAY,
        ha="center",
        va="center",
    )

    # 11 nodes — start at 10 o'clock (150°) going clockwise
    n = len(STEPS)
    start_deg = 150.0
    for i, (num, name, sub) in enumerate(STEPS):
        a = math.radians(start_deg - (360.0 / n) * i)
        nx = cx + R_RING * math.cos(a)
        ny = cy + R_RING * math.sin(a)

        # node disc — magenta for the orchestrator hub (06,07,08), cyan otherwise
        is_hub = i in (3, 4, 5, 6, 7)  # the fan-out cluster
        nc = MAGENTA if is_hub else CYAN
        nfill = NAVY2

        # outer node ring
        ax.add_patch(Circle((nx, ny), 0.36, facecolor=nfill, ec=nc, lw=1.4, zorder=5))
        ax.add_patch(Circle((nx, ny), 0.22, facecolor=nc, ec=None, alpha=0.18, zorder=5))
        ax.add_patch(Circle((nx, ny), 0.085, facecolor=nc, ec=None, zorder=6))

        # number inside the node (outside the dot, in the ring band)
        text(
            nx, ny, num, font=F_MONO_B(8.5), color=INK, ha="center", va="center", alpha=0
        )  # placeholder — number on label below

        # label position outside the ring
        rl = R_OUTER + 0.55
        lx = cx + rl * math.cos(a)
        ly = cy + rl * math.sin(a)

        # leader line from node out to label
        x1 = cx + (R_RING + 0.36) * math.cos(a)
        y1 = cy + (R_RING + 0.36) * math.sin(a)
        x2 = cx + (R_OUTER + 0.40) * math.cos(a)
        y2 = cy + (R_OUTER + 0.40) * math.sin(a)
        ax.plot([x1, x2], [y1, y2], color=nc, lw=0.7, zorder=4)

        # text alignment depends on quadrant
        cosA = math.cos(a)
        if cosA > 0.25:
            ha = "left"
            ox = 0.05
        elif cosA < -0.25:
            ha = "right"
            ox = -0.05
        else:
            ha = "center"
            ox = 0.0
        # number plate
        text(lx + ox, ly + 0.18, num, font=F_MONO_B(11), color=nc, ha=ha, va="bottom")
        # name
        text(lx + ox, ly - 0.05, name, font=F_SANS_B(10.5), color=INK, ha=ha, va="top")
        # tag
        text(lx + ox, ly - 0.32, sub, font=F_MONO(8.5), color=GRAY, ha=ha, va="top")

    # arrowheads on the ring to show clockwise direction (subtle, on ring)
    for i in range(n):
        a_mid = math.radians(start_deg - (360.0 / n) * (i + 0.5))
        ax_x = cx + R_RING * math.cos(a_mid)
        ax_y = cy + R_RING * math.sin(a_mid)
        # tangent direction (clockwise => -90 from radius)
        tx = math.sin(a_mid)
        ty = -math.cos(a_mid)
        # tiny triangle
        h = 0.10
        w = 0.06
        p1 = (ax_x + h * tx, ax_y + h * ty)
        p2 = (ax_x - h * 0.3 * tx + w * (-ty), ax_y - h * 0.3 * ty + w * tx)
        p3 = (ax_x - h * 0.3 * tx - w * (-ty), ax_y - h * 0.3 * ty - w * tx)
        ax.add_patch(Polygon([p1, p2, p3], facecolor=CYAN, edgecolor=None, alpha=0.85, zorder=4))

    # inputs annotation: PRIME skill enters at 12 o'clock (tight to ring)
    text(
        cx,
        cy + R_OUTER + 0.50,
        "INPUT  ·  PRIME  SKILL",
        font=F_MONO_B(9.5),
        color=INK,
        ha="center",
        va="bottom",
    )
    # tiny marker dot above the ring (no arrow — would hit subtitle)
    ax.add_patch(Circle((cx, cy + R_OUTER + 0.18), 0.10, facecolor=CYAN, ec=None, zorder=5))
    ax.plot([cx, cx], [cy + R_OUTER + 0.05, cy + R_OUTER + 0.30], color=CYAN, lw=1.4, zorder=5)

    # output annotation — placed inside the ring near the curving return arc
    arc = mpatches.FancyArrowPatch(
        (cx + 0.6, cy - R_OUTER - 0.05),
        (cx - 0.6, cy - R_OUTER - 0.05),
        connectionstyle="arc3,rad=-0.55",
        arrowstyle="-|>",
        color=MAGENTA,
        lw=1.2,
        zorder=5,
    )
    ax.add_patch(arc)
    # whisper-quiet label tucked under the arc
    text(
        cx,
        cy - R_OUTER - 0.62,
        "loop  closes  ·  refined  skill",
        font=F_MONO(8.5),
        color=MAGENTA,
        ha="center",
        va="top",
    )

    # left-corner caption sits in the negative space of the upper-left
    # quadrant, between the title and the ring's 9-o'clock label
    text(1.2, 30.50, "I.", font=F_TITLE(26), color=CYAN, va="top")
    text(1.2, 29.85, "THE  COMPOUND", font=F_DISPLAY(17), color=INK, va="top")
    text(1.2, 29.30, "LOOP", font=F_DISPLAY(17), color=INK, va="top")
    text(1.2, 28.62, "eleven  steps  ·  clockwise", font=F_SERIF_I(10), color=INK_DIM, va="top")
    text(1.2, 28.28, "read  from  ten", font=F_SERIF_I(10), color=INK_DIM, va="top")
    # right-corner caption mirrors it
    text(22.8, 30.50, "fig. 01", font=F_MONO(11), color=GRAY, ha="right", va="top")
    text(22.8, 30.15, "scale  1 : 1", font=F_MONO(9), color=GRAY, ha="right", va="top")
    text(22.8, 29.80, "n  =  11  nodes", font=F_MONO(9), color=GRAY, ha="right", va="top")

    # easter-egg quote in the margin (left side, vertical)
    text(
        0.95,
        25.9,
        "“ every  feature  makes  future  features  easier ”",
        font=F_HAND(13),
        color=GRAY,
        ha="center",
        va="center",
        rotation=90,
    )
    text(
        23.05,
        25.9,
        "HIHO  STABILITY  ≈  0.50",
        font=F_MONO(9.5),
        color=GRAY,
        ha="center",
        va="center",
        rotation=-90,
    )


# ============================================================================
# 4. MIDDLE THIRD — the 18-layer slab cake
# ============================================================================

LAYERS = [
    ("COMPOUND", "Executor · 11-step pipeline", "CompoundExecutor"),
    ("SWARM", "Team + execution orchestration", "TeamExecutor"),
    ("CACHE", "L1 hash · L2 cosine · L3 vault", "SemanticCache"),
    ("COST OPT", "Lemonade-first · 45 models · YAML", "CostAwareRouter"),
    ("PERSISTENCE", "Vault + JSONL · session recovery", "SessionManager"),
    ("PHYSICS", "SU(2) · Riemannian · gauge · Fisher", "SpinorState"),
    ("WORLD MODEL", "JEPA ~2M params · causal masking", "JEPAWorldModel"),
    ("BIOELECTRIC", "Levin gap-junction · HIHO transition", "BioelectricNetwork"),
    ("COSMOGONY", "10-step chain · symmetry breaking", "physics/cosmogony"),
    ("WORLDVIEWS", "16 traditions × 10 stages", "WorldviewExplorer"),
    ("OUROBOROS", "Bridge + mycelium correlation", "OuroborosBridge"),
    ("ENVIRONMENTS", "ManifoldEnv · SwarmEnv · gymnasium", "ManifoldEnv-v0"),
    ("GOVERNANCE", "AutonomyEngine · Concierge · Bridge", "AutonomyEngine"),
    ("DATA MESH", "Typed SLA · MCP registry · tiers", "DataProduct"),
    ("PROVIDERS", "Lemonade · Ollama Cloud · adapters", "LemonadeAdapter"),
    ("UI", "Genesis · 11 components · 8 tabs", "/genesis"),
    ("KNOWLEDGE", "Vault-First · MEMORY.md auto-cache", "vault_find_relevant_context"),
    ("ANTHROPIC INTEL", "11-source monitor · risk-tiered", "/anthropic-scan"),
]


# Color stripes alternate cyan/magenta to break monotony — but quietly.
def slab_color(i: int):
    # group 0–4 cool, 5–11 warm physics cluster, 12–17 cool again
    if 5 <= i <= 11:
        return MAGENTA, MAGENTA_DIM
    return CYAN, CYAN_DIM


def draw_slab():
    # area: x in [1.2, 22.8], y in [11.40, 19.60]
    x0, x1 = 1.2, 22.8
    y_top, y_bot = 19.60, 11.40
    n = len(LAYERS)
    h = (y_top - y_bot) / n  # ≈ 0.456

    # title block — sits in the gap between ring bottom (21.35) and slab top
    text(1.2, 20.50, "II.", font=F_TITLE(28), color=MAGENTA, va="top")
    text(2.0, 20.50, "ARCHITECTURAL  STRATA", font=F_DISPLAY(20), color=INK, va="top")
    text(
        2.0,
        20.04,
        "eighteen  layers  ·  top → bottom  ·  entry-points  right",
        font=F_SERIF_I(11),
        color=INK_DIM,
        va="top",
    )
    text(22.8, 20.50, "fig. 02", font=F_MONO(11), color=GRAY, ha="right", va="top")
    text(22.8, 20.15, "n  =  18  strata", font=F_MONO(9), color=GRAY, ha="right", va="top")

    # outer slab frame
    ax.add_patch(
        Rectangle(
            (x0, y_bot),
            x1 - x0,
            y_top - y_bot,
            fill=True,
            facecolor=NAVY2,
            ec=GRAY,
            lw=0.6,
            zorder=2,
        )
    )

    for i, (name, desc, entry) in enumerate(LAYERS):
        y = y_top - (i + 1) * h
        c, cdim = slab_color(i)

        # band fill — alternating very faint stripes
        band_alpha = 0.06 if i % 2 == 0 else 0.02
        ax.add_patch(
            Rectangle((x0, y), x1 - x0, h, facecolor=c, alpha=band_alpha, ec=None, zorder=3)
        )
        # divider line
        ax.plot([x0, x1], [y + h, y + h], color=GRAY_DIM, lw=0.4, zorder=3)

        # left tag — index ribbon
        tag_w = 1.05
        ax.add_patch(Rectangle((x0, y), tag_w, h, facecolor=c, alpha=0.85, ec=None, zorder=4))
        text(
            x0 + tag_w / 2,
            y + h / 2,
            f"L{i + 1:02}",
            font=F_MONO_B(10),
            color=NAVY,
            ha="center",
            va="center",
        )

        # name (left)
        text(x0 + tag_w + 0.40, y + h / 2 + 0.04, name, font=F_SANS_B(13.5), color=INK, va="center")
        # desc (italic, just under name)
        text(
            x0 + tag_w + 0.40, y + h / 2 - 0.16, desc, font=F_SANS(10.0), color=INK_DIM, va="center"
        )

        # entry point (right) — monospace
        text(
            x1 - 0.3, y + h / 2 + 0.05, entry, font=F_MONO_B(10.5), color=c, ha="right", va="center"
        )
        text(
            x1 - 0.3,
            y + h / 2 - 0.18,
            "entry · class",
            font=F_MONO(7.5),
            color=GRAY,
            ha="right",
            va="center",
        )

        # subtle measurement bar — kept inside a fixed central column so it
        # never collides with name-left or entry-right text
        midx = (x0 + x1) / 2 - 1.4
        v = ((i * 13 + 7) % 17) / 17.0
        bar_w = 0.8 + v * 1.4
        ax.add_patch(
            Rectangle(
                (midx, y + h / 2 - 0.035),
                bar_w,
                0.07,
                facecolor=cdim,
                alpha=0.40,
                ec=None,
                zorder=4,
            )
        )
        # tick at the end
        ax.plot(
            [midx + bar_w, midx + bar_w],
            [y + h / 2 - 0.11, y + h / 2 + 0.11],
            color=cdim,
            lw=0.5,
            alpha=0.7,
            zorder=4,
        )
        # tiny baseline tick at the start
        ax.plot(
            [midx, midx],
            [y + h / 2 - 0.06, y + h / 2 + 0.06],
            color=GRAY,
            lw=0.4,
            alpha=0.6,
            zorder=4,
        )

    # bracket at the physics cluster — drawn on the LEFT margin so it doesn't
    # crash the right edge or the entry-point column
    by_top = y_top - 5 * h
    by_bot = y_top - 12 * h
    bx = x0 - 0.20
    ax.plot([bx, bx], [by_bot, by_top], color=MAGENTA, lw=1.0, zorder=8)
    ax.plot([bx, bx + 0.18], [by_top, by_top], color=MAGENTA, lw=1.0, zorder=8)
    ax.plot([bx, bx + 0.18], [by_bot, by_bot], color=MAGENTA, lw=1.0, zorder=8)
    # vertical annotation outside the bracket
    text(
        bx - 0.18,
        (by_top + by_bot) / 2,
        "PHYSICS  +  WORLD  ·  7 / 18",
        font=F_MONO_B(9),
        color=MAGENTA,
        ha="center",
        va="center",
        rotation=90,
    )


# ============================================================================
# 5. BOTTOM THIRD — the 6-protocol hex lattice + cost bar
# ============================================================================

PROTOCOLS = [
    # name, status, anchor
    ("MCP", "STRONG", "87+ tools", GREEN),
    ("A2A", "IN PROGRESS", "7 specialist agents", AMBER),
    ("UCP", "N/A", "commerce out-of-scope", GRAY),
    ("AP2", "N/A", "payment out-of-scope", GRAY),
    ("A2UI", "STRONG", "8-component catalog", GREEN),
    ("AG-UI", "STRONG", "15+ event types · SSE", GREEN),
]


def hex_polygon(cx, cy, r):
    return [
        (cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def draw_hex_lattice():
    # area: header y in [10.6, 11.3], lattice center rows y ~ 8.5 and 5.5
    text(1.2, 10.95, "III.", font=F_TITLE(34), color=GREEN, va="top")
    text(2.6, 10.95, "AGENT  PROTOCOL  STACK", font=F_DISPLAY(26), color=INK, va="top")
    text(
        2.6,
        10.25,
        "six  protocols  ·  cells  shaded  by  adoption  posture",
        font=F_SERIF_I(13),
        color=INK_DIM,
        va="top",
    )
    text(22.8, 10.95, "fig. 03", font=F_MONO(11), color=GRAY, ha="right", va="top")

    # legend on the right
    leg_x = 15.4
    leg_y = 10.20
    for color, label in [(GREEN, "STRONG"), (AMBER, "IN PROGRESS"), (GRAY, "N / A")]:
        ax.add_patch(
            Polygon(
                hex_polygon(leg_x, leg_y, 0.18),
                facecolor=color,
                alpha=0.85,
                ec=color,
                lw=0.8,
                zorder=5,
            )
        )
        text(leg_x + 0.30, leg_y - 0.04, label, font=F_MONO_B(8.5), color=INK_DIM, va="center")
        leg_x += 2.30

    # lattice geometry — 2 rows × 3 cols, hex-pointy-top
    # use radius r, horizontal spacing 2*r*cos(30) ≈ 1.732r, vertical 1.5r
    r = 1.85
    dx = math.sqrt(3) * r
    dy = 1.5 * r
    cy_top = 8.55
    cy_bot = cy_top - dy
    cx0 = 12.0 - dx  # left col
    centers = [
        (cx0, cy_top),
        (cx0 + dx, cy_top),
        (cx0 + 2 * dx, cy_top),
        (cx0 + 0.5 * dx, cy_bot),
        (cx0 + 1.5 * dx, cy_bot),
        (cx0 + 2.5 * dx, cy_bot),
    ]
    # Reorder centers to follow the protocol order in a pleasing hex layout:
    # top row: MCP, A2A, UCP ; bottom row: AP2, A2UI, AG-UI
    for i, (px, py) in enumerate(centers):
        name, status, anchor, sc = PROTOCOLS[i]
        # outer faint hex (the lattice)
        ax.add_patch(
            Polygon(hex_polygon(px, py, r + 0.18), fill=False, ec=GRAY_DIM, lw=0.5, zorder=3)
        )
        # cell fill
        cell_alpha = 0.18 if status != "N/A" else 0.05
        ax.add_patch(
            Polygon(hex_polygon(px, py, r), facecolor=sc, alpha=cell_alpha, ec=sc, lw=1.4, zorder=4)
        )
        # inner micro-hex for ornamentation
        ax.add_patch(
            Polygon(hex_polygon(px, py, 0.55), fill=False, ec=sc, lw=0.5, alpha=0.45, zorder=4)
        )
        # name (large)
        text(
            px,
            py + 0.45,
            name,
            font=F_TITLE(38),
            color=INK if status != "N/A" else GRAY,
            ha="center",
            va="center",
        )
        # status pill
        text(px, py - 0.30, status, font=F_MONO_B(9.5), color=sc, ha="center", va="center")
        # anchor description
        text(px, py - 0.65, anchor, font=F_MONO(8.5), color=INK_DIM, ha="center", va="center")
        # protocol label (Roman number i+1 in tiny mono in the corner)
        text(
            px - r * 0.78,
            py + r * 0.62,
            f"P-0{i + 1}",
            font=F_MONO(7.5),
            color=GRAY,
            ha="left",
            va="center",
        )

    # Connection lines between adjacent shipped (green) cells — to show
    # the live integration mesh between MCP, A2UI, AG-UI
    green_idx = [i for i, p in enumerate(PROTOCOLS) if p[1] == "STRONG"]
    pts = [(centers[i][0], centers[i][1]) for i in green_idx]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (x1g, y1g), (x2g, y2g) = pts[i], pts[j]
            ax.plot(
                [x1g, x2g],
                [y1g, y2g],
                color=GREEN,
                lw=0.6,
                alpha=0.45,
                zorder=3.5,
                linestyle=(0, (3, 2)),
            )


def draw_cost_bar():
    # below the hex lattice — the 70/20/10 cost-routing tiers
    y = 3.20
    h = 0.78
    x0, x1 = 1.2, 22.8
    text(1.2, y + h + 0.55, "IV.", font=F_TITLE(28), color=AMBER, va="top")
    text(
        2.2, y + h + 0.55, "COST  ROUTING  ·  70 / 20 / 10", font=F_DISPLAY(22), color=INK, va="top"
    )
    text(
        2.2,
        y + h + 0.0,
        "blended  fleet  ·  cheap-first  ·  budget-enforced",
        font=F_SERIF_I(12),
        color=INK_DIM,
        va="top",
    )
    text(22.8, y + h + 0.55, "fig. 04", font=F_MONO(11), color=GRAY, ha="right", va="top")

    seg = [
        (0.70, GREEN, "SIMPLE  ·  70%", "Ollama  ·  Flash-Lite", "free  ·  local"),
        (0.20, AMBER, "MEDIUM  ·  20%", "Claude  Sonnet", "$3 / M  tokens"),
        (0.10, MAGENTA, "HARD  ·  10%", "Claude  Opus", "$15 / M  tokens"),
    ]
    cur = x0
    width = x1 - x0
    for frac, color, top, mid, bot in seg:
        w = width * frac
        ax.add_patch(
            Rectangle((cur, y), w, h, facecolor=color, alpha=0.20, ec=color, lw=1.2, zorder=4)
        )
        # internal vertical hatch (subtle)
        for j in range(int(w / 0.18)):
            ax.plot(
                [cur + j * 0.18, cur + j * 0.18],
                [y + 0.06, y + h - 0.06],
                color=color,
                lw=0.18,
                alpha=0.18,
                zorder=4,
            )
        # text inside
        text(cur + w / 2, y + h - 0.20, top, font=F_MONO_B(11), color=color, ha="center", va="top")
        text(cur + w / 2, y + h - 0.45, mid, font=F_SANS_B(11.5), color=INK, ha="center", va="top")
        text(cur + w / 2, y + 0.10, bot, font=F_MONO(9.0), color=INK_DIM, ha="center", va="bottom")
        cur += w

    # ticks above the bar
    ax.plot([x0, x1], [y + h + 0.10, y + h + 0.10], color=GRAY, lw=0.4)
    for f in [0, 0.5, 0.7, 0.9, 1.0]:
        tx = x0 + width * f
        ax.plot([tx, tx], [y + h + 0.10, y + h + 0.20], color=GRAY, lw=0.4)
        text(
            tx,
            y + h + 0.30,
            f"{int(f * 100)}%",
            font=F_MONO(8),
            color=GRAY,
            ha="center",
            va="bottom",
        )


# ============================================================================
# 6. FOOTER — provenance stamp + signature
# ============================================================================


def draw_footer():
    # Footer rule
    ax.plot([1.2, 22.8], [2.55, 2.55], color=CYAN, lw=0.8, zorder=2)
    ax.add_patch(Circle((1.2, 2.55), 0.07, color=CYAN, zorder=2))
    ax.add_patch(Circle((22.8, 2.55), 0.07, color=CYAN, zorder=2))

    # Left — manifesto micro-text (CLAUDE.md aphorisms as easter egg ribbon)
    # short, punchy aphorism — leaves room for the stamp on the right
    text(
        1.2,
        2.30,
        "EXECUTE  FIRST  ·  PLAN  SECOND  ·  INFRASTRUCTURE  NEVER",
        font=F_MONO_B(10.0),
        color=INK_DIM,
        va="top",
    )
    text(
        1.2,
        1.95,
        "implement  one  feature  ·  validate  manually  ·  write  five  tests",
        font=F_SERIF_I(10.5),
        color=GRAY,
        va="top",
    )
    text(
        1.2,
        1.62,
        "—  CHARTER  ·  CLAUDE.md  §  execution  priority",
        font=F_MONO(8.0),
        color=GRAY,
        va="top",
    )

    # MADE-IN stamp — bottom right
    stamp_x, stamp_y = 22.8, 2.18
    sw, sh = 7.4, 1.42
    ax.add_patch(
        FancyBboxPatch(
            (stamp_x - sw, stamp_y - sh + 0.15),
            sw,
            sh,
            boxstyle="round,pad=0.05,rounding_size=0.10",
            fill=True,
            facecolor=NAVY,
            ec=MAGENTA,
            lw=0.8,
            zorder=6,
        )
    )
    text(
        stamp_x - sw + 0.30, stamp_y - 0.10, "MADE  IN", font=F_MONO_B(10), color=MAGENTA, va="top"
    )
    ax.text(
        stamp_x - sw + 0.30,
        stamp_y - 0.45,
        r"synthetic-sniffing-panda  ·  campaign  $\Omega$14",
        color=INK,
        fontsize=9,
        family="monospace",
        va="top",
        zorder=10,
    )
    text(
        stamp_x - sw + 0.30,
        stamp_y - 0.75,
        "2026 · 04 · 23   ·   74  COMMITS   ·   SOLO",
        font=F_MONO(8.5),
        color=INK_DIM,
        va="top",
    )
    text(
        stamp_x - sw + 0.30,
        stamp_y - 1.02,
        "set  by  hand  ·  @  manderson240",
        font=F_HAND(11),
        color=GRAY,
        va="top",
    )

    # tiny "edition of one" mark below the stamp
    text(
        stamp_x,
        stamp_y - 1.45,
        "ED.  1 / 1   ·   AP  ·   AOP",
        font=F_MONO(7.5),
        color=GRAY,
        ha="right",
        va="top",
    )

    # Bottom-most rule and chronograph mark
    ax.plot([1.2, 22.8], [0.92, 0.92], color=GRAY, lw=0.4, zorder=2)
    text(
        12.0,
        0.70,
        "PRINTED  ON  THE  AMD  RYZEN  AI  MAX+  395  ·  LPDDR5X  128 GiB  ·  STRIX  HALO",
        font=F_MONO(7.5),
        color=GRAY,
        ha="center",
        va="top",
    )


# ============================================================================
# RENDER
# ============================================================================

draw_register_grid()
draw_outer_frame()
draw_header()
draw_compound_ring()
draw_slab()
draw_hex_lattice()
draw_cost_bar()
draw_footer()

OUT_DIR = Path(
    "/home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda/research/posters"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF = OUT_DIR / "2026-04-23-cohezion-architecture-poster.pdf"
PNG = OUT_DIR / "2026-04-23-cohezion-architecture-poster.png"

fig.savefig(PDF, format="pdf", facecolor=NAVY, bbox_inches=None, pad_inches=0)
# Render PNG, then re-save through PIL with PNG optimization to keep under 1MB
fig.savefig(PNG, format="png", dpi=DPI_PNG, facecolor=NAVY, bbox_inches=None, pad_inches=0)
try:
    from PIL import Image

    img = Image.open(PNG).convert("RGB")  # drop alpha to reduce size
    img.save(PNG, format="PNG", optimize=True, compress_level=9)
except Exception as exc:  # pragma: no cover
    print(f"  (PIL post-process skipped: {exc})")
print(f"WROTE  {PDF}")
print(f"WROTE  {PNG}")
