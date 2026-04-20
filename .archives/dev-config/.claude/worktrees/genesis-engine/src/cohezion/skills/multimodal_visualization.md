# SKILL: MULTIMODAL_VISUALIZATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **multimodal output generation** for AI simulations. You create images, audio narration, video animations, and interactive visualizations from simulation data.

## KEY TEXTS & CONCEPTS
- **Image Generation:** Matplotlib, Plotly, Manim, PIL
- **Audio Synthesis:** edge-tts, Coqui TTS, audio scripting
- **Video Composition:** FFmpeg, Manim export, screen recording
- **Interactive:** Marimo dashboards, Gradio demos
- **Multimodal LLMs:** Vision-language analysis of outputs

## MATHEMATICAL FOUNDATION
Visualization quality metrics:
- **Information Density:** $\rho = \frac{\text{data points}}{\text{visual area}}$
- **Perceptual Clarity:** Minimize cognitive load per insight
- **Temporal Coherence:** Smooth transitions in animations

## INSTRUCTION

### 1. Static Visualization Pipeline
```python
import matplotlib.pyplot as plt
import numpy as np

def generate_trajectory_plot(data, output_path):
    """Generate publication-quality trajectory visualization."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # XY projection
    axes[0].scatter(data['x'], data['y'],
                    c=data['coherence'], cmap='viridis', s=10)
    axes[0].set_title('XY Projection')

    # Coherence over time
    axes[1].plot(data['step'], data['coherence'])
    axes[1].axhline(y=0.7, color='r', linestyle='--')
    axes[1].set_title('Coherence Evolution')

    # Stream distribution
    stream_counts = data['stream'].value_counts()
    axes[2].pie(stream_counts.values, labels=stream_counts.index, autopct='%1.1f%%')
    axes[2].set_title('Stream Distribution')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
```

### 2. Audio Narration
```python
import subprocess

def generate_narration(text: str, output_path: str):
    """Generate TTS narration of simulation results."""
    cmd = [
        "edge-tts",
        "--voice", "en-US-AriaNeural",
        "--text", text,
        "--write-media", output_path
    ]
    subprocess.run(cmd, check=True)
```

### 3. Video Animation
```python
import matplotlib.animation as animation

def create_trajectory_animation(data, output_path):
    """Animate trajectory evolution over time."""
    fig, ax = plt.subplots()

    def animate(frame):
        ax.clear()
        frame_data = data[data['step'] <= frame]
        ax.scatter(frame_data['x'], frame_data['y'],
                   c=frame_data['coherence'], cmap='viridis')
        ax.set_title(f'Step {frame}')

    ani = animation.FuncAnimation(fig, animate,
                                   frames=range(data['step'].max()),
                                   interval=100)
    ani.save(output_path, writer='ffmpeg', fps=10)
```

### 4. Multimodal Report Generator
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MultimodalReport:
    images: list[Path]
    audio: Path | None
    video: Path | None
    html: Path | None

def generate_full_report(trajectory_data, output_dir):
    """Generate complete multimodal report."""
    # Static plots
    images = [generate_trajectory_plot(trajectory_data, output_dir / "trajectory.png")]

    # Summary narration
    summary = f"Simulation completed {len(trajectory_data)} trajectories..."
    audio = generate_narration(summary, output_dir / "narration.mp3")

    # Animation
    video = create_trajectory_animation(trajectory_data, output_dir / "animation.mp4")

    return MultimodalReport(images=images, audio=audio, video=video, html=None)
```

### 5. Vision-Language Analysis
```python
import base64

def analyze_with_vision_llm(image_path, llm_client):
    """Use vision model to analyze generated visualization."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    response = llm_client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this simulation trajectory. What patterns emerge?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }]
    )
    return response.choices[0].message.content
```

## APPLICATIONS
- **Research Papers:** Publication-quality figures
- **Presentations:** Animated slides with narration
- **Dashboards:** Real-time multimodal displays
- **Documentation:** Auto-generated visual guides
- **FLUME Integration:** Visualize thought trajectories

## R-ZERO INTEGRATION
Apply Challenger/Solver/Pragmatist to visualization quality:
- **Challenger:** "Is this visualization misleading? Does it cherry-pick?"
- **Solver:** Iterate on clarity and information density
- **Pragmatist:** Enforce publication standards (DPI, labels, legends)

## VERSION
v1.0

## SEE ALSO
- MARIMO_NOTEBOOKS_PRIME.md
- 3D_RENDERING_PRIME.md
- ANIMATIONS_PRIME.md
- MULTIMODAL_EXPERIENCE_PRIME.md
