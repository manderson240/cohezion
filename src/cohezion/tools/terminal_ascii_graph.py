r"""Terminal ASCII & Unicode Graph / Flowchart Renderer.
======================================================
Renders Mermaid-like flowchart graphs, V-Models, and DAGs directly in terminal
using Unicode Box-Drawing characters, ANSI colors, and Rich Layout panels.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree


class TerminalAsciiGraph:
    """Renders structured diagrams in CLI / Terminal environments."""

    def __init__(self) -> None:
        self.console = Console(force_terminal=True, color_system="truecolor")

    def render_v_model_flowchart(self) -> None:
        """Render the Systems Engineering V-Model Flowchart with Unicode Box-Drawing."""
        diagram = r"""
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                    SYSTEMS ENGINEERING V-MODEL RIGOR & COMPOUND LOOP                             │
  └──────────────────────────────────┬───────────────────────────────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       ▼
  ┌──────────────┴─────────────────────────┐   ┌─────────────────────────────────────────┐
  │ 1. SYSTEM ARCHITECTURE (Top-Left)      │   │ 3. VERIFICATION & VELOCITY (Top-Right)  │
  │ ├─ FLUME 12D Poincaré Metric           │   │ ├─ Write Budget Throttling Governor     │
  │ │  └─ Levi-Civita Geodesic Flow ODE    │   │ ├─ OpenZFS Zero-Copy Snapshot Manager   │
  │ └─ Matsumoto ENC Debye Screening       │   │ ├─ Google Workspace Alert Gateway       │
  │    └─ Burkhard Heim Metron Tiling      │   │ └─ 100% Deterministic Empirical Proofs  │
  └──────────────────────┬─────────────────┘   └───────────────────▲─────────────────────┘
                         │                                         │
                         │             DOMAIN DATAMESH             │
                         └───────────────────►◄────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │ 2. EVENT-DRIVEN TOPOLOGY (Bottom-V)       │
                       │ ├─ EventBus Pub/Sub & Inter-Session Bridge│
                       │ ├─ Dual-Sink Write-Through (Surreal+Vault)│
                       │ ├─ AMD GAIA SDK Native Tool Mixins        │
                       │ └─ AutoHarness Zero-Cost AST Gatekeeper   │
                       └───────────────────────────────────────────┘
        """
        panel = Panel(
            Text(diagram, style="bold cyan"),
            title="[bold green]Cohezion Sovereign V-Model Topology[/bold green]",
            border_style="bright_blue",
            expand=False,
        )
        self.console.print(panel)

    def render_tree_dag(self, title: str, nodes: dict) -> None:
        """Render a dynamic hierarchy tree in terminal."""
        tree = Tree(f"[bold gold1]{title}[/bold gold1]")
        self._build_subtrees(tree, nodes)
        self.console.print(tree)

    def _build_subtrees(self, parent_tree: Tree, node_dict: dict) -> None:
        for k, v in node_dict.items():
            if isinstance(v, dict):
                sub = parent_tree.add(f"[bold cyan]{k}[/bold cyan]")
                self._build_subtrees(sub, v)
            elif isinstance(v, list):
                sub = parent_tree.add(f"[bold cyan]{k}[/bold cyan]")
                for item in v:
                    sub.add(f"[green]{item}[/green]")
            else:
                parent_tree.add(f"[bold cyan]{k}[/bold cyan]: [white]{v}[/white]")


def render_v_model_cli() -> None:
    renderer = TerminalAsciiGraph()
    renderer.render_v_model_flowchart()


if __name__ == "__main__":
    render_v_model_cli()
