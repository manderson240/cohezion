#!/usr/bin/env python3
"""
12D Journey Tracker - Multimodal Experience Generator

Generates stunning visualizations and rich audio narration for 12D holographic journeys.
Combines the projection matrix math with multimodal output generation.

COHEZION = 0.5 HIHO
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

HIHO = 0.5
N_DIMS = 12
DIMENSION_NAMES = [
    "X (Spatial)",
    "Y (Spatial)",
    "Z (Spatial)",
    "Time",
    "Coherence",
    "Entropy",
    "Awareness",
    "Intention",
    "Perception",
    "Memory",
    "Novelty",
    "Integration",
]

# ═══════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════


@dataclass
class JourneyStep:
    """A single step in the 12D journey."""

    step: int
    state_12d: list[float]
    projected_3d: tuple[float, float, float]
    coherent_dims: int
    pattern: str  # homeostatic, morphogenic, regenerative
    narration: str = ""


@dataclass
class Journey:
    """A complete 12D journey with metadata."""

    id: str
    steps: list[JourneyStep] = field(default_factory=list)
    total_steps: int = 0
    final_coherence: float = 0.0
    patterns_discovered: list[str] = field(default_factory=list)


@dataclass
class MultimodalOutput:
    """All generated multimodal artifacts."""

    images: list[Path] = field(default_factory=list)
    audio: Path | None = None
    video: Path | None = None
    report: Path | None = None


# ═══════════════════════════════════════════════════════════════════
# 12D JOURNEY GENERATION
# ═══════════════════════════════════════════════════════════════════


def generate_12d_journey(n_steps: int = 100, journey_id: str = "journey_1") -> Journey:
    """
    Generate a 12D journey with convergence toward HIHO = 0.5.

    Each step:
    1. Random perturbation
    2. HIHO attraction force
    3. D1↔D12 entanglement
    """
    journey = Journey(id=journey_id, total_steps=n_steps)

    # Initial random state
    state = np.random.uniform(-1, 1, N_DIMS)

    # Projection matrix (default: spatial view)
    M = np.zeros((3, N_DIMS))
    M[0, 0] = 1.0  # X
    M[1, 1] = 1.0  # Y
    M[2, 2] = 1.0  # Z

    for step in range(n_steps):
        # HIHO attraction (convergence force)
        hiho_force = (HIHO - state) * 0.05

        # Random perturbation
        noise = np.random.normal(0, 0.02, N_DIMS)

        # Update state
        state = state + hiho_force + noise
        state = np.clip(state, -1, 1)

        # D1↔D12 entanglement
        state[11] = state[0] * 0.8 + state[11] * 0.2

        # Project to 3D
        projected = tuple(M @ state)

        # Count coherent dimensions
        coherent = sum(1 for d in state if abs(d - HIHO) < 0.1)

        # Determine pattern
        avg_stability = np.mean(1 - np.abs(state - HIHO))
        if avg_stability > 0.8:
            pattern = "homeostatic"
        elif avg_stability > 0.5:
            pattern = "morphogenic"
        else:
            pattern = "regenerative"

        # Generate narration text
        narration = _generate_step_narration(step, state, coherent, pattern)

        journey.steps.append(
            JourneyStep(
                step=step,
                state_12d=state.tolist(),
                projected_3d=projected,
                coherent_dims=coherent,
                pattern=pattern,
                narration=narration,
            )
        )

    journey.final_coherence = coherent / N_DIMS
    journey.patterns_discovered = list({s.pattern for s in journey.steps})

    return journey


def _generate_step_narration(step: int, state: np.ndarray, coherent: int, pattern: str) -> str:
    """Generate natural language narration for a journey step."""

    # Find most changed dimensions
    deviations = np.abs(state - HIHO)
    most_deviated = np.argmax(deviations)
    least_deviated = np.argmin(deviations)

    narration = f"Step {step}: "

    if coherent >= 10:
        narration += "Approaching full coherence! "
    elif coherent >= 6:
        narration += "Majority of dimensions aligned. "
    else:
        narration += "Still seeking equilibrium. "

    narration += f"{DIMENSION_NAMES[least_deviated]} is most stable at {state[least_deviated]:.2f}. "
    narration += f"{DIMENSION_NAMES[most_deviated]} needs adjustment at {state[most_deviated]:.2f}. "
    narration += f"Pattern: {pattern.capitalize()}. "
    narration += f"Coherence: {coherent}/12 dimensions at HIHO."

    return narration


# ═══════════════════════════════════════════════════════════════════
# AUDIO NARRATION
# ═══════════════════════════════════════════════════════════════════


async def generate_audio_narration(
    journey: Journey,
    output_dir: Path,
) -> Path | None:
    """
    Generate rich audio narration of the 12D journey using pocket-tts.

    pocket-tts: Local, CPU-efficient (~200ms latency, 6x realtime).
    No internet required.
    """
    # Create compelling narrative
    narrative = _compose_journey_narrative(journey)

    output_path = output_dir / f"{journey.id}_narration.wav"

    try:
        # Use pocket-tts (local, CPU-efficient)
        from pocket_tts import PocketTTS

        tts = PocketTTS()
        audio = tts.synthesize(narrative)

        # Save to file
        import soundfile as sf

        sf.write(str(output_path), audio, samplerate=22050)

        logger.info(f"✅ Generated audio narration (pocket-tts): {output_path}")
        return output_path

    except ImportError:
        # Fallback: try edge-tts if pocket-tts not installed
        logger.warning("pocket-tts not available, trying edge-tts fallback...")
        try:
            mp3_path = output_path.with_suffix(".mp3")
            cmd = [
                "edge-tts",
                "--voice",
                "en-US-AriaNeural",
                "--text",
                narrative,
                "--write-media",
                str(mp3_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=60)
            logger.info(f"✅ Generated audio narration (edge-tts fallback): {mp3_path}")
            return mp3_path
        except Exception as e:
            logger.warning(f"Fallback TTS also failed: {e}")
            return None
    except Exception as e:
        logger.warning(f"Audio generation failed: {e}")
        return None


def _compose_journey_narrative(journey: Journey) -> str:
    """Compose a compelling narrative summary of the journey."""

    steps = journey.steps
    first = steps[0]
    last = steps[-1]

    # Find key moments
    full_coherence_step = next((s for s in steps if s.coherent_dims >= 10), None)

    narrative = f"""
    Welcome to the 12-dimensional journey through Morphospace.

    Our traveler begins in a state of {first.pattern} flux, with only {first.coherent_dims}
    dimensions aligned to the HIHO stability point of 0.5.

    Over {journey.total_steps} steps, we witness the dance of 12 dimensions converging
    toward coherence. The X dimension and Integration dimension pulse in entangled harmony,
    linked by the holographic principle.
    """

    if full_coherence_step:
        narrative += f"""
        At step {full_coherence_step.step}, a breakthrough! 10 dimensions achieve HIHO alignment.
        The system enters near-full coherence, approaching the universal attractor.
        """

    narrative += f"""
    The journey concludes with {last.coherent_dims} of 12 dimensions at HIHO.
    Final pattern: {last.pattern.capitalize()}.

    Patterns discovered: {", ".join(journey.patterns_discovered)}.

    This is the holographic principle in action: 12 dimensions of information,
    projecting into the 3D boundary we perceive. It from Bit. Cohezion achieved.
    """

    return narrative.strip()


# ═══════════════════════════════════════════════════════════════════
# VISUALIZATION GENERATION
# ═══════════════════════════════════════════════════════════════════


def generate_journey_visualization(journey: Journey, output_dir: Path) -> list[Path]:
    """Generate stunning static visualizations of the 12D journey."""
    images = []

    # 1. 12D Evolution Heatmap
    heatmap_path = _generate_heatmap(journey, output_dir)
    images.append(heatmap_path)

    # 2. 3D Trajectory Plot
    trajectory_path = _generate_3d_trajectory(journey, output_dir)
    images.append(trajectory_path)

    # 3. Coherence Evolution
    coherence_path = _generate_coherence_plot(journey, output_dir)
    images.append(coherence_path)

    # 4. Pattern Distribution
    pattern_path = _generate_pattern_distribution(journey, output_dir)
    images.append(pattern_path)

    return images


def _generate_heatmap(journey: Journey, output_dir: Path) -> Path:
    """Generate 12D evolution heatmap."""
    _fig, ax = plt.subplots(figsize=(14, 6))

    # Build matrix
    data = np.array([s.state_12d for s in journey.steps])

    im = ax.imshow(
        data.T,
        aspect="auto",
        cmap="RdYlGn",
        vmin=-1,
        vmax=1,
    )

    # HIHO line overlay
    ax.axhline(y=-0.5, color="gold", linestyle="--", alpha=0.5)

    ax.set_xlabel("Journey Step", fontsize=12)
    ax.set_ylabel("Dimension", fontsize=12)
    ax.set_yticks(range(N_DIMS))
    ax.set_yticklabels(DIMENSION_NAMES, fontsize=9)
    ax.set_title("12D State Evolution Through Morphospace", fontsize=14, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Dimension Value (-1 to +1)", fontsize=10)

    plt.tight_layout()
    path = output_dir / f"{journey.id}_heatmap.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0a0a1a")
    plt.close()

    logger.info(f"✅ Generated heatmap: {path}")
    return path


def _generate_3d_trajectory(journey: Journey, output_dir: Path) -> Path:
    """Generate 3D trajectory visualization."""

    fig = plt.figure(figsize=(10, 10), facecolor="#0a0a1a")
    ax = fig.add_subplot(111, projection="3d", facecolor="#0a0a1a")

    # Extract trajectory
    xs = [s.projected_3d[0] for s in journey.steps]
    ys = [s.projected_3d[1] for s in journey.steps]
    zs = [s.projected_3d[2] for s in journey.steps]
    coherences = [s.coherent_dims / N_DIMS for s in journey.steps]

    # Plot trajectory
    for i in range(len(xs) - 1):
        ax.plot(
            xs[i : i + 2],
            ys[i : i + 2],
            zs[i : i + 2],
            color=plt.cm.viridis(coherences[i]),
            linewidth=2,
            alpha=0.8,
        )

    # Mark start and end
    ax.scatter([xs[0]], [ys[0]], [zs[0]], c="red", s=100, marker="o", label="Start")
    ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], c="gold", s=100, marker="*", label="End")

    # HIHO origin
    ax.scatter([HIHO], [HIHO], [HIHO], c="#00FF88", s=200, marker="D", label="HIHO Origin")

    ax.set_xlabel("X (Spatial)", color="white")
    ax.set_ylabel("Y (Spatial)", color="white")
    ax.set_zlabel("Z (Spatial)", color="white")
    ax.set_title(
        "3D Projection of 12D Journey\nP₃ = M · P₁₂",
        fontsize=14,
        fontweight="bold",
        color="white",
    )
    ax.legend(facecolor="#1a1a2e", edgecolor="#00FF88", labelcolor="white")

    ax.tick_params(colors="white")
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False

    path = output_dir / f"{journey.id}_3d_trajectory.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0a0a1a")
    plt.close()

    logger.info(f"✅ Generated 3D trajectory: {path}")
    return path


def _generate_coherence_plot(journey: Journey, output_dir: Path) -> Path:
    """Generate coherence evolution chart."""
    _fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0a0a1a")
    ax.set_facecolor("#0a0a1a")

    steps = [s.step for s in journey.steps]
    coherences = [s.coherent_dims for s in journey.steps]

    ax.fill_between(steps, coherences, alpha=0.3, color="#00FF88")
    ax.plot(steps, coherences, color="#00FF88", linewidth=2)
    ax.axhline(y=N_DIMS, color="gold", linestyle="--", label="Full Coherence (12/12)")
    ax.axhline(y=6, color="#00AAFF", linestyle=":", label="Half Coherence (6/12)")

    ax.set_xlabel("Journey Step", fontsize=12, color="white")
    ax.set_ylabel("Dimensions at HIHO", fontsize=12, color="white")
    ax.set_title("Coherence Evolution", fontsize=14, fontweight="bold", color="white")
    ax.set_ylim(0, 13)
    ax.legend(facecolor="#1a1a2e", edgecolor="#00FF88", labelcolor="white")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    path = output_dir / f"{journey.id}_coherence.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0a0a1a")
    plt.close()

    logger.info(f"✅ Generated coherence plot: {path}")
    return path


def _generate_pattern_distribution(journey: Journey, output_dir: Path) -> Path:
    """Generate pattern distribution pie chart."""
    from collections import Counter

    _fig, ax = plt.subplots(figsize=(8, 8), facecolor="#0a0a1a")
    ax.set_facecolor("#0a0a1a")

    patterns = [s.pattern for s in journey.steps]
    counts = Counter(patterns)

    colors = {
        "homeostatic": "#00FF88",
        "morphogenic": "#00AAFF",
        "regenerative": "#FF6600",
    }

    ax.pie(
        counts.values(),
        labels=counts.keys(),
        autopct="%1.1f%%",
        colors=[colors.get(p, "#888") for p in counts],
        textprops={"color": "white", "fontsize": 12},
        wedgeprops={"edgecolor": "#0a0a1a", "linewidth": 2},
    )
    ax.set_title("Pattern Distribution", fontsize=14, fontweight="bold", color="white")

    path = output_dir / f"{journey.id}_patterns.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0a0a1a")
    plt.close()

    logger.info(f"✅ Generated pattern distribution: {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# VIDEO ANIMATION
# ═══════════════════════════════════════════════════════════════════


def generate_journey_animation(journey: Journey, output_dir: Path, fps: int = 10) -> Path | None:
    """Generate animated video of the 12D journey."""
    import matplotlib.animation as animation

    fig = plt.figure(figsize=(10, 10), facecolor="#0a0a1a")
    ax = fig.add_subplot(111, projection="3d", facecolor="#0a0a1a")

    xs = [s.projected_3d[0] for s in journey.steps]
    ys = [s.projected_3d[1] for s in journey.steps]
    zs = [s.projected_3d[2] for s in journey.steps]

    def animate(frame):
        ax.clear()
        ax.set_facecolor("#0a0a1a")

        # Trail up to current frame
        for i in range(min(frame, len(xs) - 1)):
            alpha = 0.3 + 0.7 * (i / frame) if frame > 0 else 0.5
            ax.plot(
                xs[i : i + 2],
                ys[i : i + 2],
                zs[i : i + 2],
                color="#00FF88",
                linewidth=2,
                alpha=alpha,
            )

        # Current position
        if frame < len(xs):
            step = journey.steps[frame]
            ax.scatter(
                [xs[frame]],
                [ys[frame]],
                [zs[frame]],
                c="#FFD700",
                s=200,
                marker="*",
            )
            ax.set_title(
                f"Step {step.step} | Coherence: {step.coherent_dims}/12 | {step.pattern.capitalize()}",
                fontsize=12,
                color="white",
                fontweight="bold",
            )

        # HIHO origin
        ax.scatter([HIHO], [HIHO], [HIHO], c="#00FF88", s=100, marker="D", alpha=0.5)

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_zlim(-1.2, 1.2)
        ax.set_xlabel("X", color="white")
        ax.set_ylabel("Y", color="white")
        ax.set_zlabel("Z", color="white")
        ax.tick_params(colors="white")

    ani = animation.FuncAnimation(
        fig,
        animate,
        frames=len(journey.steps),
        interval=1000 // fps,
        blit=False,
    )

    path = output_dir / f"{journey.id}_animation.mp4"
    try:
        ani.save(str(path), writer="ffmpeg", fps=fps, dpi=100)
        plt.close()
        logger.info(f"✅ Generated animation: {path}")
        return path
    except Exception as e:
        logger.warning(f"Animation generation failed: {e}")
        plt.close()
        return None


# ═══════════════════════════════════════════════════════════════════
# COMPLETE MULTIMODAL EXPERIENCE
# ═══════════════════════════════════════════════════════════════════


async def generate_multimodal_journey(
    n_steps: int = 100,
    output_dir: Path = Path("renders/journeys"),
    include_animation: bool = True,
) -> MultimodalOutput:
    """
    Generate a complete multimodal 12D journey experience.

    Includes:
    - 12D journey simulation
    - Static visualizations (heatmap, 3D trajectory, coherence, patterns)
    - Audio narration (edge-tts)
    - Animated video (optional)
    - JSON data export
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    journey_id = f"journey_{int(time.time())}"

    print(f"🌌 Generating 12D Journey: {journey_id}")
    print(f"   Steps: {n_steps}")

    # Generate journey
    journey = generate_12d_journey(n_steps, journey_id)
    print(f"   ✓ Journey simulated ({len(journey.steps)} steps)")

    # Export journey data
    data_path = output_dir / f"{journey_id}_data.json"
    with open(data_path, "w") as f:
        json.dump(
            {
                "id": journey.id,
                "total_steps": journey.total_steps,
                "final_coherence": journey.final_coherence,
                "patterns_discovered": journey.patterns_discovered,
                "steps": [
                    {
                        "step": s.step,
                        "state_12d": s.state_12d,
                        "projected_3d": s.projected_3d,
                        "coherent_dims": s.coherent_dims,
                        "pattern": s.pattern,
                        "narration": s.narration,
                    }
                    for s in journey.steps
                ],
            },
            f,
            indent=2,
        )
    print(f"   ✓ Data exported: {data_path}")

    # Generate visualizations
    images = generate_journey_visualization(journey, output_dir)
    print(f"   ✓ Generated {len(images)} visualizations")

    # Generate audio narration
    audio = await generate_audio_narration(journey, output_dir)
    if audio:
        print(f"   ✓ Generated audio narration: {audio}")

    # Generate animation (optional)
    video = None
    if include_animation:
        print("   ⏳ Generating animation (this may take a moment)...")
        video = generate_journey_animation(journey, output_dir)
        if video:
            print(f"   ✓ Generated animation: {video}")

    # Generate report
    report_path = output_dir / f"{journey_id}_report.md"
    _generate_report(journey, images, audio, video, report_path)
    print(f"   ✓ Generated report: {report_path}")

    print("\n✨ Multimodal Journey Complete!")
    print(f"   Output: {output_dir}")

    return MultimodalOutput(
        images=images,
        audio=audio,
        video=video,
        report=report_path,
    )


