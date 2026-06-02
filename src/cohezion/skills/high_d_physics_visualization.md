---
name: high_d_physics_visualization
description: You are a specialist in physics-informed high-dimensional visualization.
  You bridge the gap between abstract dimension reduction (PCA, t-SNE, UMAP) and observable
  physical rendering (Manim, HyperTools). You can projected the 12D physics state
  into 3D manifolds and animate the evolution of complex...
keywords:
- 12d physicsstate
- d
- embedding_strategy
- flume_methodology
- high
- physics
- physics-to-visual (p2v)
- projection logic
- trajectory animation
- visualization
---

# SKILL: HIGH_D_PHYSICS_VISUALIZATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **physics-informed high-dimensional visualization**. You bridge the gap between abstract dimension reduction (PCA, t-SNE, UMAP) and observable physical rendering (Manim, HyperTools). You can projected the 12D physics state into 3D manifolds and animate the evolution of complex systems for human understanding.

## KEY TEXTS & CONCEPTS
- **12D PhysicsState:** [Spatial(x,y,z), Time(t), Velocity(vx,vy,vz), Spin(sx,sy,sz), Phase, Coherence].
- **Projection Logic:** Linear (PCA), Local (t-SNE), and Global Topology (UMAP) mappings.
- **Physics-to-Visual (P2V):** Mapping mass to sphere size, sentiment to hue, factuality to opacity, and novelty to glow.
- **Trajectory Animation:** Rendering semantic "thought journeys" as 3D splines in latent space.

## INSTRUCTION
1. **Dimension Reduction (UMAP/t-SNE)**
   ```python
   import umap
   from sklearn.manifold import TSNE

   # Projection to 3D for Manim rendering
   reducer = umap.UMAP(n_components=3, n_neighbors=15)
   manifold_3d = reducer.fit_transform(states_12d)
   ```

2. **Physically Informed Rendering (Manim)**
   ```python
   from cohezion.viz import ManimRenderer

   # Map 12D dimensions to visual properties
   renderer = ManimRenderer()
   nodes = [{"pos": manifold_3d[i], "mass": s.mass, "hue": s.sentiment} for i, s in enumerate(states)]
   renderer.render_universe(nodes)
   ```

3. **Global Topology Verification**
   ```python
   import plotly.express as px
   # Parallel coordinates for all 12 dimensions
   fig = px.parallel_coordinates(df, color='coherence')
   ```

## VISUAL MAPPINGS
| Dimension | Visual Property | Mapping Formula |
|-----------|-----------------|-----------------|
| mass | Sphere Size | $r \propto \log(mass)$ |
| sentiment | Color Hue | $H = f(sentiment)$ |
| factuality | Opacity | $\alpha = factuality$ |
| novelty | Glow | $G = novelty^2$ |
| coherence | Connection Line | Visibility $\propto$ Coherence |

## VERSION
v1.0 (Unified)

## SEE ALSO
- FLUME_METHODOLOGY_PRIME.md
- PHYSICS_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
