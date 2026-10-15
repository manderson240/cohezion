#!/usr/bin/env python3
"""Compiles the Gemma 4 Developer Agent research manuscript into a publication-ready arXiv-style PDF."""

import subprocess
import shutil
from pathlib import Path


def compile_manuscript_to_pdf():
    source_file = Path("docs/research/gemma4_developer_agent_paper_manuscript.md")
    if not source_file.exists():
        raise FileNotFoundError(f"Manuscript source not found at {source_file}")

    content = source_file.read_text(encoding="utf-8")
    
    # Locate markdown code block for the manuscript
    marker = "# Compound Graph Engineering & Token-Insulated Hierarchical Agents"
    start_pos = content.find(marker)
    if start_pos != -1:
        end_pos = content.find("\n```\n\n***", start_pos)
        if end_pos != -1:
            manuscript_text = content[start_pos:end_pos]
        else:
            manuscript_text = content[start_pos:]
    else:
        manuscript_text = content

    out_dir = Path("dist/papers")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    md_file = out_dir / "gemma4_compound_agent_paper.md"
    html_file = out_dir / "gemma4_compound_agent_paper.html"
    pdf_file = out_dir / "gemma4_compound_agent_paper.pdf"
    
    md_file.write_text(manuscript_text, encoding="utf-8")
    
    # Convert to self-contained HTML with mathjax and academic styling
    css_styling = """
    <style>
    body {
        font-family: 'Latin Modern Roman', 'Times New Roman', Times, serif;
        font-size: 11pt;
        line-height: 1.5;
        max-width: 8.5in;
        margin: 1in auto;
        padding: 0 0.5in;
        color: #111;
    }
    h1 { font-size: 18pt; text-align: center; margin-bottom: 0.5em; }
    h2 { font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; margin-top: 1.5em; }
    h3 { font-size: 12pt; margin-top: 1.2em; }
    p, li { text-align: justify; }
    pre { background: #f4f4f4; padding: 10px; border-radius: 4px; font-size: 9pt; overflow-x: auto; }
    code { font-family: 'Courier New', Courier, monospace; font-size: 9.5pt; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
    th { background: #f2f2f2; }
    @page { margin: 1in; }
    </style>
    """
    
    header_file = out_dir / "header.html"
    header_file.write_text(css_styling, encoding="utf-8")

    cmd_pandoc = [
        "pandoc",
        str(md_file),
        "-s",
        "--mathjax",
        "-H", str(header_file),
        "-o", str(html_file),
        "--metadata", "title=Compound Graph Engineering & Token-Insulated Hierarchical Agents for Autonomous Software Engineering on Gemma 4"
    ]
    subprocess.run(cmd_pandoc, check=True)
    
    # Compile to PDF using headless Chrome
    cmd_chrome = [
        "google-chrome",
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        f"--print-to-pdf={pdf_file}",
        str(html_file.resolve()),
    ]
    subprocess.run(cmd_chrome, check=True)
    
    print(f"✓ Publication PDF compiled successfully: {pdf_file} ({pdf_file.stat().st_size:,} bytes)")


if __name__ == "__main__":
    compile_manuscript_to_pdf()
