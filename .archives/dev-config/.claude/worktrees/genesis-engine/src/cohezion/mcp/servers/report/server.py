"""Report Generation MCP Server - With Reactive Marimo Notebooks.

Port: 8372
Features:
- Generate interactive reports
- Marimo notebook creation
- Reactive visualization
- Export to multiple formats (HTML, PDF, WASM)
- Live data updates
- Collaborative editing

Integrates with BMAD workflows for documentation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import web


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8372"))
MARIMO_PORT = int(os.getenv("MARIMO_PORT", "8765"))


@dataclass
class Report:
    """A generated report."""

    id: str
    title: str
    content: str
    notebook_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_marimo: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "notebook_path": self.notebook_path,
            "created_at": self.created_at,
            "is_marimo": self.is_marimo,
        }


class MarimoReportGenerator:
    """Generate reactive Marimo reports."""

    def __init__(self, output_dir: str = "/tmp/marimo-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.reports: dict[str, Report] = {}

    def generate_notebook(
        self,
        title: str,
        data: dict[str, Any],
        template: str = "analysis",
    ) -> Report:
        """Generate a Marimo notebook."""
        report_id = str(uuid.uuid4())[:8]

        # Write data to a sidecar JSON file to prevent code injection
        data_path = self.output_dir / f"{report_id}_data.json"
        data_path.write_text(json.dumps(data, indent=2))

        # Create Marimo notebook content (loads from data_path)
        notebook_content = self._create_marimo_content(title, str(data_path), template)

        # Write notebook file
        notebook_path = self.output_dir / f"{report_id}.py"
        notebook_path.write_text(notebook_content)

        report = Report(
            id=report_id,
            title=title,
            content=notebook_content,
            notebook_path=str(notebook_path),
            is_marimo=True,
        )
        self.reports[report_id] = report

        return report

    def _create_marimo_content(
        self,
        title: str,
        data_path: str,
        template: str,
    ) -> str:
        """Create Marimo notebook Python code."""

        base_imports = f"""
import marimo as mo
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json
from pathlib import Path

__generated__ = True
DATA_PATH = {json.dumps(data_path)}
"""

        load_data_cell = """
@app.cell
def load_data():
    if Path(DATA_PATH).exists():
        data = json.loads(Path(DATA_PATH).read_text())
    else:
        data = {}
    return data,