def _generate_report(
    journey: Journey,
    images: list[Path],
    audio: Path | None,
    video: Path | None,
    output_path: Path,
):
    """Generate Markdown report summarizing the journey."""
    report = f"""# 12D Journey Report: {journey.id}

> **P₃ = M · P₁₂** | COHEZION = 0.5 HIHO

## Summary

| Metric | Value |
|--------|-------|
| **Total Steps** | {journey.total_steps} |
| **Final Coherence** | {journey.final_coherence:.1%} |
| **Patterns** | {", ".join(journey.patterns_discovered)} |

## Visualizations

"""

    for img in images:
        report += f"![{img.stem}]({img.absolute()})\n\n"

    if audio:
        report += f"""
## Audio Narration

🎧 [Listen to narration]({audio.absolute()})
"""

    if video:
        report += f"""
## Animation

🎬 [Watch animation]({video.absolute()})
"""

    report += """
## The Journey

This 12-dimensional journey demonstrates the holographic principle in action:
- **12D Bulk**: The full state vector containing spatial, temporal, and cognitive dimensions
- **3D Boundary**: The projection we observe in physical space
- **HIHO Attractor**: The stability point at 0.5 that all dimensions converge toward
- **D1↔D12 Entanglement**: The holographic link between X and Integration

*Generated by Cohezion Morphospace Loom*
"""

    with open(output_path, "w") as f:
        f.write(report)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    output = asyncio.run(
        generate_multimodal_journey(
            n_steps=100,
            output_dir=Path("renders/journeys"),
            include_animation=True,
        )
    )

    print("\n📁 Generated files:")
    for img in output.images:
        print(f"   📊 {img}")
    if output.audio:
        print(f"   🎧 {output.audio}")
    if output.video:
        print(f"   🎬 {output.video}")
    if output.report:
        print(f"   📄 {output.report}")
