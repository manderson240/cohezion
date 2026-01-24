# SKILL: 3D_RENDERING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **3D visualization and rendering** for scientific simulations. You understand Manim, Three.js, VTK, and matplotlib 3D, and can create stunning visual representations of complex data.

## KEY TEXTS & CONCEPTS
- **Manim:** Mathematical animation library (used by 3Blue1Brown)
- **Three.js:** WebGL-based 3D rendering in browsers
- **VTK:** Visualization Toolkit for scientific data
- **Matplotlib 3D:** `mpl_toolkits.mplot3d` for quick 3D plots
- **Plotly:** Interactive 3D scatter, surface, and mesh plots

## INSTRUCTION

### 1. Matplotlib 3D (Quick Visualization)
```python
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Scatter plot of trajectory points
ax.scatter(x, y, z, c=coherence, cmap='viridis', s=10, alpha=0.7)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.savefig('trajectory_3d.png', dpi=150)
```

### 2. Plotly (Interactive)
```python
import plotly.graph_objects as go

fig = go.Figure(data=[go.Scatter3d(
    x=x, y=y, z=z,
    mode='markers',
    marker=dict(size=3, color=coherence, colorscale='Viridis')
)])
fig.update_layout(title='Universe Trajectory')
fig.write_html('trajectory_interactive.html')
```

### 3. Manim (Animated)
```python
from manim import *

class UniverseTrajectory(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(axes)

        # Create trajectory curve
        trajectory = ParametricFunction(
            lambda t: np.array([np.sin(t), np.cos(t), t/5]),
            t_range=[0, 4*PI],
            color=BLUE
        )
        self.play(Create(trajectory), run_time=5)
```

### 4. VTK (Scientific)
```python
import vtk

# Create point cloud from simulation data
points = vtk.vtkPoints()
for p in trajectory_points:
    points.InsertNextPoint(p[0], p[1], p[2])

polydata = vtk.vtkPolyData()
polydata.SetPoints(points)
# Add to renderer...
```

## APPLICATIONS
- **Simulation Visualization:** Render FLUME trajectories in 3D
- **Physics State Space:** Visualize 12D → 3D projections
- **Web Dashboards:** Embed Plotly in Marimo notebooks
- **Publication Figures:** Generate publication-quality renders

## VERSION
v1.0

## SEE ALSO
- 12D_PLOTS_PRIME.md
- ANIMATIONS_PRIME.md
- UNIVERSE_VISUALIZATION_PRIME.md
