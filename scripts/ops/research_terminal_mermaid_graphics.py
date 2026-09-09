#!/usr/bin/env python3
"""Bleeding-Edge Terminal Mermaid & High-Fidelity Graph Rendering Research.

Consults the Ollama Cloud Frontier Fleet (deepseek-v4-pro:cloud, glm-5.2:cloud, qwen3.5:397b-cloud)
to investigate cutting-edge techniques for terminal graphics, Kitty/Sixel graphics protocols,
rich Unicode Braille graphs, and colored Mermaid AST compilation directly to terminal canvas.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

import httpx


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.core.resource_management.write_budget_governor import WriteBudgetGovernor


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mermaid_research")

RESEARCH_TOPICS = [
    {
        "id": "terminal_graphics_protocols",
        "title": "Kitty / Sixel / iTerm2 Graphics Protocols for Terminal Mermaid Rendering",
        "model": "deepseek-v4-pro:cloud",
        "prompt": (
            "Research state-of-the-art terminal graphics protocols (Kitty Graphics Protocol, Sixel, iTerm2 Inline Images, and Chafa/VisiData) "
            "for rendering high-fidelity, colorized Mermaid SVG/PNG diagrams directly inside terminal emulators without opening a web browser. "
            "Detail how an AI coding agent CLI can automatically detect terminal capabilities (e.g. query Kitty via APC escape codes) and emit inline bitmap/vector graphs."
        ),
    },
    {
        "id": "mermaid_ast_to_unicode_box_canvas",
        "title": "Mermaid AST Parser to Rich Unicode Box-Drawing & Directed Graph Layout",
        "model": "glm-5.2:cloud",
        "prompt": (
            "Research techniques for compiling Mermaid flowchart syntax (subgraphs, nodes, directional edges, custom styles) "
            "directly into an AST, computing Sugiyama-style layered graph coordinates, and rasterizing into a Rich/Textual ANSI 24-bit TrueColor Unicode box canvas. "
            "Compare graph-easy, mermaid-ascii, Textual graph widgets, and custom Python Sugiyama layout engines."
        ),
    },
    {
        "id": "sixels_braille_vector_canvas",
        "title": "Braille Unicode Vectors & ASCII Shading for Topological Manifolds in CLI",
        "model": "qwen3.5:397b-cloud",
        "prompt": (
            "Research methods for rendering continuous 2D/3D manifolds (like the 12D Poincaré disk or 3D torus) inside CLI terminals "
            "using Unicode Braille characters (U+2800..U+28FF, 2x4 dot resolution), block elements (U+2580..U+258F), and ANSI 256/TrueColor shading. "
            "Highlight libraries like plotext, termplot, textual-canvas, and drawille."
        ),
    },
]


async def query_cloud_researcher(client: httpx.AsyncClient, topic: dict[str, str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("🚀 [Frontier Research] Querying %s via %s...", topic["id"], topic["model"])

    response_text = ""
    try:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": topic["model"],
                "prompt": topic["prompt"],
                "stream": False,
            },
            timeout=90.0,
        )
        if res.status_code == 200:
            data = res.json()
            response_text = data.get("response", "")
            logger.info("  ✓ [%s] Received %d words from %s", topic["id"], len(response_text.split()), topic["model"])
    except Exception as e:
        logger.warning("Cloud error on %s: %s", topic["id"], e)

    if "</think>" in response_text:
        response_text = response_text.split("</think>")[-1].strip()

    dt = time.perf_counter() - t0
    return {
        "id": topic["id"],
        "title": topic["title"],
        "model": topic["model"],
        "latency_s": round(dt, 2),
        "content": response_text,
    }


async def main_async() -> None:
    print("=" * 100)
    print("    🌐 BLEEDING-EDGE RESEARCH: TERMINAL MERMAID & GRAPH GRAPHICS")
    print("=" * 100)

    t_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        tasks = [query_cloud_researcher(client, topic) for topic in RESEARCH_TOPICS]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    out_file = Path("/home/mike-anderson/dev/cohezion/docs/research/terminal_mermaid_graphics_bleeding_edge_report.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    md = [
        "# Bleeding-Edge Research: High-Fidelity Terminal Mermaid & Graph Graphics",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S EDT')}",
        "**Consulted Frontier Fleet**: `deepseek-v4-pro:cloud`, `glm-5.2:cloud`, `qwen3.5:397b-cloud`",
        "**Objective**: Achieve pixel-perfect and color-rich Mermaid / topological chart rendering directly in Linux terminals.",
        "",
        "---",
        "",
    ]

    for r in results:
        md.append(f"## 🎨 {r['title']}")
        md.append(f"**Frontier Model**: `{r['model']}` | **Research Latency**: `{r['latency_s']}s`")
        md.append("")
        md.append(r["content"])
        md.append("")
        md.append("---")
        md.append("")

    # Enforce safe write with WriteBudgetGovernor
    gov = WriteBudgetGovernor()
    gov.safe_write_text(out_file, "\n".join(md))
    dt_total = time.perf_counter() - t_start

    print("\n" + "=" * 100)
    print(f"🎉 TERMINAL MERMAID RESEARCH COMPLETE IN {dt_total:.2f}s!")
    print(f"📝 Master Report saved to: {out_file}")
    print("=" * 100)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
