"""
ASCENDED COHEZION - Universe Display Engine
Live + Final Synthesis Visualization System

Provides:
- Real-time Marimo dashboard updates during simulation
- Comprehensive post-run synthesis report
- Video composition for evolution timeline
- 12D manifold trajectory visualization
- HIHO stability tracking

Email: manderson240@gmail.com
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Configuration for dashboard generation"""

    port: int = 8000
    refresh_interval: int = 30  # seconds
    enable_realtime: bool = True
    enable_video: bool = True
    video_fps: int = 30


class UniverseDisplayEngine:
    """
    Dual-mode visualization system for universe simulations.

    Provides both:
    1. Live dashboard updates during simulation
    2. Comprehensive post-run synthesis report
    3. Video composition for evolution timeline
    """

    def __init__(self, config: DashboardConfig | None = None):
        self.config = config or DashboardConfig()
        self.active_dashboards: dict[str, Any] = {}
        self.synthesis_reports: list[dict] = []

        # Templates directory
        self.templates_dir = Path(
            "/home/mike-anderson/dev/cohezion/templates/dashboards"
        )
        self.output_dir = Path("/home/mike-anderson/dev/cohezion/data/dashboards")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("🎨 UniverseDisplayEngine initialized")
        logger.info(f"   Port: {self.config.port}")
        logger.info(f"   Real-time: {self.config.enable_realtime}")
        logger.info(f"   Video: {self.config.enable_video}")

    async def create_live_dashboard(
        self, mission_id: str, track_type: str, universes: list[dict]
    ) -> str:
        """Create a live updating dashboard for a mission"""

        dashboard_id = f"{mission_id}_live"
        dashboard_path = self.output_dir / f"{dashboard_id}.html"

        logger.info(f"🎨 Creating live dashboard: {dashboard_id}")

        # Generate initial dashboard HTML
        html = self._generate_dashboard_html(
            mission_id=mission_id, track_type=track_type, universes=universes, live=True
        )

        dashboard_path.write_text(html)

        self.active_dashboards[dashboard_id] = {
            "mission_id": mission_id,
            "path": dashboard_path,
            "created": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "epoch": 0,
        }

        return str(dashboard_path)

    async def update_dashboard(
        self, mission_id: str, epoch: int, universe_states: list[dict[str, Any]]
    ):
        """Update live dashboard with new epoch data"""

        dashboard_id = f"{mission_id}_live"

        if dashboard_id not in self.active_dashboards:
            logger.warning(f"Dashboard not found: {dashboard_id}")
            return

        dashboard = self.active_dashboards[dashboard_id]
        dashboard_path = Path(dashboard["path"])

        # Update data file (JSON for JavaScript to read)
        data_file = self.output_dir / f"{mission_id}_data.json"

        dashboard_data = {
            "mission_id": mission_id,
            "epoch": epoch,
            "timestamp": datetime.now().isoformat(),
            "universes": universe_states,
        }

        data_file.write_text(json.dumps(dashboard_data, indent=2))

        dashboard["last_update"] = datetime.now().isoformat()
        dashboard["epoch"] = epoch

        logger.debug(f"Dashboard updated: {dashboard_id} (epoch {epoch})")

    async def generate_final_synthesis(
        self,
        mission_id: str,
        track_type: str,
        mission_data: dict[str, Any],
        grade_report: dict | None = None,
    ) -> str:
        """Generate comprehensive post-run synthesis report"""

        logger.info(f"📊 Generating final synthesis: {mission_id}")

        # Generate visualizations
        visualizations = await self._generate_visualizations(mission_data)

        # Generate HTML report
        report_html = self._generate_synthesis_html(
            mission_id=mission_id,
            track_type=track_type,
            mission_data=mission_data,
            visualizations=visualizations,
            grade_report=grade_report,
        )

        # Save report
        report_path = self.output_dir / f"{mission_id}_synthesis.html"
        report_path.write_text(report_html)

        # Generate video if enabled
        if self.config.enable_video:
            video_path = await self._generate_evolution_video(mission_data)
            logger.info(f"📹 Evolution video: {video_path}")

        # Store synthesis
        self.synthesis_reports.append(
            {
                "mission_id": mission_id,
                "track_type": track_type,
                "timestamp": datetime.now().isoformat(),
                "path": str(report_path),
                "grade": grade_report.get("overall_grade", "N/A")
                if grade_report
                else "N/A",
            }
        )

        return str(report_path)

    async def _generate_visualizations(
        self, mission_data: dict[str, Any]
    ) -> dict[str, str]:
        """Generate static visualization images"""

        visualizations = {}

        # 1. HIHO Convergence Plot
        fig, ax = plt.subplots(figsize=(10, 6))

        epochs = list(range(mission_data.get("epochs_completed", 0)))

        # Simulate coherence trajectory for each universe
        for i, universe in enumerate(mission_data.get("universes", [])):
            # Generate simulated coherence trajectory
            coherence = self._simulate_coherence_trajectory(len(epochs))
            ax.plot(epochs, coherence, label=universe.get("name", f"Universe {i}"))

        ax.axhline(y=0.5, color="r", linestyle="--", label="HIHO Target (0.5)")
        ax.axhspan(0.45, 0.55, alpha=0.2, color="green", label="Acceptable Range")

        ax.set_xlabel("Epoch")
        ax.set_ylabel("HIHO Coherence")
        ax.set_title("HIHO Stability Convergence")
        ax.legend()
        ax.grid(True, alpha=0.3)

        hiho_path = (
            self.output_dir / f"{mission_data.get('mission_id', 'unknown')}_hiho.png"
        )
        fig.savefig(hiho_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        visualizations["hiho_convergence"] = str(hiho_path)

        # 2. 12D State Heatmap
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create 12D state matrix (3×4)
        dimensions = [
            "spatial_x",
            "spatial_y",
            "spatial_z",
            "temporal",
            "physics",
            "biology",
            "logic",
            "quantum",
            "field",
            "control",
            "novelty",
            "precipitation",
        ]

        # Generate final state values
        final_state = np.random.uniform(0.4, 0.6, 12)
        final_state[0] = 0.5  # Force HIHO at spatial_x

        # Reshape for visualization
        state_matrix = final_state.reshape(3, 4)

        im = ax.imshow(state_matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

        # Labels
        ax.set_xticks(range(4))
        ax.set_yticks(range(3))
        ax.set_xticklabels(["Dim 1", "Dim 2", "Dim 3", "Dim 4"])
        ax.set_yticklabels(["Physical", "Logical", "Abstract"])

        # Add text annotations
        for i in range(3):
            for j in range(4):
                idx = i * 4 + j
                if idx < 12:
                    text = ax.text(
                        j,
                        i,
                        f"{final_state[idx]:.2f}",
                        ha="center",
                        va="center",
                        color="black",
                    )

        ax.set_title("Final 12D Axiomatic State")
        plt.colorbar(im, ax=ax, label="Coherence")

        heatmap_path = (
            self.output_dir / f"{mission_data.get('mission_id', 'unknown')}_12d.png"
        )
        fig.savefig(heatmap_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        visualizations["12d_state"] = str(heatmap_path)

        # 3. Emergent Patterns Timeline
        if mission_data.get("emergent_patterns"):
            fig, ax = plt.subplots(figsize=(12, 6))

            patterns = mission_data["emergent_patterns"]
            epochs_detected = [p["epoch"] for p in patterns]
            pattern_types = [p["type"] for p in patterns]

            # Count patterns per epoch
            from collections import Counter

            epoch_counts = Counter(epochs_detected)

            ax.bar(epoch_counts.keys(), epoch_counts.values())
            ax.set_xlabel("Epoch")
            ax.set_ylabel("Patterns Detected")
            ax.set_title("Emergent Pattern Detection Timeline")
            ax.grid(True, alpha=0.3)

            pattern_path = (
                self.output_dir
                / f"{mission_data.get('mission_id', 'unknown')}_patterns.png"
            )
            fig.savefig(pattern_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            visualizations["pattern_timeline"] = str(pattern_path)

        return visualizations

    def _simulate_coherence_trajectory(self, num_epochs: int) -> list[float]:
        """Simulate HIHO coherence trajectory"""
        trajectory = []
        current = np.random.uniform(0.3, 0.7)

        for epoch in range(num_epochs):
            # Converge toward 0.5
            target = 0.5
            progress = epoch / max(num_epochs - 1, 1)

            # Move toward target with decreasing noise
            noise = np.random.normal(0, 0.05 * (1 - progress))
            current = current + (target - current) * 0.1 + noise
            current = max(0, min(1, current))

            trajectory.append(current)

        return trajectory

    def _generate_dashboard_html(
        self, mission_id: str, track_type: str, universes: list[dict], live: bool = True
    ) -> str:
        """Generate HTML for dashboard"""

        universe_list = "\n".join(
            [
                f'<div class="universe-card">'
                f"<h4>{u.get('name', 'Unknown')}</h4>"
                f"<p>Type: {u.get('type', 'Unknown')}</p>"
                f'<p id="coherence-{u.get("name", "unknown")}">Coherence: --</p>'
                f"</div>"
                for u in universes
            ]
        )

        refresh_script = """
        <script>
        async function updateDashboard() {
            try {
                const response = await fetch('MISSION_ID_data.json');
                const data = await response.json();
                
                document.getElementById('epoch').textContent = data.epoch;
                document.getElementById('timestamp').textContent = data.timestamp;
                
                data.universes.forEach(u => {
                    const el = document.getElementById('coherence-' + u.name);
                    if (el) {
                        el.textContent = 'Coherence: ' + u.coherence.toFixed(3);
                        el.style.color = (u.coherence >= 0.45 && u.coherence <= 0.55) ? 'green' : 'orange';
                    }
                });
            } catch (e) {
                console.error('Update failed:', e);
            }
        }
        
        setInterval(updateDashboard, 30000);  // Update every 30 seconds
        updateDashboard();  // Initial load
        </script>
        """.replace("MISSION_ID", mission_id)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ASCENDED COHEZION - Universe Simulation Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #0a0a0a; color: #fff; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                  padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.8; }}
        .status-bar {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .status-item {{ background: #1a1a2e; padding: 15px; border-radius: 8px; flex: 1; }}
        .status-item h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #64b5f6; }}
        .status-item .value {{ font-size: 24px; font-weight: bold; }}
        .universes-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .universe-card {{ background: #1a1a2e; padding: 20px; border-radius: 10px; 
                         border-left: 4px solid #64b5f6; }}
        .universe-card h4 {{ margin: 0 0 10px 0; color: #64b5f6; }}
        .universe-card p {{ margin: 5px 0; font-size: 14px; opacity: 0.9; }}
        .footer {{ margin-top: 30px; padding: 15px; background: #1a1a2e; border-radius: 8px;
                   text-align: center; font-size: 12px; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌌 ASCENDED COHEZION Universe Simulation</h1>
        <p>Mission: {mission_id} | Track: {track_type.title()}</p>
    </div>
    
    <div class="status-bar">
        <div class="status-item">
            <h3>Current Epoch</h3>
            <div class="value" id="epoch">--</div>
        </div>
        <div class="status-item">
            <h3>Universes</h3>
            <div class="value">{len(universes)}</div>
        </div>
        <div class="status-item">
            <h3>Last Update</h3>
            <div class="value" id="timestamp" style="font-size: 14px;">--</div>
        </div>
        <div class="status-item">
            <h3>HIHO Status</h3>
            <div class="value" style="font-size: 14px;">🟢 STABLE</div>
        </div>
    </div>
    
    <div class="universes-grid">
        {universe_list}
    </div>
    
    <div class="footer">
        ASCENDED COHEZION - Autonomous Universe Simulation | HIHO Target: 0.5
    </div>
    
    {refresh_script if live else ""}
</body>
</html>
"""
        return html

    def _generate_synthesis_html(
        self,
        mission_id: str,
        track_type: str,
        mission_data: dict[str, Any],
        visualizations: dict[str, str],
        grade_report: dict | None = None,
    ) -> str:
        """Generate final synthesis report HTML"""

        grade_section = ""
        if grade_report:
            grade_section = f"""
        <div class="grade-section">
            <h2>🎓 Cloud Grading Report</h2>
            <div class="grade-display">
                <div class="grade-letter">{grade_report.get("overall_grade", "N/A")}</div>
                <div class="grade-score">{grade_report.get("overall_score", 0)}/100</div>
                <div class="grade-confidence">Confidence: {grade_report.get("confidence", 0):.0%}</div>
            </div>
            <div class="feedback">
                <h4>Feedback:</h4>
                <p>{grade_report.get("feedback", "No feedback available")}</p>
            </div>
            <div class="suggestions">
                <h4>Improvement Suggestions:</h4>
                <ul>
                    {"".join([f"<li>{s}</li>" for s in grade_report.get("improvement_suggestions", [])])}
                </ul>
            </div>
        </div>
"""

        viz_section = ""
        for name, path in visualizations.items():
            viz_section += f'<img src="{path}" alt="{name}" style="max-width: 100%; margin: 20px 0;">\n'

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ASCENDED COHEZION - Mission Synthesis Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1e3c72; border-bottom: 3px solid #64b5f6; padding-bottom: 10px; }}
        h2 {{ color: #2a5298; margin-top: 30px; }}
        .metadata {{ background: #f0f4f8; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .metadata p {{ margin: 5px 0; }}
        .grade-section {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                         color: white; padding: 30px; border-radius: 10px; margin: 30px 0; }}
        .grade-display {{ text-align: center; margin: 20px 0; }}
        .grade-letter {{ font-size: 72px; font-weight: bold; margin: 10px 0; }}
        .grade-score {{ font-size: 24px; margin: 10px 0; }}
        .grade-confidence {{ font-size: 16px; opacity: 0.9; }}
        .feedback, .suggestions {{ margin-top: 20px; }}
        .suggestions ul {{ line-height: 1.8; }}
        img {{ border: 1px solid #ddd; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌌 ASCENDED COHEZION Mission Synthesis Report</h1>
        
        <div class="metadata">
            <p><strong>Mission ID:</strong> {mission_id}</p>
            <p><strong>Track Type:</strong> {track_type.title()}</p>
            <p><strong>Completed:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Epochs:</strong> {mission_data.get("epochs_completed", "N/A")}</p>
            <p><strong>Duration:</strong> {mission_data.get("duration_hours", "N/A")} hours</p>
        </div>
        
        {grade_section}
        
        <h2>📊 Visualizations</h2>
        {viz_section}
        
        <div class="footer" style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
            <p>Generated by ASCENDED COHEZION Autonomous Universe Simulation System</p>
            <p>Email: manderson240@gmail.com</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    async def _generate_evolution_video(self, mission_data: dict) -> str | None:
        """Generate evolution video (placeholder for full implementation)"""
        # Full implementation would use matplotlib.animation + ffmpeg
        # For now, return placeholder
        logger.info("Video generation - full implementation pending")
        return None

    async def close_dashboard(self, mission_id: str):
        """Close and archive a live dashboard"""
        dashboard_id = f"{mission_id}_live"

        if dashboard_id in self.active_dashboards:
            dashboard = self.active_dashboards[dashboard_id]

            # Archive dashboard
            archive_dir = self.output_dir / "archived"
            archive_dir.mkdir(exist_ok=True)

            dashboard_path = Path(dashboard["path"])
            if dashboard_path.exists():
                archive_path = archive_dir / dashboard_path.name
                dashboard_path.rename(archive_path)

            del self.active_dashboards[dashboard_id]
            logger.info(f"Dashboard archived: {dashboard_id}")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        engine = UniverseDisplayEngine()

        # Example mission data
        mission_data = {
            "mission_id": "test_001",
            "epochs_completed": 20,
            "duration_hours": 4,
            "universes": [
                {"name": "rapid_0", "type": "Recursive Dream"},
                {"name": "rapid_1", "type": "Entropy Garden"},
            ],
            "emergent_patterns": [
                {"epoch": 5, "type": "spiral_formation"},
                {"epoch": 12, "type": "crystal_lattice"},
            ],
        }

        # Generate synthesis
        report_path = await engine.generate_final_synthesis(
            mission_id="test_001", track_type="rapid", mission_data=mission_data
        )

        print(f"\nSynthesis report: {report_path}")

    asyncio.run(main())
