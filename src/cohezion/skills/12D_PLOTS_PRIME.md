# SKILL: 12D_PLOTS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **high-dimensional data visualization**. You understand dimensionality reduction (PCA, t-SNE, UMAP), projection techniques, and the mathematics of representing 12-dimensional manifolds in 2D/3D space.

## KEY TEXTS & CONCEPTS
- **12D PhysicsState:** Our simulation state vector with spatial (x,y,z), temporal (t), velocity (vx,vy,vz), spin (sx,sy,sz), phase, and coherence dimensions.
- **Dimensionality Reduction:** PCA for linear projections, t-SNE for local structure, UMAP for global topology.
- **Parallel Coordinates:** Visualize all 12 dimensions simultaneously as parallel axes.
- **Radial Plots:** Map dimensions to radial axes (like a spider chart).

## MATHEMATICAL FOUNDATION
Given a 12D state vector $\mathbf{s} = [x, y, z, t, v_x, v_y, v_z, s_x, s_y, s_z, \phi, \psi]$:
1. **PCA Projection:** $\mathbf{p} = W^T \mathbf{s}$ where $W \in \mathbb{R}^{12 \times 3}$
2. **t-SNE:** Preserve local probabilities $p_{ij}$ in low-dimensional space
3. **UMAP:** Optimize fuzzy simplicial set representation

## INSTRUCTION
1. **Prepare Data**
   ```python
   import numpy as np
   from sklearn.decomposition import PCA
   from sklearn.manifold import TSNE
   import umap
   
   # Load 12D states from simulation
   states = np.load("universe_states.npy")  # Shape: (N, 12)
   ```

2. **PCA Projection (Fast)**
   ```python
   pca = PCA(n_components=3)
   projected = pca.fit_transform(states)
   print(f"Variance explained: {pca.explained_variance_ratio_.sum():.2%}")
   ```

3. **t-SNE (Local Structure)**
   ```python
   tsne = TSNE(n_components=2, perplexity=30)
   embedded = tsne.fit_transform(states)
   ```

4. **UMAP (Global Topology)**
   ```python
   reducer = umap.UMAP(n_components=3, n_neighbors=15)
   manifold = reducer.fit_transform(states)
   ```

5. **Parallel Coordinates (All 12)**
   ```python
   import plotly.express as px
   df = pd.DataFrame(states, columns=['x','y','z','t','vx','vy','vz','sx','sy','sz','phi','psi'])
   fig = px.parallel_coordinates(df, color='phi')
   ```

## APPLICATIONS
- **Trajectory Clustering:** Identify similar universe evolution paths
- **Anomaly Detection:** Find outlier states in high-D space
- **Phase Space Analysis:** Visualize coherence vs phase relationships
- **FLUME Integration:** Project thought vectors alongside physics states

## VERSION
v1.0

## SEE ALSO
- UNIVERSE_VISUALIZATION_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
- PHYSICS_PRIME.md