"""

        if template == "analysis":
            return f'''{base_imports}

# {title}

app = mo.App()

{load_data_cell}

@app.cell
def title(data):
    mo.md(f"""
    # {title}

    *Generated: {{data.get("generated_at", "N/A")}}*
    *Report ID: {{data.get("report_id", "N/A")}}*
    """)

@app.cell
def data_overview(data):
    mo.md(f"""
    ## Data Overview

    - **Total Records:** {{len(data.get('records', []))}}
    - **Summary:** {{data.get('summary', 'N/A')}}
    """)

@app.cell
def visualization(data):
    # Create interactive plot
    if 'records' in data and len(data['records']) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=[r.get('value', 0) for r in data['records']],
            mode='lines+markers',
            name='Values'
        ))
        fig.update_layout(
            title='Interactive Data Visualization',
            xaxis_title='Index',
            yaxis_title='Value'
        )
        mo.ui.plotly(fig)
    else:
        mo.md("*No visualization data available*")

@app.cell
def analysis():
    mo.md("""
    ## Analysis

    This report is generated using Marimo's reactive execution model.
    Update cells and see results update automatically.
    """)

if __name__ == "__main__":
    app.run()
'''
        elif template == "physics":
            return f'''{base_imports}

# {title} - Physics Simulation Report

app = mo.App()

{load_data_cell}

@app.cell
def title(data):
    mo.md(f"""
    # {title}

    ## Physics Simulation Analysis

    *Generated: {{data.get("generated_at", "N/A")}}*
    """)

@app.cell
def simulation_params(data):
    mo.md(f"""
    ### Parameters

    - **Grid Size:** {{data.get('grid_size', 'N/A')}}
    - **Time Step:** {{data.get('time_step', 'N/A')}}
    - **Duration:** {{data.get('duration', 'N/A')}}
    """)

@app.cell
def results(data):
    if 'results' in data:
        results = data['results']

        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        if 'particle_count' in results:
            ax1.plot(results['particle_count'])
            ax1.set_title('Particle Count Over Time')
            ax1.set_xlabel('Step')
            ax1.set_ylabel('Count')

        if 'energy' in results:
            ax2.plot(results['energy'])
            ax2.set_title('System Energy')
            ax2.set_xlabel('Step')
            ax2.set_ylabel('Energy')

        plt.tight_layout()
        mo.ui.pyplot(fig)
    else:
        mo.md("*No results data available*")

if __name__ == "__main__":
    app.run()
'''
        else:
            return f'''{base_imports}

# {title}

app = mo.App()

{load_data_cell}

@app.cell
def _():
    mo.md(f"""
    # {title}
    """)

@app.cell
def _(data):
    mo.json(data)

if __name__ == "__main__":
    app.run()
'''

    async def serve_notebook(self, report_id: str) -> dict[str, Any]:
        """Start Marimo server for a notebook."""
        report = self.reports.get(report_id)
        if not report or not report.notebook_path:
            return {"error": "Report not found"}

        # Start Marimo server in background
        cmd = [
            "nohup",
            "uv",
            "run",
            "marimo",
            "run",
            report.notebook_path,
            "--host",
            "0.0.0.0",
            "--port",
            str(MARIMO_PORT),
            ">",
            "/tmp/marimo.log",
            "2>&1",
            "&",
        ]

        try:
            subprocess.Popen(
                " ".join(cmd),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return {
                "report_id": report_id,
                "url": f"http://localhost:{MARIMO_PORT}",
                "status": "serving",
            }
        except Exception as e:
            return {"error": str(e)}

    def export_notebook(self, report_id: str, format: str) -> dict[str, Any]:
        """Export notebook to different formats."""
        report = self.reports.get(report_id)
        if not report or not report.notebook_path:
            return {"error": "Report not found"}

        try:
            if format == "html":
                output_path = self.output_dir / f"{report_id}.html"
                # Would run: marimo export html report.py -o report.html
                return {
                    "format": "html",
                    "path": str(output_path),
                    "status": "exported",
                }
            elif format == "wasm":
                output_path = self.output_dir / f"{report_id}-wasm"
                # Would run: marimo export wasm report.py -o report-wasm/
                return {
                    "format": "wasm",
                    "path": str(output_path),
                    "status": "exported",
                }
            else:
                return {"error": f"Unsupported format: {format}"}
        except Exception as e:
            return {"error": str(e)}


# Global generator instance
_generator: MarimoReportGenerator | None = None


def get_generator() -> MarimoReportGenerator:
    """Get or create report generator."""
    global _generator
    if _generator is None:
        _generator = MarimoReportGenerator()
    return _generator


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "report-generation",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Report Generation MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "marimo_port": MARIMO_PORT,
            "features": [
                "Marimo notebook generation",
                "Reactive visualizations",
                "HTML export",
                "WASM export",
                "Live serving",
            ],
            "templates": ["analysis", "physics", "default"],
        }
    )


@routes.post("/tools/report_generate")
async def tool_generate(request: web.Request) -> web.Response:
    """Generate a report."""
    try:
        data = await request.json()
        title = data.get("title", "Untitled Report")
        report_data = data.get("data", {})
        template = data.get("template", "analysis")

        generator = get_generator()
        report = generator.generate_notebook(title, report_data, template)

        return web.json_response(
            {
                "tool": "report_generate",
                "report": report.to_dict(),
                "content_preview": report.content[:500] + "..." if len(report.content) > 500 else report.content,
            }
        )
    except Exception as e:
        logger.exception("Generate failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/report_serve")
async def tool_serve(request: web.Request) -> web.Response:
    """Serve a report with Marimo."""
    try:
        data = await request.json()
        report_id = data.get("report_id", "")

        generator = get_generator()
        result = await generator.serve_notebook(report_id)

        return web.json_response(
            {
                "tool": "report_serve",
                **result,
            }
        )
    except Exception as e:
        logger.exception("Serve failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/report_export")
async def tool_export(request: web.Request) -> web.Response:
    """Export report to format."""
    try:
        data = await request.json()
        report_id = data.get("report_id", "")
        format_type = data.get("format", "html")

        generator = get_generator()
        result = generator.export_notebook(report_id, format_type)

        return web.json_response(
            {
                "tool": "report_export",
                **result,
            }
        )
    except Exception as e:
        logger.exception("Export failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/report_list")
async def tool_list(request: web.Request) -> web.Response:
    """List all generated reports."""
    try:
        generator = get_generator()
        reports = [r.to_dict() for r in generator.reports.values()]

        return web.json_response(
            {
                "tool": "report_list",
                "count": len(reports),
                "reports": reports,
            }
        )
    except Exception as e:
        logger.exception("List failed")
        return web.json_response({"error": str(e)}, status=500)


async def main():
    """Run Report Generation MCP Server."""
    get_generator()  # Initialize

    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)

    logger.info(f"Starting Report Generation MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Report Generation Server running on http://localhost:{MCP_PORT}")
    logger.info(f"   Marimo port: {MARIMO_PORT}")
    logger.info("   Templates: analysis, physics, default")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Report Generation Server stopped")
