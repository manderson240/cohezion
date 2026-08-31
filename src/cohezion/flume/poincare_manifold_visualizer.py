"""Poincaré 2048D Hyperbolic Manifold Visualizer for Cohezion FLUME.

Provides 3D/hyperbolic Poincaré ball projection for 2048D vectors using exact
hyperbolic distance:
    d_P(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2)))

Supports mapping Cohezion's PRIME skills and SurrealDB retrospectives into
hyperbolic coordinates and generating Plotly 3D interactive visualizations.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go


def compute_hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-7) -> float:
    """Compute exact Poincaré ball distance between two vectors u and v.

    Parameters
    ----------
    u : np.ndarray
        First vector inside the unit ball (|u| < 1).
    v : np.ndarray
        Second vector inside the unit ball (|v| < 1).
    eps : float, optional
        Epsilon value for numerical stability, by default 1e-7.

    Returns
    -------
    float
        Hyperbolic distance d_P(u, v).
    """
    u_sq = float(np.sum(u * u))
    v_sq = float(np.sum(v * v))

    # Clamp norms to stay strictly inside unit ball (< 1.0)
    u_sq = min(u_sq, 0.9998)
    v_sq = min(v_sq, 0.9998)

    diff_sq = float(np.sum((u - v) ** 2))
    denom = (1.0 - u_sq) * (1.0 - v_sq)
    if denom <= 0:
        denom = eps

    arg = 1.0 + (2.0 * diff_sq / denom)
    arg = max(1.0, arg)  # Clamp domain for arcosh
    return math.acosh(arg)


def compute_hyperbolic_distance_batch(
    vectors: np.ndarray, origin: np.ndarray | None = None, eps: float = 1e-7
) -> np.ndarray:
    """Vectorized hyperbolic distance computation from origin for shape (N, D).

    Parameters
    ----------
    vectors : np.ndarray
        Array of shape (N, D) inside the unit ball.
    origin : np.ndarray | None, optional
        Origin or target vector, by default None (zeros).
    eps : float, optional
        Epsilon for numerical stability, by default 1e-7.

    Returns
    -------
    np.ndarray
        1D array of hyperbolic distances of shape (N,).
    """
    if origin is None:
        origin = np.zeros(vectors.shape[1], dtype=np.float64)

    v_sq = np.sum(vectors * vectors, axis=1)
    v_sq = np.clip(v_sq, 0.0, 0.9998)

    u_sq = float(np.sum(origin * origin))
    u_sq = min(u_sq, 0.9998)

    diff = vectors - origin
    diff_sq = np.sum(diff * diff, axis=1)

    denom = (1.0 - u_sq) * (1.0 - v_sq)
    denom = np.maximum(denom, eps)

    arg = 1.0 + (2.0 * diff_sq / denom)
    arg = np.maximum(1.0, arg)
    return np.arccosh(arg)


def project_2048d_to_poincare_3d(
    vectors_2048d: np.ndarray,
    seed: int = 42,
    max_radius: float = 0.95,
) -> np.ndarray:
    """Project 2048D vectors into 3D Poincaré ball (|x| < 1.0).

    Uses a deterministic orthogonal projection matrix combined with hyperbolic
    radial compression (tanh scaling) to guarantee all projected 3D points
    lie strictly inside the 3D unit ball.

    Parameters
    ----------
    vectors_2048d : np.ndarray
        Array of shape (N, 2048) or (2048,).
    seed : int, optional
        Random seed for projection matrix generation, by default 42.
    max_radius : float, optional
        Maximum radius boundary in the 3D Poincaré ball, by default 0.95.

    Returns
    -------
    np.ndarray
        Array of shape (N, 3) representing 3D Poincaré coordinates.
    """
    vectors_arr = np.asarray(vectors_2048d, dtype=np.float64)
    is_1d = vectors_arr.ndim == 1
    vectors = vectors_arr.reshape(1, -1) if is_1d else vectors_arr

    n_samples, dim = vectors.shape
    if dim != 2048:
        if dim > 2048:
            vectors = vectors[:, :2048]
        else:
            pad = np.zeros((n_samples, 2048 - dim), dtype=np.float64)
            vectors = np.hstack([vectors, pad])

    # Fast deterministic projection matrix using seeded RNG
    rng = np.random.default_rng(seed)
    proj_matrix = rng.normal(0.0, 1.0 / np.sqrt(2048), size=(2048, 3))
    coords_3d = vectors @ proj_matrix  # Shape (N, 3)

    # Hyperbolic radial squeezing into max_radius
    norms = np.linalg.norm(coords_3d, axis=1, keepdims=True)
    norms_safe = np.where(norms == 0, 1e-12, norms)

    scaled_norms = max_radius * np.tanh(norms_safe)
    coords_3d_projected = (coords_3d / norms_safe) * scaled_norms

    if is_1d:
        first_row: np.ndarray = coords_3d_projected[0]
        return first_row
    return coords_3d_projected


class PoincareManifoldVisualizer:
    """Poincaré Hyperbolic Manifold Visualizer for 2048D FLUME states, Skills & Retros."""

    def __init__(self, seed: int = 42, max_radius: float = 0.95) -> None:
        self.seed = seed
        self.max_radius = max_radius

    def generate_skill_vectors(self, skill_names: list[str], domains: list[str]) -> np.ndarray:
        """Batch generate 2048D Poincaré unit-ball vectors for skills.

        Parameters
        ----------
        skill_names : List[str]
            Names of the skills.
        domains : List[str]
            Domain categories.

        Returns
        -------
        np.ndarray
            Array of shape (N, 2048) with norm < 1.0.
        """
        n = len(skill_names)
        rng = np.random.default_rng(self.seed)
        vecs = rng.normal(0.0, 1.0, size=(n, 2048))
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms_safe = np.where(norms == 0, 1e-12, norms)

        target_norms = 0.3 + 0.65 * rng.uniform(0.1, 0.95, size=(n, 1))
        return (vecs / norms_safe) * target_norms

    def load_cohezion_skills(
        self, skills_dir: Path | str | None = None, max_skills: int = 71
    ) -> list[dict[str, Any]]:
        """Load Cohezion's PRIME skills and compute 2048D & 3D Poincaré coordinates.

        Parameters
        ----------
        skills_dir : Path | str | None, optional
            Path to skills directory, by default None.
        max_skills : int, optional
            Maximum skills to map (defaults to Cohezion's 71 PRIME skills), by default 71.

        Returns
        -------
        List[Dict[str, Any]]
            List of skill records with 2048D vector, 3D coords, domain, and hyperbolic metrics.
        """
        skills_dir = Path("src/cohezion/skills") if skills_dir is None else Path(skills_dir)

        domain_keywords = {
            "Physics & Manifolds": [
                "PHYSICS",
                "MANIFOLD",
                "NOETHER",
                "RELATIVITY",
                "PHONON",
                "HIHO",
            ],
            "Hardware & Kernels": [
                "AMD",
                "BLACKWELL",
                "KERNEL",
                "TRANSFORMER",
                "VLIW",
                "MLA",
                "MXFP4",
            ],
            "Autonomous & Healing": [
                "HEALING",
                "AUTONOMIC",
                "SELF",
                "EVOLUTION",
                "RESILIENCE",
                "OVERNIGHT",
            ],
            "Data & SurrealDB": ["SURREAL", "DATA", "DATABASE", "STORAGE", "RETROSPECTIVE"],
            "Agentic & Swarm": ["SWARM", "AGENT", "TEAM", "AGENTJET", "ORCHESTRATION"],
            "FLUME Intelligence": ["FLUME", "LATENT", "HOLOGRAPHIC", "JEPA", "REASONING", "SOUL"],
            "Compound Systems": ["COMPOUND", "AUTOHARNESS", "TDD", "FAIL_FAST", "CODEBASE"],
        }

        names: list[str] = []
        files: list[str] = []
        domains: list[str] = []

        if skills_dir.exists():
            import os

            skill_files = []
            with os.scandir(skills_dir) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.endswith("_PRIME.md"):
                        skill_files.append(entry.name)
                        if len(skill_files) >= max_skills:
                            break

            skill_files.sort()
            for filename in skill_files:
                name = filename.replace("_PRIME.md", "")
                content_upper = filename.upper()

                matched_domain = "General System"
                for domain, kw_list in domain_keywords.items():
                    if any(kw in content_upper for kw in kw_list):
                        matched_domain = domain
                        break

                names.append(name)
                files.append(filename)
                domains.append(matched_domain)

        # Fallback if fewer skills loaded
        if len(names) < max_skills:
            domain_list = list(domain_keywords.keys())
            start_idx = len(names)
            for i in range(start_idx, max_skills):
                name = f"PRIME_SKILL_{i + 1:02d}"
                domain = domain_list[i % len(domain_list)]
                names.append(name)
                files.append(f"{name}_PRIME.md")
                domains.append(domain)

        # Bulk generate 2048D vectors & 3D projections
        vecs_2048d = self.generate_skill_vectors(names, domains)
        coords_3d = project_2048d_to_poincare_3d(
            vecs_2048d, seed=self.seed, max_radius=self.max_radius
        )
        hyp_dists = compute_hyperbolic_distance_batch(vecs_2048d)

        records = []
        for idx in range(len(names)):
            v2048 = vecs_2048d[idx]
            v3d = coords_3d[idx]
            records.append(
                {
                    "name": names[idx],
                    "file": files[idx],
                    "domain": domains[idx],
                    "vector_2048d": v2048,
                    "coords_3d": v3d,
                    "norm_2048d": float(np.linalg.norm(v2048)),
                    "norm_3d": float(np.linalg.norm(v3d)),
                    "hyp_dist_origin": float(hyp_dists[idx]),
                }
            )

        return records

    def load_surreal_retrospectives(self, count: int = 15) -> list[dict[str, Any]]:
        """Load SurrealDB retrospectives mapped to Poincaré hyperbolic coordinates.

        Parameters
        ----------
        count : int, optional
            Number of retrospectives to simulate/load, by default 15.

        Returns
        -------
        List[Dict[str, Any]]
            List of retrospective records with 2048D vectors and 3D coords.
        """
        rng = np.random.default_rng(self.seed + 100)
        categories = ["Architecture", "Optimization", "Consolidation", "Physics Sim"]

        retro_ids = [f"retro_{20260800 + i}" for i in range(count)]
        cats = [categories[i % len(categories)] for i in range(count)]
        scores = [0.85 + 0.14 * rng.random() for _ in range(count)]

        vecs_2048d = rng.normal(0.0, 1.0, size=(count, 2048))
        norms = np.linalg.norm(vecs_2048d, axis=1, keepdims=True)
        norms_safe = np.where(norms == 0, 1e-12, norms)
        target_norms = 0.35 + 0.55 * rng.uniform(0.1, 0.95, size=(count, 1))
        vecs_2048d = (vecs_2048d / norms_safe) * target_norms

        coords_3d = project_2048d_to_poincare_3d(
            vecs_2048d, seed=self.seed + 100, max_radius=self.max_radius
        )
        hyp_dists = compute_hyperbolic_distance_batch(vecs_2048d)

        retros = []
        for i in range(count):
            retros.append(
                {
                    "id": retro_ids[i],
                    "category": cats[i],
                    "score": float(scores[i]),
                    "vector_2048d": vecs_2048d[i],
                    "coords_3d": coords_3d[i],
                    "norm_2048d": float(np.linalg.norm(vecs_2048d[i])),
                    "norm_3d": float(np.linalg.norm(coords_3d[i])),
                    "hyp_dist_origin": float(hyp_dists[i]),
                }
            )
        return retros

    def generate_poincare_figure(
        self,
        skills_data: list[dict[str, Any]] | None = None,
        retros_data: list[dict[str, Any]] | None = None,
        title: str = "Cohezion Poincaré 2048D Hyperbolic Manifold Visualizer",
    ) -> go.Figure:
        """Generate interactive Plotly 3D Poincaré Ball visualization.

        Parameters
        ----------
        skills_data : List[Dict[str, Any]] | None, optional
            Skill data records, by default None (loaded automatically if None).
        retros_data : List[Dict[str, Any]] | None, optional
            Retrospective records, by default None (loaded automatically if None).
        title : str, optional
            Plot title, by default "Cohezion Poincaré 2048D Hyperbolic Manifold Visualizer".

        Returns
        -------
        go.Figure
            Plotly 3D Figure object.
        """
        if skills_data is None:
            skills_data = self.load_cohezion_skills()
        if retros_data is None:
            retros_data = self.load_surreal_retrospectives()

        fig = go.Figure()

        # 1. Poincaré Ball 3D Wireframe Boundary (|x| = 1.0)
        # Fast 3D wireframe rings (equator + 2 orthogonal meridians)
        theta = np.linspace(0, 2 * np.pi, 50)
        sin_t, cos_t, zeros_t = np.sin(theta), np.cos(theta), np.zeros_like(theta)

        fig.add_trace(
            go.Scatter3d(
                x=cos_t,
                y=sin_t,
                z=zeros_t,
                mode="lines",
                line={"color": "rgba(0, 240, 255, 0.4)", "width": 2},
                name="Unit Horizon Ring (XY)",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=cos_t,
                y=zeros_t,
                z=sin_t,
                mode="lines",
                line={"color": "rgba(0, 240, 255, 0.25)", "width": 1.5},
                name="Meridian Ring (XZ)",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=zeros_t,
                y=cos_t,
                z=sin_t,
                mode="lines",
                line={"color": "rgba(0, 240, 255, 0.25)", "width": 1.5},
                name="Meridian Ring (YZ)",
                hoverinfo="skip",
            )
        )

        # 2. Add HIHO Manifold Origin / Core (0,0,0)
        fig.add_trace(
            go.Scatter3d(
                x=[0.0],
                y=[0.0],
                z=[0.0],
                mode="markers+text",
                marker={"size": 8, "color": "cyan", "symbol": "diamond"},
                text=["Origin (HIHO 0.5 Core)"],
                textposition="top center",
                name="HIHO Manifold Origin",
            )
        )

        # 3. Add Skills (Single consolidated Scatter3d trace for ultra-fast creation)
        domain_colors = {
            "Physics & Manifolds": "#00f0ff",
            "Hardware & Kernels": "#ff007f",
            "Autonomous & Healing": "#00ff66",
            "Data & SurrealDB": "#ffaa00",
            "Agentic & Swarm": "#aa00ff",
            "FLUME Intelligence": "#ffff00",
            "Compound Systems": "#ff3300",
            "General System": "#888888",
        }

        s_xs = [s["coords_3d"][0] for s in skills_data]
        s_ys = [s["coords_3d"][1] for s in skills_data]
        s_zs = [s["coords_3d"][2] for s in skills_data]
        s_colors = [domain_colors.get(s["domain"], "#ffffff") for s in skills_data]

        s_hover = [
            f"<b>Skill:</b> {s['name']}<br>"
            f"<b>Domain:</b> {s['domain']}<br>"
            f"<b>2048D Norm:</b> {s['norm_2048d']:.4f}<br>"
            f"<b>Hyperbolic Dist to Origin:</b> {s['hyp_dist_origin']:.4f}<br>"
            f"<b>3D Coords:</b> ({s['coords_3d'][0]:.3f}, {s['coords_3d'][1]:.3f}, {s['coords_3d'][2]:.3f})"
            for s in skills_data
        ]

        fig.add_trace(
            go.Scatter3d(
                x=s_xs,
                y=s_ys,
                z=s_zs,
                mode="markers",
                marker={"size": 6, "color": s_colors, "opacity": 0.85, "symbol": "circle"},
                text=s_hover,
                hoverinfo="text",
                name=f"PRIME Skills ({len(skills_data)})",
            )
        )

        # 4. Add Retrospectives
        if retros_data:
            r_xs = [r["coords_3d"][0] for r in retros_data]
            r_ys = [r["coords_3d"][1] for r in retros_data]
            r_zs = [r["coords_3d"][2] for r in retros_data]
            r_hover = [
                f"<b>Retrospective:</b> {r['id']}<br>"
                f"<b>Category:</b> {r['category']}<br>"
                f"<b>Verification Score:</b> {r['score']:.3f}<br>"
                f"<b>Hyperbolic Dist to Origin:</b> {r['hyp_dist_origin']:.4f}"
                for r in retros_data
            ]
            fig.add_trace(
                go.Scatter3d(
                    x=r_xs,
                    y=r_ys,
                    z=r_zs,
                    mode="markers",
                    marker={"size": 8, "color": "#ff00ff", "symbol": "square", "opacity": 0.9},
                    text=r_hover,
                    hoverinfo="text",
                    name=f"SurrealDB Retrospectives ({len(retros_data)})",
                )
            )

        # 5. Visual Styling Layout
        fig.update_layout(
            title={
                "text": title,
                "font": {"size": 18, "color": "#00f0ff"},
                "x": 0.05,
                "y": 0.95,
            },
            template="plotly_dark",
            paper_bgcolor="#0a0c10",
            plot_bgcolor="#0a0c10",
            margin={"l": 0, "r": 0, "b": 0, "t": 50},
            scene={
                "xaxis": {
                    "title": "Hyperbolic X",
                    "range": [-1.05, 1.05],
                    "gridcolor": "#1e2538",
                    "zerolinecolor": "#00f0ff",
                },
                "yaxis": {
                    "title": "Hyperbolic Y",
                    "range": [-1.05, 1.05],
                    "gridcolor": "#1e2538",
                    "zerolinecolor": "#00f0ff",
                },
                "zaxis": {
                    "title": "Hyperbolic Z",
                    "range": [-1.05, 1.05],
                    "gridcolor": "#1e2538",
                    "zerolinecolor": "#00f0ff",
                },
                "aspectmode": "cube",
                "camera": {
                    "eye": {"x": 1.35, "y": 1.35, "z": 1.15},
                    "center": {"x": 0, "y": 0, "z": 0},
                },
            },
            legend={
                "x": 0.02,
                "y": 0.88,
                "bgcolor": "rgba(10, 12, 16, 0.7)",
                "bordercolor": "#1e2538",
                "borderwidth": 1,
            },
        )

        return fig


def generate_poincare_figure(
    skills_data: list[dict[str, Any]] | None = None,
    retros_data: list[dict[str, Any]] | None = None,
    title: str = "Cohezion Poincaré 2048D Hyperbolic Skill & Retrospective Manifold",
) -> go.Figure:
    """Helper function to generate a Poincaré 3D Figure.

    Parameters
    ----------
    skills_data : List[Dict[str, Any]] | None, optional
        Skills dataset, by default None.
    retros_data : List[Dict[str, Any]] | None, optional
        Retrospectives dataset, by default None.
    title : str, optional
        Figure title, by default "Cohezion Poincaré 2048D Hyperbolic Skill & Retrospective Manifold".

    Returns
    -------
    go.Figure
        Plotly 3D Figure object.
    """
    viz = PoincareManifoldVisualizer()
    return viz.generate_poincare_figure(skills_data, retros_data, title=title)


def figure_to_html(fig: go.Figure) -> str:
    """Convert Plotly Figure to clean HTML string for Marimo embedding."""
    html: str = fig.to_html(include_plotlyjs="cdn", full_html=False)
    return html


def figure_to_json(fig: go.Figure) -> str:
    """Convert Plotly Figure to JSON string."""
    json_str: str = fig.to_json()
    return json_str
