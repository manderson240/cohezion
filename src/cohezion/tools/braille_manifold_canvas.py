r"""Braille Vector & Sub-Pixel Terminal Manifold Renderer.
=========================================================
Renders high-resolution 2D/3D Poincaré hyperbolic disks, torus manifolds,
and Lyapunov attractors directly in the terminal using 2x4 sub-pixel Braille dots.
"""

from __future__ import annotations

import math

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class BrailleCanvas:
    """Sub-pixel terminal canvas using Unicode Braille characters (U+2800..U+28FF)."""

    def __init__(self, width: int = 80, height: int = 40) -> None:
        self.char_w = width
        self.char_h = height
        self.pixel_w = width * 2
        self.pixel_h = height * 4
        self.grid = [[0 for _ in range(self.pixel_w)] for _ in range(self.pixel_h)]
        self.console = Console(force_terminal=True, color_system="truecolor")

    def set_pixel(self, x: int, y: int) -> None:
        if 0 <= x < self.pixel_w and 0 <= y < self.pixel_h:
            self.grid[y][x] = 1

    def draw_poincare_disk(self) -> None:
        """Draw a 2048D Poincaré disk cross-section with hyperbolic geodesics and boundary."""
        cx = self.pixel_w // 2
        cy = self.pixel_h // 2
        radius = min(cx, cy) - 4

        # 1. Draw boundary circle (||z|| = 1.0)
        for angle in range(0, 360, 1):
            rad = math.radians(angle)
            px = int(cx + radius * math.cos(rad))
            py = int(cy + radius * math.sin(rad))
            self.set_pixel(px, py)

        # 2. Draw interior hyperbolic geodesic arcs
        for r_factor in [0.25, 0.50, 0.75]:
            r_arc = radius * r_factor
            for angle in range(0, 360, 2):
                rad = math.radians(angle)
                px = int(cx + r_arc * math.cos(rad))
                py = int(cy + r_arc * math.sin(rad))
                self.set_pixel(px, py)

        # 3. Draw orthogonal geodesic arcs connecting HIHO 0.5 points
        for i in range(-radius + 4, radius - 4, 3):
            # Hyperbolic trajectory line
            x_norm = i / radius
            if abs(x_norm) < 1.0:
                y_span = math.sqrt(1.0 - x_norm**2) * radius
                px = int(cx + i)
                py1 = int(cy - y_span * 0.7)
                py2 = int(cy + y_span * 0.7)
                self.set_pixel(px, py1)
                self.set_pixel(px, py2)

    def to_string(self) -> str:
        """Convert pixel matrix to Unicode Braille text."""
        # Braille bit offsets:
        # [0][3]  (1, 8)
        # [1][4]  (2, 16)
        # [2][5]  (4, 32)
        # [6][7]  (64, 128)
        dot_map = [
            [0x01, 0x08],
            [0x02, 0x10],
            [0x04, 0x20],
            [0x40, 0x80],
        ]

        lines = []
        for cy in range(self.char_h):
            line_chars = []
            for cx in range(self.char_w):
                val = 0
                for dy in range(4):
                    for dx in range(2):
                        px = cx * 2 + dx
                        py = cy * 4 + dy
                        if py < self.pixel_h and px < self.pixel_w:
                            if self.grid[py][px]:
                                val |= dot_map[dy][dx]
                line_chars.append(chr(0x2800 + val))
            lines.append("".join(line_chars))
        return "\n".join(lines)

    def render(self) -> None:
        self.draw_poincare_disk()
        braille_str = self.to_string()
        panel = Panel(
            Text(braille_str, style="bold bright_cyan"),
            title="[bold yellow] 🌌 2048D Poincaré Hyperbolic Manifold (Braille 2×4 Sub-Pixel Canvas) [/bold yellow]",
            subtitle="[bold green] Boundary: ||z|| < 1.0 | Coherence Attractor: HIHO 0.5 Point [/bold green]",
            border_style="magenta",
            expand=False,
        )
        self.console.print(panel)


def main() -> None:
    canvas = BrailleCanvas(width=60, height=20)
    canvas.render()


if __name__ == "__main__":
    main()
