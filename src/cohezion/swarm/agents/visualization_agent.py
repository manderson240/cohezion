"""
Visualization Agent - Multimodal output generation for simulations.

This agent specializes in creating rich visual representations of 
FLUME trajectories and universe simulations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VisualizationRequest:
    """Request for visualization generation."""
    data_path: Path
    output_dir: Path
    format: str = "png"  # png, svg, html, mp4
    style: str = "publication"  # publication, presentation, web
    include_audio: bool = False
    include_animation: bool = False


@dataclass
class VisualizationResult:
    """Result of visualization generation."""
    images: list[Path] = field(default_factory=list)
    audio: Path | None = None
    video: Path | None = None
    html: Path | None = None
    metadata: dict = field(default_factory=dict)


class VisualizationAgent:
    """
    Agent for generating multimodal visualizations from simulation data.
    
    Capabilities:
    - Static plots (matplotlib, plotly)
    - Animated visualizations (matplotlib.animation)
    - Audio narration (edge-tts)
    - Video composition (ffmpeg)
    - Interactive dashboards (marimo export)
    """
    
    def __init__(self, output_base: Path = Path("renders")):
        self.output_base = output_base
        self.output_base.mkdir(parents=True, exist_ok=True)
        
    async def generate(self, request: VisualizationRequest) -> VisualizationResult:
        """Generate multimodal visualization from request."""
        logger.info(f"Generating visualization for {request.data_path}")
        
        # Load data
        data = self._load_data(request.data_path)
        
        result = VisualizationResult()
        result.metadata = {
            "source": str(request.data_path),
            "records": len(data),
            "style": request.style
        }
        
        # Generate static plots
        result.images = await self._generate_plots(data, request)
        
        # Generate audio if requested
        if request.include_audio:
            result.audio = await self._generate_audio(data, request)
            
        # Generate animation if requested
        if request.include_animation:
            result.video = await self._generate_animation(data, request)
            
        logger.info(f"Visualization complete: {len(result.images)} images")
        return result
    
    def _load_data(self, path: Path) -> list[dict]:
        """Load JSONL trajectory data."""
        data = []
        with open(path, 'r') as f:
            for line in f:
                data.append(json.loads(line))
        return data
    
    async def _generate_plots(self, data: list[dict], request: VisualizationRequest) -> list[Path]:
        """Generate static visualization plots."""
        import pandas as pd
        df = pd.DataFrame(data)
        
        plots = []
        output_dir = request.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set style
        if request.style == "publication":
            plt.style.use('seaborn-v0_8-whitegrid')
        elif request.style == "presentation":
            plt.style.use('dark_background')
        
        # Plot 1: Coherence by Stream
        fig, ax = plt.subplots(figsize=(10, 6))
        for stream in df['stream'].unique():
            stream_data = df[df['stream'] == stream]
            ax.plot(stream_data['step'], stream_data['coherence'], 
                   label=stream, alpha=0.7, linewidth=2)
        ax.axhline(y=0.7, color='r', linestyle='--', label='Threshold')
        ax.set_xlabel('Simulation Step', fontsize=12)
        ax.set_ylabel('Coherence', fontsize=12)
        ax.set_title('FLUME Trajectory Coherence by Expert Domain', fontsize=14)
        ax.legend(loc='lower right')
        
        plot_path = output_dir / f"coherence_by_stream.{request.format}"
        plt.savefig(plot_path, dpi=300 if request.style == "publication" else 150, 
                   bbox_inches='tight')
        plt.close()
        plots.append(plot_path)
        
        # Plot 2: Stream Distribution
        fig, ax = plt.subplots(figsize=(8, 8))
        stream_counts = df['stream'].value_counts()
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        ax.pie(stream_counts.values, labels=stream_counts.index, 
               autopct='%1.1f%%', colors=colors[:len(stream_counts)])
        ax.set_title('Trajectory Distribution by Expert Domain', fontsize=14)
        
        plot_path = output_dir / f"stream_distribution.{request.format}"
        plt.savefig(plot_path, dpi=300 if request.style == "publication" else 150, 
                   bbox_inches='tight')
        plt.close()
        plots.append(plot_path)
        
        # Plot 3: Status Heatmap
        fig, ax = plt.subplots(figsize=(10, 6))
        status_by_stream = df.groupby(['stream', 'status']).size().unstack(fill_value=0)
        status_by_stream.plot(kind='bar', stacked=True, ax=ax, 
                              color=['#E74C3C', '#2ECC71'])
        ax.set_xlabel('Expert Stream', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Trajectory Outcomes by Domain', fontsize=14)
        ax.legend(title='Status')
        plt.xticks(rotation=45)
        
        plot_path = output_dir / f"trajectory_outcomes.{request.format}"
        plt.savefig(plot_path, dpi=300 if request.style == "publication" else 150, 
                   bbox_inches='tight')
        plt.close()
        plots.append(plot_path)
        
        return plots
    
    async def _generate_audio(self, data: list[dict], request: VisualizationRequest) -> Path | None:
        """Generate audio narration of results."""
        import subprocess
        import pandas as pd
        
        df = pd.DataFrame(data)
        
        # Generate summary text
        summary = f"""
        The FLUME simulation completed {len(df)} trajectories across {df['stream'].nunique()} expert domains.
        The average coherence score was {df['coherence'].mean():.2f}.
        {(df['status'] == 'survived').sum()} trajectories survived above the threshold.
        The {df.groupby('stream')['coherence'].mean().idxmax()} stream achieved the highest average coherence.
        """
        
        output_path = request.output_dir / "narration.mp3"
        
        try:
            # Use edge-tts if available
            cmd = [
                "edge-tts",
                "--voice", "en-US-AriaNeural",
                "--text", summary.strip(),
                "--write-media", str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            logger.info(f"Generated audio narration: {output_path}")
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Audio generation failed: {e}")
            return None
    
    async def _generate_animation(self, data: list[dict], request: VisualizationRequest) -> Path | None:
        """Generate animated visualization."""
        import matplotlib.animation as animation
        import pandas as pd
        
        df = pd.DataFrame(data)
        output_path = request.output_dir / "trajectory_animation.mp4"
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            def animate(frame):
                ax.clear()
                frame_data = df[df['step'] <= frame]
                for stream in df['stream'].unique():
                    stream_data = frame_data[frame_data['stream'] == stream]
                    ax.plot(stream_data['step'], stream_data['coherence'], 
                           label=stream, alpha=0.7, linewidth=2)
                ax.axhline(y=0.7, color='r', linestyle='--', alpha=0.5)
                ax.set_xlim(0, df['step'].max())
                ax.set_ylim(0, 1)
                ax.set_xlabel('Step')
                ax.set_ylabel('Coherence')
                ax.set_title(f'FLUME Trajectory Evolution (Step {frame})')
                ax.legend(loc='lower right')
            
            max_step = df['step'].max()
            ani = animation.FuncAnimation(fig, animate, frames=range(0, max_step, 5),
                                         interval=100, blit=False)
            ani.save(str(output_path), writer='ffmpeg', fps=10)
            plt.close()
            
            logger.info(f"Generated animation: {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Animation generation failed: {e}")
            return None


async def main():
    """Demo of visualization agent."""
    agent = VisualizationAgent()
    
    request = VisualizationRequest(
        data_path=Path("src/cohezion/knowledge_graph/universe_nodes/flume_trajectories.jsonl"),
        output_dir=Path("renders/demo"),
        format="png",
        style="publication",
        include_audio=False,
        include_animation=False
    )
    
    result = await agent.generate(request)
    print(f"Generated {len(result.images)} visualizations")
    for img in result.images:
        print(f"  - {img}")


if __name__ == "__main__":
    asyncio.run(main())
