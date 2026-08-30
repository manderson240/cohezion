r"""3D Multimodal Plotly & HTML/SVG Manifold Renderer for Cohezion Story.
========================================================================
Generates interactive, color-graded 3D Toroidal Manifolds, Poincaré Disks,
and Reality Precipitation geometries using Plotly with dark neon theme.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go


def generate_3d_torus_manifold(out_html_path: Path) -> Path:
    """Generate a 3D self-similar fractal toroidal vortex in Plotly."""
    out_html_path.parent.mkdir(parents=True, exist_ok=True)

    # Grid parameters
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, 2 * np.pi, 100)
    U, V = np.meshgrid(u, v)

    # Torus with Golden Ratio (Phi) Major/Minor Radii
    R = 3.0  # Major radius
    r = 1.0  # Minor radius

    # 3D Torus parametric equations with golden spiral modulation
    phi_twist = 1.6180339887 * U
    X = (R + r * np.cos(V)) * np.cos(U + 0.2 * np.sin(phi_twist))
    Y = (R + r * np.cos(V)) * np.sin(U + 0.2 * np.sin(phi_twist))
    Z = r * np.sin(V) + 0.3 * np.cos(phi_twist)

    # Color mapping based on distance from HIHO 0.5 Coherence surface
    coherence_field = 0.5 + 0.5 * np.sin(U) * np.cos(V)

    fig = go.Figure(
        data=[
            go.Surface(
                x=X,
                y=Y,
                z=Z,
                surfacecolor=coherence_field,
                colorscale="Viridis",
                colorbar=dict(title="HIHO Coherence (0.5 = Stable)"),
                opacity=0.92,
                lighting=dict(ambient=0.4, diffuse=0.8, specular=0.9, roughness=0.1),
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="⚡ The New Science: 3D Fractal Toroidal Invariant Manifold ⚡",
            font=dict(size=20, color="#38BDF8"),
        ),
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#0B0F19",
        scene=dict(
            xaxis=dict(showbackground=False, visible=False),
            yaxis=dict(showbackground=False, visible=False),
            zaxis=dict(showbackground=False, visible=False),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
        ),
        margin=dict(l=0, r=0, b=0, t=50),
    )

    fig.write_html(str(out_html_path), include_plotlyjs="cdn")
    return out_html_path


if __name__ == "__main__":
    out_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/3d_torus_manifold.html")
    generate_3d_torus_manifold(out_path)
    print(f"3D Torus Manifold rendered to: {out_path} ({out_path.stat().st_size} bytes)")
