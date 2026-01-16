"""
HyperTools Renderer - Interactive high-dimensional data visualization.

HyperTools provides dimensionality reduction visualization using
UMAP, t-SNE, and PCA to project high-dimensional embeddings to
2D/3D for exploration.

Features:
- Interactive embedding exploration
- Animated trajectory visualization
- Cluster coloring and labeling
- Multiple projection methods
"""

import logging
from pathlib import Path
from typing import Any, Literal

import numpy as np

logger = logging.getLogger(__name__)


ProjectionMethod = Literal["umap", "tsne", "pca"]


class HyperToolsViz:
    """
    High-dimensional data visualization using HyperTools.
    
    Provides interactive exploration of embeddings and
    animated visualization of thought trajectories.
    """
    
    def __init__(
        self,
        output_dir: Path | str = Path("renders"),
        default_method: ProjectionMethod = "umap",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_method = default_method
        self._hypertools_available = False
        self._check_hypertools()
    
    def _check_hypertools(self) -> None:
        """Check if HyperTools is available."""
        try:
            import hypertools as hyp
            self._hypertools_available = True
            logger.info("HyperTools is available")
        except ImportError:
            logger.warning(
                "HyperTools not installed. "
                "Install with: pip install hypertools"
            )
    
    def plot_embeddings(
        self,
        embeddings: np.ndarray | list[np.ndarray],
        labels: list[str] | None = None,
        colors: list[str] | None = None,
        method: ProjectionMethod | None = None,
        output_name: str = "embeddings",
        interactive: bool = False,
    ) -> Path:
        """
        Visualize high-dimensional embeddings.
        
        Args:
            embeddings: (n_samples, n_features) array or list of arrays
            labels: Optional labels for each sample
            colors: Optional colors for each sample
            method: Dimensionality reduction method
            output_name: Output file name
            interactive: Whether to show interactive plot
            
        Returns:
            Path to saved visualization
        """
        method = method or self.default_method
        
        if isinstance(embeddings, list):
            embeddings = np.vstack(embeddings)
        
        if self._hypertools_available:
            return self._plot_hypertools(
                embeddings, labels, colors, method, output_name, interactive
            )
        else:
            return self._plot_fallback(
                embeddings, labels, colors, method, output_name
            )
    
    def _plot_hypertools(
        self,
        embeddings: np.ndarray,
        labels: list[str] | None,
        colors: list[str] | None,
        method: ProjectionMethod,
        output_name: str,
        interactive: bool,
    ) -> Path:
        """Plot using HyperTools."""
        try:
            import hypertools as hyp
            import matplotlib.pyplot as plt
            
            # Project to 3D
            geo = hyp.plot(
                embeddings,
                reduce=method,
                ndims=3,
                labels=labels,
                show=interactive,
                save_path=None,  # We'll save manually
            )
            
            output_path = self.output_dir / f"{output_name}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            if not interactive:
                plt.close()
            
            logger.info(f"Saved HyperTools plot to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"HyperTools plotting failed: {e}")
            return self._plot_fallback(
                embeddings, labels, colors, method, output_name
            )
    
    def _plot_fallback(
        self,
        embeddings: np.ndarray,
        labels: list[str] | None,
        colors: list[str] | None,
        method: ProjectionMethod,
        output_name: str,
    ) -> Path:
        """Fallback plotting using sklearn + matplotlib."""
        import matplotlib.pyplot as plt
        
        # Reduce to 3D
        reduced = self._reduce_dimensions(embeddings, 3, method)
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Color by index if not specified
        if colors is None:
            colors = plt.cm.viridis(np.linspace(0, 1, len(embeddings)))
        
        scatter = ax.scatter(
            reduced[:, 0], reduced[:, 1], reduced[:, 2],
            c=range(len(embeddings)) if colors is None else colors,
            cmap='viridis',
            s=50,
            alpha=0.7,
        )
        
        # Add labels if provided
        if labels:
            for i, label in enumerate(labels[:20]):  # Limit to avoid clutter
                ax.text(reduced[i, 0], reduced[i, 1], reduced[i, 2], 
                       label[:20], fontsize=8)
        
        ax.set_xlabel('Dimension 1')
        ax.set_ylabel('Dimension 2')
        ax.set_zlabel('Dimension 3')
        ax.set_title(f'Embeddings Visualization ({method.upper()})')
        
        output_path = self.output_dir / f"{output_name}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved fallback plot to {output_path}")
        return output_path
    
    def _reduce_dimensions(
        self,
        data: np.ndarray,
        n_dims: int,
        method: ProjectionMethod,
    ) -> np.ndarray:
        """Reduce dimensionality using specified method."""
        if data.shape[1] <= n_dims:
            # Pad if needed
            padding = np.zeros((data.shape[0], n_dims - data.shape[1]))
            return np.hstack([data, padding])
        
        if method == "pca":
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=n_dims)
        elif method == "tsne":
            from sklearn.manifold import TSNE
            reducer = TSNE(n_components=n_dims, random_state=42)
        elif method == "umap":
            try:
                from umap import UMAP
                reducer = UMAP(n_components=n_dims, random_state=42)
            except ImportError:
                logger.warning("UMAP not available, falling back to PCA")
                from sklearn.decomposition import PCA
                reducer = PCA(n_components=n_dims)
        else:
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=n_dims)
        
        return reducer.fit_transform(data)
    
    def animate_trajectory(
        self,
        trajectory: list[np.ndarray] | np.ndarray,
        output_name: str = "trajectory_animation",
        fps: int = 10,
    ) -> Path:
        """
        Create an animated visualization of a trajectory.
        
        Args:
            trajectory: Sequence of vectors
            output_name: Output file name
            fps: Frames per second
            
        Returns:
            Path to saved animation (GIF)
        """
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation, PillowWriter
        
        if isinstance(trajectory, list):
            trajectory = np.array(trajectory)
        
        # Reduce to 3D if needed
        if trajectory.shape[1] > 3:
            trajectory = self._reduce_dimensions(trajectory, 3, "pca")
        elif trajectory.shape[1] < 3:
            padding = np.zeros((trajectory.shape[0], 3 - trajectory.shape[1]))
            trajectory = np.hstack([trajectory, padding])
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Initialize elements
        line, = ax.plot([], [], [], 'b-', alpha=0.6, linewidth=2)
        point, = ax.plot([], [], [], 'ro', markersize=10)
        trail, = ax.plot([], [], [], 'c.', alpha=0.3, markersize=3)
        
        # Set axis limits
        margin = 0.1
        for i, setter in enumerate([ax.set_xlim, ax.set_ylim, ax.set_zlim]):
            min_val, max_val = trajectory[:, i].min(), trajectory[:, i].max()
            range_val = max_val - min_val
            setter(min_val - margin * range_val, max_val + margin * range_val)
        
        ax.set_xlabel('Dim 1')
        ax.set_ylabel('Dim 2')
        ax.set_zlabel('Dim 3')
        ax.set_title('Thought Trajectory Animation')
        
        def init():
            line.set_data([], [])
            line.set_3d_properties([])
            point.set_data([], [])
            point.set_3d_properties([])
            trail.set_data([], [])
            trail.set_3d_properties([])
            return line, point, trail
        
        def update(frame):
            idx = frame + 1
            # Line up to current point
            line.set_data(trajectory[:idx, 0], trajectory[:idx, 1])
            line.set_3d_properties(trajectory[:idx, 2])
            # Current point
            point.set_data([trajectory[frame, 0]], [trajectory[frame, 1]])
            point.set_3d_properties([trajectory[frame, 2]])
            # Trail
            trail.set_data(trajectory[:idx, 0], trajectory[:idx, 1])
            trail.set_3d_properties(trajectory[:idx, 2])
            return line, point, trail
        
        anim = FuncAnimation(
            fig, update, init_func=init,
            frames=len(trajectory), interval=1000//fps, blit=True
        )
        
        output_path = self.output_dir / f"{output_name}.gif"
        anim.save(output_path, writer=PillowWriter(fps=fps))
        plt.close()
        
        logger.info(f"Saved trajectory animation to {output_path}")
        return output_path
    
    def compare_embeddings(
        self,
        embedding_sets: list[np.ndarray],
        set_labels: list[str],
        method: ProjectionMethod | None = None,
        output_name: str = "embedding_comparison",
    ) -> Path:
        """
        Compare multiple sets of embeddings.
        
        Args:
            embedding_sets: List of embedding arrays
            set_labels: Labels for each set
            method: Reduction method
            output_name: Output file name
            
        Returns:
            Path to saved visualization
        """
        import matplotlib.pyplot as plt
        
        method = method or self.default_method
        
        # Combine all embeddings for joint projection
        combined = np.vstack(embedding_sets)
        reduced = self._reduce_dimensions(combined, 3, method)
        
        # Split back
        indices = np.cumsum([0] + [len(e) for e in embedding_sets])
        reduced_sets = [
            reduced[indices[i]:indices[i+1]]
            for i in range(len(embedding_sets))
        ]
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(embedding_sets)))
        
        for i, (reduced_set, label) in enumerate(zip(reduced_sets, set_labels)):
            ax.scatter(
                reduced_set[:, 0], reduced_set[:, 1], reduced_set[:, 2],
                c=[colors[i]], label=label, s=50, alpha=0.7,
            )
        
        ax.set_xlabel('Dimension 1')
        ax.set_ylabel('Dimension 2')
        ax.set_zlabel('Dimension 3')
        ax.set_title(f'Embedding Comparison ({method.upper()})')
        ax.legend()
        
        output_path = self.output_dir / f"{output_name}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved comparison plot to {output_path}")
        return output_path
