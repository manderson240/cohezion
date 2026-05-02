#!/usr/bin/env python3
"""
Mermaid Diagram Renderer
========================
Pre-renders Mermaid diagrams in markdown files to PNG/SVG images.

Usage:
    python render_mermaid.py path/to/file.md
    python render_mermaid.py --all  # Render all markdown files

Requires: mermaid-cli (npm install -g @mermaid-js/mermaid-cli)
"""

import argparse
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path


def find_mermaid_blocks(content: str) -> list[tuple[int, int, str]]:
    """Find all mermaid code blocks in markdown content."""
    pattern = r"```mermaid\n(.*?)```"
    matches = []

    for match in re.finditer(pattern, content, re.DOTALL):
        start = match.start()
        end = match.end()
        diagram_code = match.group(1).strip()
        matches.append((start, end, diagram_code))

    return matches


def render_diagram(diagram_code: str, output_path: Path, format: str = "png") -> bool:
    """Render mermaid diagram to image using mmdc CLI."""

    # Write diagram to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
        f.write(diagram_code)
        temp_path = f.name

    try:
        cmd = [
            "mmdc",
            "-i",
            temp_path,
            "-o",
            str(output_path),
            "-b",
            "transparent",
            "-t",
            "dark",  # Use dark theme for dark mode IDEs
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Error rendering diagram: {result.stderr}")
            return False

        return output_path.exists()

    except FileNotFoundError:
        print("ERROR: mermaid-cli (mmdc) not found. Install with:")
        print("  npm install -g @mermaid-js/mermaid-cli")
        return False
    except subprocess.TimeoutExpired:
        print("ERROR: Mermaid rendering timed out")
        return False
    finally:
        Path(temp_path).unlink(missing_ok=True)


def process_markdown_file(file_path: Path, output_dir: Path, format: str = "png") -> int:
    """Process a markdown file, rendering all mermaid diagrams."""

    content = file_path.read_text()
    blocks = find_mermaid_blocks(content)

    if not blocks:
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = 0
    new_content = content

    for start, end, diagram_code in reversed(blocks):  # Reverse to maintain positions
        # Generate deterministic filename from content hash
        hash_id = hashlib.md5(diagram_code.encode()).hexdigest()[:8]
        output_name = f"{file_path.stem}_mermaid_{hash_id}.{format}"
        output_path = output_dir / output_name

        if render_diagram(diagram_code, output_path, format):
            rendered += 1

            # Create image reference
            relative_path = (
                output_path.relative_to(file_path.parent)
                if output_path.is_relative_to(file_path.parent)
                else output_path
            )
            img_ref = f"![Diagram]({relative_path})\n\n<details>\n<summary>Mermaid Source</summary>\n\n```mermaid\n{diagram_code}\n```\n</details>"

            # Replace mermaid block with image + collapsible source
            new_content = new_content[:start] + img_ref + new_content[end:]

    if rendered > 0:
        # Optionally write back (commented out for safety)
        # file_path.write_text(new_content)
        print(f"Rendered {rendered} diagrams from {file_path}")

    return rendered


def main():
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams to images")
    parser.add_argument("path", nargs="?", help="Markdown file to process")
    parser.add_argument("--all", action="store_true", help="Process all markdown files")
    parser.add_argument(
        "--output-dir",
        "-o",
        default="renders/mermaid",
        help="Output directory for images",
    )
    parser.add_argument("--format", "-f", choices=["png", "svg", "pdf"], default="png")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.all:
        # Find all markdown files
        md_files = list(Path(".").rglob("*.md"))
        total = 0
        for md_file in md_files:
            if ".git" not in str(md_file) and "node_modules" not in str(md_file):
                total += process_markdown_file(md_file, output_dir, args.format)
        print(f"Total rendered: {total} diagrams")

    elif args.path:
        file_path = Path(args.path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 1
        process_markdown_file(file_path, output_dir, args.format)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
