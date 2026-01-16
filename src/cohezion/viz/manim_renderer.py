"""
Manim Renderer - 3D animated visualization of the Universe Simulation.

Uses Manim to render universe nodes as particles in 3D space,
with physics-based interactions and smooth animations.

The 12D physics state is projected to 3D for visualization:
- Position (x, y, z): Spatial coordinates
- Size: Based on mass
- Color: Based on sentiment + complexity
- Opacity: Based on factuality
- Glow: Based on novelty
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RenderConfig:
    """Configuration for Manim rendering."""
    output_dir: Path = Path("renders")
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30
    quality: str = "medium"  # low, medium, high
    background_color: str = "#0a0a1a"  # Dark space blue
    
    def to_manim_config(self) -> dict[str, Any]:
        return {
            "pixel_width": self.resolution[0],
            "pixel_height": self.resolution[1],
            "frame_rate": self.fps,
            "quality": self.quality,
            "background_color": self.background_color,
        }


class ManimRenderer:
    """
    Render universe nodes as 3D Manim animations.
    
    Projects 12D physics state to visual parameters:
    - x, y, z → 3D position
    - mass → sphere size
    - sentiment → color hue (red-green)
    - complexity → color saturation
    - factuality → opacity
    - novelty → glow intensity
    - connectivity → connection lines
    """
    
    def __init__(self, config: RenderConfig | None = None):
        self.config = config or RenderConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._manim_available = False
        self._check_manim()
    
    def _check_manim(self) -> None:
        """Check if Manim is available."""
        try:
            import manim
            self._manim_available = True
            logger.info("Manim is available")
        except ImportError:
            logger.warning(
                "Manim not installed. "
                "Install with: pip install manim"
            )
    
    def physics_to_visual(
        self,
        physics_state: dict[str, float],
    ) -> dict[str, Any]:
        """
        Convert 12D physics state to visual parameters.
        
        Args:
            physics_state: Dictionary with dim_1_x through dim_12_coherence
            
        Returns:
            Visual parameters for rendering
        """
        # Extract dimensions
        x = physics_state.get("dim_1_x", 0)
        y = physics_state.get("dim_2_y", 0)
        z = physics_state.get("dim_3_z", 0)
        mass = physics_state.get("dim_5_mass", 0.5)
        sentiment = physics_state.get("dim_6_sentiment", 0)
        complexity = physics_state.get("dim_7_complexity", 0.5)
        factuality = physics_state.get("dim_8_factuality", 0.5)
        novelty = physics_state.get("dim_11_novelty", 0.5)
        
        # Map to visual parameters
        position = np.array([x * 5, y * 5, z * 5])  # Scale for visibility
        radius = 0.1 + mass * 0.4  # 0.1 to 0.5
        
        # Color: sentiment maps to hue (red=-1, green=1)
        hue = (sentiment + 1) / 2  # 0 to 1
        saturation = 0.3 + complexity * 0.7  # 0.3 to 1.0
        
        # Convert HSV to RGB
        rgb = self._hsv_to_rgb(hue, saturation, 0.9)
        
        opacity = 0.4 + factuality * 0.6  # 0.4 to 1.0
        glow = novelty  # 0 to 1
        
        return {
            "position": position,
            "radius": radius,
            "color": rgb,
            "opacity": opacity,
            "glow": glow,
        }
    
    def _hsv_to_rgb(
        self,
        h: float,
        s: float,
        v: float,
    ) -> tuple[float, float, float]:
        """Convert HSV to RGB."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (r, g, b)
    
    def render_nodes(
        self,
        nodes: list[dict[str, Any]],
        output_name: str = "universe",
        duration: float = 5.0,
    ) -> Path | None:
        """
        Render universe nodes as a 3D animation.
        
        Args:
            nodes: List of node dictionaries with physics_state
            output_name: Name for the output file
            duration: Animation duration in seconds
            
        Returns:
            Path to the rendered video, or None if failed
        """
        if not self._manim_available:
            return self._render_fallback(nodes, output_name)
        
        try:
            from manim import (
                ThreeDScene, Sphere, Line3D, config as manim_config,
                OUT, IN, UP, DOWN, LEFT, RIGHT,
                BLUE, GREEN, RED, WHITE,
            )
            
            # Configure Manim
            for key, value in self.config.to_manim_config().items():
                setattr(manim_config, key, value)
            
            # Create scene dynamically
            visual_nodes = [
                self.physics_to_visual(n.get("physics_state", {}))
                for n in nodes
            ]
            
            # For now, generate a static matplotlib visualization
            # Full Manim scene would require more complex setup
            return self._render_matplotlib_3d(visual_nodes, output_name)
            
        except Exception as e:
            logger.error(f"Manim rendering failed: {e}")
            return self._render_fallback(nodes, output_name)
    
    def _render_matplotlib_3d(
        self,
        visual_nodes: list[dict[str, Any]],
        output_name: str,
    ) -> Path:
        """Fallback to matplotlib 3D scatter plot."""
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        
        fig = plt.figure(figsize=(12, 10), facecolor=self.config.background_color)
        ax = fig.add_subplot(111, projection='3d', facecolor=self.config.background_color)
        
        for node in visual_nodes:
            pos = node["position"]
            ax.scatter(
                pos[0], pos[1], pos[2],
                s=node["radius"] * 500,
                c=[node["color"]],
                alpha=node["opacity"],
                edgecolors='white' if node["glow"] > 0.5 else 'none',
                linewidths=1 if node["glow"] > 0.5 else 0,
            )
        
        ax.set_xlabel('X', color='white')
        ax.set_ylabel('Y', color='white')
        ax.set_zlabel('Z', color='white')
        ax.tick_params(colors='white')
        ax.set_title('Universe Simulation', color='white', fontsize=16)
        
        # Style the axes
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('gray')
        ax.yaxis.pane.set_edgecolor('gray')
        ax.zaxis.pane.set_edgecolor('gray')
        
        output_path = self.config.output_dir / f"{output_name}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        
        logger.info(f"Rendered visualization to {output_path}")
        return output_path
    
    def _render_fallback(
        self,
        nodes: list[dict[str, Any]],
        output_name: str,
    ) -> Path:
        """Fallback rendering when Manim is not available."""
        visual_nodes = [
            self.physics_to_visual(n.get("physics_state", {}))
            for n in nodes
        ]
        return self._render_matplotlib_3d(visual_nodes, output_name)
    
    def render_trajectory(
        self,
        trajectory: list[np.ndarray],
        output_name: str = "trajectory",
    ) -> Path:
        """
        Render a thought trajectory as a 3D path.
        
        Args:
            trajectory: List of vectors (will use first 3 dims)
            output_name: Output file name
            
        Returns:
            Path to rendered image
        """
        import matplotlib.pyplot as plt
        
        fig = plt.figure(figsize=(12, 10), facecolor=self.config.background_color)
        ax = fig.add_subplot(111, projection='3d', facecolor=self.config.background_color)
        
        # Extract 3D coordinates
        points = np.array([t[:3] if len(t) >= 3 else np.pad(t, (0, 3-len(t))) 
                          for t in trajectory])
        
        # Plot trajectory line
        ax.plot(
            points[:, 0], points[:, 1], points[:, 2],
            color='cyan', alpha=0.6, linewidth=2,
        )
        
        # Mark start and end
        ax.scatter(*points[0], c='green', s=100, marker='o', label='Start')
        ax.scatter(*points[-1], c='red', s=100, marker='s', label='End')
        
        # Color intermediate points by position in sequence
        colors = plt.cm.viridis(np.linspace(0, 1, len(points)))
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=colors, s=30, alpha=0.8)
        
        ax.set_xlabel('Dim 1', color='white')
        ax.set_ylabel('Dim 2', color='white')
        ax.set_zlabel('Dim 3', color='white')
        ax.tick_params(colors='white')
        ax.set_title('Thought Trajectory', color='white', fontsize=16)
        ax.legend()
        
        output_path = self.config.output_dir / f"{output_name}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        
        logger.info(f"Rendered trajectory to {output_path}")
        return output_path
