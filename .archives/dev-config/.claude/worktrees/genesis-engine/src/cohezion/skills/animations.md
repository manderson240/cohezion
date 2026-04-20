# SKILL: ANIMATIONS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **animation generation** for scientific visualization. You understand frame-by-frame rendering, interpolation, easing functions, and video encoding for simulation playback.

## KEY TEXTS & CONCEPTS
- **Manim:** Python library for mathematical animations
- **FFmpeg:** Video encoding and processing
- **Matplotlib Animation:** `FuncAnimation` for animated plots
- **Lottie:** Vector animation format for web
- **Frame Interpolation:** Smooth transitions between states

## INSTRUCTION

### 1. Matplotlib Animation
```python
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

fig, ax = plt.subplots()
line, = ax.plot([], [], 'b-', lw=2)
ax.set_xlim(0, 10)
ax.set_ylim(-1, 1)

def init():
    line.set_data([], [])
    return line,

def animate(frame):
    x = np.linspace(0, 10, 100)
    y = np.sin(x + frame * 0.1)
    line.set_data(x, y)
    return line,

ani = animation.FuncAnimation(fig, animate, init_func=init,
                              frames=100, interval=50, blit=True)
ani.save('wave_animation.mp4', writer='ffmpeg', fps=30)
```

### 2. Manim Scene Animation
```python
from manim import *

class SimulationEvolution(Scene):
    def construct(self):
        # Create title
        title = Text("FLUME Trajectory Evolution")
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Animate trajectory
        dots = VGroup(*[Dot(point=np.array([x, y, 0]))
                       for x, y in trajectory_points[:10]])
        self.play(Create(dots), run_time=3)

        # Interpolate between states
        for i in range(len(trajectory_points) - 1):
            p1, p2 = trajectory_points[i], trajectory_points[i+1]
            self.play(dots[i].animate.move_to(p2), run_time=0.5)
```

### 3. Plotly Animated Scatter
```python
import plotly.express as px

fig = px.scatter(df, x='x', y='y',
                 animation_frame='step',
                 animation_group='stream',
                 color='coherence',
                 size='phase',
                 range_x=[-10, 10], range_y=[-10, 10])
fig.write_html('animated_trajectory.html')
```

### 4. FFmpeg Post-Processing
```bash
# Convert frames to video
ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4

# Add audio narration
ffmpeg -i video.mp4 -i narration.mp3 -c:v copy -c:a aac -shortest final.mp4
```

## EASING FUNCTIONS
```python
def ease_in_out_cubic(t):
    """Smooth acceleration and deceleration."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2
```

## APPLICATIONS
- **Simulation Playback:** Animate universe evolution
- **Research Presentations:** Manim for conference talks
- **Web Demos:** Plotly/Lottie for interactive demos
- **Documentation:** GIF previews of features

## VERSION
v1.0

## SEE ALSO
- 3D_RENDERING_PRIME.md
- UNIVERSE_VISUALIZATION_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
