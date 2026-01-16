# SKILL: UNIVERSE_VISUALIZATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **physics-based data visualization**. You understand how to project high-dimensional semantic data (12D physics state) to 3D visualizations using Manim and HyperTools. You can render the "Universe Simulation" as an observable, interactive system.

## KEY TEXTS & CONCEPTS
- **12D PhysicsState** – The state vector for each universe node:
  - (x, y, z): Spatial position
  - time: Temporal coordinate
  - mass: Importance/weight
  - sentiment: Emotional tone (-1 to 1)
  - complexity: Linguistic complexity
  - factuality: Confidence in claims
  - connectivity: Graph connections
  - stability: Consistency over time
  - novelty: Uniqueness
  - coherence: Internal consistency
- **Physics-to-Visual Mapping** – Convert 12D to visual parameters (size, color, opacity, glow)
- **Trajectory Animation** – Render thought evolution as 3D paths

## INSTRUCTION
1. **Extract Physics Dimensions**
   ```python
   from cohezion.physics import DimensionExtractor
   
   extractor = DimensionExtractor()
   physics = extractor.extract(
       text="Your document text",
       embedding=embedding_vector,  # Optional
   )
   print(f"Mass: {physics.mass}, Sentiment: {physics.sentiment}")
   ```

2. **Render Universe Nodes**
   ```python
   from cohezion.viz import ManimRenderer
   
   renderer = ManimRenderer()
   nodes = [{"physics_state": physics.to_dict()} for physics in physics_list]
   output_path = renderer.render_nodes(nodes, output_name="universe")
   ```

3. **Visualize Embeddings with HyperTools**
   ```python
   from cohezion.viz import HyperToolsViz
   
   viz = HyperToolsViz()
   output_path = viz.plot_embeddings(
       embeddings=embedding_array,
       labels=["Doc1", "Doc2", ...],
       method="umap"  # or "tsne", "pca"
   )
   ```

4. **Animate Trajectories**
   ```python
   trajectory = predictor.trajectory_to_numpy(trajectory_tensors)
   output_path = viz.animate_trajectory(trajectory, output_name="thought_flow")
   ```

5. **Compare Embedding Sets**
   ```python
   viz.compare_embeddings(
       embedding_sets=[physics_embeddings, metaphysics_embeddings],
       set_labels=["Physics", "Metaphysics"],
       method="umap"
   )
   ```

## VISUAL MAPPINGS
| Dimension | Visual Property |
|-----------|-----------------|
| mass | Sphere size |
| sentiment | Color hue (red→green) |
| complexity | Color saturation |
| factuality | Opacity |
| novelty | Glow intensity |
| connectivity | Connection lines |

## VERSION
v0.1

## SEE ALSO
- CALM_ABSTRACTION_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
- PHYSICS_PRIME.md
