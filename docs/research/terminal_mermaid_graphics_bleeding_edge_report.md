# Bleeding-Edge Research: High-Fidelity Terminal Mermaid & Graph Graphics
**Timestamp**: 2026-08-18 23:02:57 EDT
**Consulted Frontier Fleet**: `deepseek-v4-pro:cloud`, `glm-5.2:cloud`, `qwen3.5:397b-cloud`
**Objective**: Achieve pixel-perfect and color-rich Mermaid / topological chart rendering directly in Linux terminals.

---

## 🎨 Kitty / Sixel / iTerm2 Graphics Protocols for Terminal Mermaid Rendering
**Frontier Model**: `deepseek-v4-pro:cloud` | **Research Latency**: `28.92s`

## Terminal Graphics Protocols for Inline Mermaid Diagrams in AI Coding Agents

Modern terminal emulators support rendering high‑fidelity images directly inside the terminal window, eliminating the need to open a separate browser for diagrams. This is especially useful for AI coding agents that generate Mermaid diagrams (flowcharts, sequence diagrams, etc.) and want to display them inline for the user.

This document surveys the state‑of‑the‑art protocols—**Kitty Graphics Protocol**, **Sixel**, **iTerm2 Inline Images**—and clarifies the role of tools like **Chafa** and **VisiData**. It then explains how an AI coding agent CLI can automatically detect terminal capabilities and emit rasterized Mermaid diagrams (PNG) using these protocols, with fallback strategies.

---

## 1. Terminal Graphics Protocols Overview

| Protocol | Terminal Support | Image Formats | Color Depth | Vector Support | Detection Method |
|----------|------------------|---------------|-------------|----------------|------------------|
| **Kitty Graphics Protocol** | Kitty, WezTerm, Konsole (partial), foot, etc. | PNG, raw RGBA, animations | True color (24‑bit) | No (raster only) | APC query (`ESC _ G i=1 ESC \`) |
| **Sixel** | xterm (with `--enable-sixel`), mlterm, foot, WezTerm, RLogin, etc. | Sixel bitmap (palette‑based) | Up to 256 colors (palette) | No | DA1 response contains `4` |
| **iTerm2 Inline Images** | iTerm2, WezTerm (partial), some others | PNG, JPEG, GIF, TIFF, etc. | True color | No | Environment variables (`TERM_PROGRAM=iTerm.app`) |

**Chafa** and **VisiData** are not protocols themselves.  
- **Chafa** is a command‑line tool that converts images into terminal graphics using one of several backends: Unicode block characters, Sixel, Kitty, iTerm2, or ANSI truecolor. It can be used as a subprocess or library.  
- **VisiData** is a terminal data exploration tool that can display images (e.g., in cells) by leveraging similar backends (often via Chafa or `viu`).  

For an AI coding agent, the most robust approach is to **directly implement the protocols** (or use a library that does) to avoid external dependencies, while optionally falling back to Chafa for ASCII/Unicode rendering.

---

## 2. Detecting Terminal Capabilities

Before emitting an image, the CLI must determine which protocol (if any) the terminal supports. Detection can be done via:

- **Environment variables** (fast, but not always reliable)
- **Terminfo database** (may not include graphics capabilities)
- **Active querying** using escape sequences (most reliable)

### 2.1 Kitty Graphics Protocol Detection

Kitty uses **Application Program Command (APC)** escape sequences. To query support, send:

```
ESC _ G i = 1 ESC \
```

In a shell:  
```bash
printf '\033_Gi=1\033\\'
```

If the terminal supports the protocol, it responds with:

```
ESC _ G i = 1 ; ok ESC \
```

The response can be read from stdin (if the terminal is attached) or via a temporary file descriptor. In practice, many libraries simply attempt to send an image and check for errors, but the query is cleaner.

**Python example** (using `sys.stdin` and `sys.stdout`):

```python
import sys, os, select

def kitty_supported():
    # Send query
    sys.stdout.write("\033_Gi=1\033\\")
    sys.stdout.flush()
    # Wait for response (with timeout)
    if select.select([sys.stdin], [], [], 0.5)[0]:
        response = os.read(sys.stdin.fileno(), 1024)
        return b"ok" in response
    return False
```

### 2.2 Sixel Detection

Sixel support is traditionally detected by sending **Device Attributes (DA1)**:

```
ESC [ c
```

The terminal responds with a sequence like `ESC [ ? 1 ; 2 ; 4 c`. The presence of `4` indicates Sixel support.

**Shell example**:

```bash
# Send DA1 and capture response
IFS= read -r -d 'c' -t 1 response < <(printf '\033[c')
if [[ "$response" == *"4"* ]]; then
    echo "Sixel supported"
fi
```

Alternatively, some terminals set the `TERM` variable to a value that includes `sixel` (e.g., `xterm-sixel`), but this is not universal. The DA1 query is more reliable.

### 2.3 iTerm2 Inline Images Detection

iTerm2 sets environment variables that can be checked:

- `TERM_PROGRAM` = `iTerm.app`
- `LC_TERMINAL` = `iTerm2`
- `ITERM_SESSION_ID` is present

**Shell example**:

```bash
if [[ "$TERM_PROGRAM" == "iTerm.app" || "$LC_TERMINAL" == "iTerm2" ]]; then
    echo "iTerm2 inline images supported"
fi
```

There is also an escape sequence to report the iTerm2 version (`ESC ] 1337 ; ReportVersion ST`), but environment variables are sufficient for most cases.

### 2.4 General Fallback

If none of the above protocols are detected, the CLI can fall back to:

- **Unicode/ASCII art** using Chafa (`chafa --format symbols`) or a custom block‑character renderer.
- **Opening the image in a browser** (e.g., using `xdg-open` or `open`).
- **Displaying the Mermaid source code** with a note that a graphical terminal is required.

---

## 3. Emitting Inline Graphs

The AI coding agent must first generate a raster image (PNG) from the Mermaid diagram. This can be done with:

- **Mermaid CLI** (`mmdc -i input.mmd -o output.png`)
- **mermaid.ink API** (HTTP request returning PNG)
- **Headless browser** (Puppeteer, Playwright) to render SVG to PNG

For high fidelity, generate the PNG at a high resolution (e.g., scale factor 2 or 3) and let the terminal scale it down.

Once the PNG is available, the CLI sends it using the appropriate protocol.

### 3.1 Kitty Graphics Protocol

The Kitty protocol transmits images as **base64‑encoded PNG** (or raw RGBA) inside an APC sequence.

**Format**:

```
ESC _ G a=T,f=100,s=<width>,v=<height>,c=<columns>,r=<rows>; <base64 data> ESC \
```

- `a=T` – transmission action
- `f=100` – format 100 = PNG
- `s`, `v` – image size in pixels (optional, terminal can infer from PNG)
- `c`, `r` – number of terminal cells to occupy (optional)
- `q=2` – quiet mode (suppress response)

**Python example**:

```python
import base64, sys

def kitty_display_png(png_path):
    with open(png_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    sys.stdout.write(f"\033_Ga=T,f=100;{data}\033\\")
    sys.stdout.flush()
```

### 3.2 Sixel

Sixel is a bitmap format that encodes pixels as a series of characters. The easiest way is to use a tool like `img2sixel` (from libsixel) or `chafa --format sixel`. However, for a self‑contained CLI, you can implement a minimal Sixel encoder or use a library (e.g., `PySixel` in Python).

**Basic Sixel emission**:

```
ESC P q <sixel data> ESC \
```

The Sixel data consists of:
- Color definitions (`#<id>;2;<r>;<g>;<b>`)
- Pixel data using characters `?` to `~` (63‑126) to represent six vertical pixels.

**Using `img2sixel` as subprocess** (if available):

```bash
img2sixel diagram.png
```

**Python with `chafa` subprocess**:

```python
import subprocess

def sixel_display_png(png_path):
    subprocess.run(["chafa", "--format", "sixel", png_path])
```

### 3.3 iTerm2 Inline Images

iTerm2 uses an **OSC 1337** sequence with a `File` command and `inline=1` parameter.

**Format**:

```
ESC ] 1337 ; File=name=<base64 name>;inline=1;size=<bytes>;width=<px>;height=<px>: <base64 data> BEL
```

- `BEL` is `\a` or `\x07`
- `size` is the number of bytes of the original file (before base64)
- `width` and `height` are optional but recommended for proper scaling

**Python example**:

```python
import base64, sys

def iterm2_display_png(png_path):
    with open(png_path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    # Get image dimensions (using PIL or similar)
    from PIL import Image
    with Image.open(png_path) as img:
        w, h = img.size
    sys.stdout.write(f"\033]1337;File=inline=1;size={len(raw)};width={w}px;height={h}px:{b64}\a")
    sys.stdout.flush()
```

---

## 4. Integration in an AI Coding Agent CLI

A robust implementation should:

1. **Detect** the best available protocol (Kitty > iTerm2 > Sixel > fallback).
2. **Generate** the Mermaid diagram as PNG (cached for reuse).
3. **Emit** the image using the chosen protocol.
4. **Fallback** to ASCII art or browser if no protocol is supported.

### 4.1 Using a Library

Several libraries abstract these protocols:

- **`term-image`** (Python) – supports Kitty, iTerm2, Sixel, and Unicode.
- **`chafa`** (C library / CLI) – can output to any backend.
- **`viu`** (Rust) – similar to Chafa.

For an AI coding agent, using `term-image` is convenient:

```python
from term_image.image import from_file

image = from_file("diagram.png")
image.draw()  # automatically selects best protocol
```

### 4.2 Fallback to ASCII/Unicode

If no graphics protocol is available, use Chafa’s symbol output:

```bash
chafa --format symbols --size 80x40 diagram.png
```

This produces a block‑character representation that works in any terminal.

### 4.3 Performance Considerations

- **Caching**: Store generated PNGs keyed by Mermaid source hash to avoid re‑rendering.
- **Image size**: Limit the image to the terminal’s current width/height (query via `stty size` or `TIOCGWINSZ`).
- **Transmission**: For large diagrams, consider downscaling or using a lower color depth (e.g., Sixel’s palette) to reduce data size.

---

## 5. Conclusion

Terminal graphics protocols enable AI coding agents to display rich, colorized Mermaid diagrams directly in the terminal, improving user experience without leaving the CLI. By detecting support via escape sequences or environment variables and emitting PNG data using the appropriate protocol, an agent can provide high‑fidelity inline graphics across a wide range of modern terminals. When no protocol is available, falling back to Unicode art or opening a browser ensures the diagram is still accessible.

The key steps are:

- **Detect** Kitty via APC query, Sixel via DA1, iTerm2 via environment variables.
- **Render** Mermaid to PNG using `mmdc` or a headless browser.
- **Emit** the PNG using the protocol’s escape sequence.
- **Fallback** to Chafa/Unicode or browser if needed.

This approach is already used by tools like `gh` (GitHub CLI) and `rich` (Python library) and can be easily integrated into any AI coding agent.

---

## 🎨 Mermaid AST Parser to Rich Unicode Box-Drawing & Directed Graph Layout
**Frontier Model**: `glm-5.2:cloud` | **Research Latency**: `29.63s`

Compiling Mermaid syntax into a terminal-native, Rich/Textual-rendered graph involves a multi-stage pipeline: **Parsing (Mermaid → AST)**, **Layout (AST → Sugiyama Coordinates)**, and **Rasterization (Coordinates → ANSI TrueColor Canvas)**. 

Here is a comprehensive breakdown of the techniques required for this pipeline, followed by a comparative analysis of the available tools and libraries.

---

### Phase 1: Compiling Mermaid Syntax to an AST

Since Mermaid is traditionally a JavaScript/TypeScript ecosystem, building a native Python parser is required for seamless integration with Rich/Textual. 

**Technique: Lark-based EBNF Parser**
Using the `lark` library, you can define a Context-Free Grammar (CFG) to parse Mermaid flowcharts. 

1. **Lexing:** Tokenize keywords (`flowchart`, `subgraph`, `end`, `-->`), node IDs, text labels (`["..."]`), and styling rules (`style node fill:#...`).
2. **AST Generation:** Transform the parse tree into a logical AST.
   * **Nodes:** Store ID, label, shape (rect, round, stadium).
   * **Edges:** Store source, target, direction, label, arrow type.
   * **Subgraphs:** Handled as nested containers (clusters) in the AST.
   * **Styles:** Map Mermaid hex colors to 24-bit RGB tuples for later rasterization.

```python
# Conceptual Lark Grammar snippet
flowchart: "flowchart" direction? graph_item+
graph_item: node_def | edge_def | subgraph_def | style_def
node_def: ID ("[" | "(" | "{") TEXT ("]" | ")" | "}")
edge_def: ID ("-->"|"---"|"-.->") ID
subgraph_def: "subgraph" ID graph_item* "end"
style_def: "style" ID "fill:" HEXCOLOR
```

### Phase 2: Computing Sugiyama-Style Coordinates

The Sugiyama framework is the gold standard for layered graph drawing (used by Graphviz's `dot`). It consists of four steps:
1. **Cycle Removal:** Reverses back-edges to make the graph a DAG.
2. **Layering:** Assigns nodes to hierarchical layers (Y-coordinates). 
3. **Crossing Reduction:** Reorders nodes within layers to minimize edge crossings (using the Barycenter heuristic).
4. **Coordinate Assignment:** Assigns X-coordinates while keeping edges straight and balancing nodes.

**Handling Subgraphs in Sugiyama:**
Subgraphs complicate the Sugiyama algorithm because they require *compound graph layouts*. 
* *Technique:* Flatten the graph for layout, compute coordinates, and then calculate a bounding box around all child nodes. Expand the bounding box to accommodate padding/borders, and push neighboring nodes outwards to prevent overlap.

### Phase 3: Rasterization to Rich/Textual Canvas

Once you have `(x, y)` coordinates for nodes and edge paths, you must rasterize them to a 2D character grid.

**Techniques:**
* **Box Drawing:** Map terminal characters to layout intersections. Use `┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼` for corners and `│ ─` for straight lines. For curved edges (Sugiyama splines), use `╭ ╮ ╰ ╯`.
* **TrueColor ANSI:** Rich supports 24-bit TrueColor. When rasterizing, apply `rich.color.Color.parse("#RRGGBB")` to the background (`bg`) of the node bounding box and the foreground (`fg`) of the edges.
* **Textual Integration:** Use Textual's `Canvas` widget. You can write pixel-by-pixel (character-by-character) to the canvas, applying styles per character.

---

### Comparison of Tools & Approaches

#### 1. `graph-easy` (Perl/CLI)
* **What it is:** A Perl CLI tool that converts Graphviz/DOT files to ASCII art.
* **Mermaid Support:** None natively. You must transpile Mermaid to DOT first.
* **Layout:** Uses Graphviz under the hood (full Sugiyama).
* **Rasterization:** Pure ASCII/Unicode. No 24-bit color, no native Python/Rich integration.
* **Verdict:** Good for quick CLI debugging, but unsuitable for a native Rich/Textual application. Requires shell-outs and stripping ANSI to fit into Python.

#### 2. `mermaid-ascii` (Node.js/CLI)
* **What it is:** A JS-based tool for rendering Mermaid graphs as ASCII.
* **Mermaid Support:** Native. Parses Mermaid syntax directly.
* **Layout:** Usually relies on Dagre (a JS implementation of Sugiyama).
* **Rasterization:** Basic ASCII/Unicode. Lacks 24-bit color and Python ecosystem integration.
* **Verdict:** Excellent reference for how to handle Mermaid parsing and edge rasterization, but running it inside a Python app requires Node.js as an external dependency, defeating the purpose of a native TUI.

#### 3. Textual Graph Widgets
* **What it is:** Textual does not currently ship with a first-party Sugiyama graph layout widget. It has `Sparkline` and `DataTable`, but no topological graph widget.
* **Approach:** You must build a custom `Widget` inheriting from `textual.widget.Widget`.
* **Technique:** Override `on_mount` to instantiate a `Canvas`. Override `render()` to map your Sugiyama coordinates to the Canvas. Textual handles the scrolling, focus, and mouse interactions (e.g., clicking a node).
* **Verdict:** This is the ultimate destination for your pipeline. Textual provides the interactive UI layer, but provides *zero* layout logic—you must bring the AST and Sugiyama engine yourself.

#### 4. Custom Python Engines (`grandalf` + `lark` + `rich`)
* **What it is:** A pure-Python pipeline. 
* **Components:**
  * `lark` for Mermaid parsing.
  * `grandalf` (a pure Python graph layout library) for the Sugiyama algorithm. `grandalf` handles the 4 stages of Sugiyama out of the box.
  * `rich` or `textual.Canvas` for rasterization.
* **Workflow:**
  1. Lark parses Mermaid -> AST.
  2. AST is translated into `grandalf`'s `Vertex` and `Edge` objects.
  3. `grandalf.layouts.SugiyamaLayout` computes `view.xy` coordinates for each node.
  4. A custom Python function iterates through these coordinates, drawing boxes and splines onto a `rich.console.Console` or Textual `Canvas`.
* **Pros:** Zero non-Python dependencies. Full control over TrueColor ANSI, custom shapes, and Textual widget integration. You can easily map Mermaid `style` rules directly to `rich.style.Style`.
* **Cons:** You must write the rasterizer (mapping graph edges to Unicode characters) from scratch, as `grandalf` only outputs mathematical coordinates.

### Architectural Recommendation

To achieve true 24-bit ANSI Mermaid rendering inside a Rich/Textual application, bypass `graph-easy` and `mermaid-ascii`. 

Instead, implement the following pipeline:
1. **Parser:** Define a Lark grammar for Mermaid flowcharts. Convert to an AST.
2. **Layout:** Feed the AST into `grandalf`. Extend `grandalf`'s layout to calculate bounding boxes for subgraphs after the initial node coordinate pass.
3. **Rasterizer:** Write a Python module that translates `grandalf`'s coordinate output into a 2D array of `rich.text.Text` or `textual.canvas.Canvas` pixels. Use Bresenham's line algorithm to rasterize edge paths into Unicode box-drawing characters. 
4. **UI:** Wrap the rasterizer in a Textual `Widget`, handling scrolling and zooming.

---

## 🎨 Braille Unicode Vectors & ASCII Shading for Topological Manifolds in CLI
**Frontier Model**: `qwen3.5:397b-cloud` | **Research Latency**: `65.38s`

Rendering continuous manifolds in a CLI environment is a constraint-satisfaction problem involving **dimensionality reduction**, **rasterization**, and **glyph selection**. Terminals are inherently discrete 2D grids, while manifolds (especially hyperbolic or high-dimensional ones) are continuous and often exceed 3 dimensions.

Below is a research framework and implementation guide for rendering these structures using Unicode Braille, Block elements, and ANSI color, utilizing the specified libraries.

---

### 1. Mathematical Foundation & Projection Pipeline

Before rendering, the manifold must be transformed into terminal coordinates.

#### A. Manifold Parameterization
*   **3D Torus:** Defined by major radius $R$ and minor radius $r$.
    $$x = (R + r \cos v) \cos u$$
    $$y = (R + r \cos v) \sin u$$
    $$z = r \sin v$$
*   **Poincaré Disk (Hyperbolic $H^2$):** Maps infinite hyperbolic space into a unit disk.
    $$ds^2 = \frac{4(dx^2 + dy^2)}{(1 - (x^2 + y^2))^2}$$
    *Note on "12D Poincaré":* Standard terminology refers to the Poincaré *Ball* model for $H^n$. Visualizing 12D data requires **Dimensionality Reduction** (PCA, t-SNE, UMAP) to project to 2D/3D before terminal rendering, or a specific slice projection.

#### B. The Rendering Pipeline
1.  **Sampling:** Generate a point cloud or mesh on the manifold.
2.  **Transformation:** Apply rotation matrices (3D) or Möbius transformations (Hyperbolic).
3.  **Projection:** Perspective or Orthographic projection to 2D terminal space $(x, y)$.
4.  **Rasterization:** Map $(x, y)$ to terminal grid $(col, row)$.
5.  **Sub-pixel Mapping:** Map residual fractional coordinates to Braille dots or Block halves.
6.  **Shading:** Map depth ($z$-buffer) or normal vectors to ANSI color codes.

---

### 2. Unicode Rendering Techniques

#### A. Unicode Braille (U+2800..U+28FF)
*   **Resolution:** 2 columns $\times$ 4 rows of dots per character cell.
*   **Density:** 8 dots allow $2^8 = 256$ unique patterns per cell.
*   **Mapping:** A 2x4 boolean grid maps directly to the Braille byte offset.
    *   Dot 1 (top-left) $\to$ bit 0
    *   Dot 4 (bottom-left) $\to$ bit 3
    *   Dot 5 (top-right) $\to$ bit 4
    *   ...etc.
*   **Use Case:** High-resolution line drawing and sparse point clouds.

#### B. Block Elements (U+2580..U+258F)
*   **Resolution:** Primarily half-blocks (`▀` U+2580, `▄` U+2584) provide 2 vertical sub-pixels.
*   **Shading:** Combining foreground and background colors on half-blocks creates the illusion of 1 extra vertical pixel of resolution and smooth color gradients.
*   **Use Case:** Solid surface rendering with depth shading.

#### C. ANSI Shading (256/TrueColor)
*   **Z-Buffering:** Normalize depth $z \in [z_{min}, z_{max}]$ to color index $0..255$.
*   **Normal Shading:** Calculate surface normal $\vec{n}$ and light vector $\vec{l}$. Intensity $I = \max(0, \vec{n} \cdot \vec{l})$. Map $I$ to grayscale or heatmap ANSI codes.

---

### 3. Library Analysis & Selection

| Library | Primary Strength | Manifold Suitability | Rendering Method |
| :--- | :--- | :--- | :--- |
| **`drawille`** | **Braille Rasterization** | **High.** Best for converting pixel buffers to Braille chars. | Direct pixel-to-Braille mapping. |
| **`textual`** | **Interactive TUI Framework** | **Medium-High.** `textual-canvas` allows custom drawing logic with reactive updates. | Canvas drawing commands, supports Braille/Blocks. |
| **`plotext`** | **Static Data Plotting** | **Low-Medium.** Optimized for charts, not custom geometry rasterization. | High-level plot APIs. |
| **`termplot`** | **Simple Terminal Plotting** | **Low.** Generally wraps gnuplot or simple line drawing. | ASCII lines/blocks. |

#### Deep Dive: `drawille`
This is the critical library for Braille rendering. It maintains a virtual pixel buffer.
*   **Method:** `canvas.set_pixel(x, y)` automatically handles the Braille character lookup.
*   **Limitation:** It treats pixels as binary (on/off). For shading, you must layer Braille with ANSI color codes manually.

#### Deep Dive: `textual-canvas`
Part of the `textual` Python TUI framework.
*   **Method:** Provides a `Canvas` widget where you can draw lines, points, and polygons.
*   **Advantage:** Handles terminal resizing, event loops, and TrueColor styling natively.
*   **Strategy:** Use `textual` for the app shell and `numpy` for the math, drawing directly to the canvas context.

---

### 4. Implementation Strategy: Rotating 3D Torus

Below is a research-grade prototype combining `numpy` for math and `drawille` for Braille rendering, with ANSI color for depth.

#### Prerequisites
```bash
pip install drawille numpy blessed
```

#### Code Concept
```python
import numpy as np
import drawille
import sys
import time
from blessed import Terminal

# Terminal Setup
term = Terminal()
width, height = term.width, term.height
# Aspect Ratio Correction (Fonts are usually 2:1 height:width)
ASPECT = 0.5 

# Manifold Parameters (Torus)
R, r = 10, 4
u = np.linspace(0, 2 * np.pi, 60)
v = np.linspace(0, 2 * np.pi, 30)
u, v = np.meshgrid(u, v)

# Pre-calculate Torus Geometry
X = (R + r * np.cos(v)) * np.cos(u)
Y = (R + r * np.cos(v)) * np.sin(u)
Z = r * np.sin(v)

def rotate(points, angle, axis):
    """Rotate points around an axis."""
    c, s = np.cos(angle), np.sin(angle)
    if axis == 'z':
        M = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    elif axis == 'x':
        M = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    else:
        M = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.dot(points, M.T)

def render_frame(angle):
    # 1. Transform
    pts = np.stack([X.flatten(), Y.flatten(), Z.flatten()])
    pts = rotate(pts.T, angle, 'z')
    pts = rotate(pts, angle * 0.5, 'x')
    
    # 2. Project (Orthographic for simplicity)
    # Scale to terminal size
    x_proj = (pts[:, 0] * 2 + width / 2).astype(int)
    y_proj = (pts[:, 1] * ASPECT * 2 + height / 2).astype(int)
    z_depth = pts[:, 2]
    
    # 3. Rasterize to Braille Buffer
    canvas = drawille.Canvas()
    
    # Z-Buffering simulation (simple painter's algorithm sort)
    order = np.argsort(z_depth)
    
    for i in order:
        px, py = x_proj[i], y_proj[i]
        if 0 <= px < width * 2 and 0 <= py < height * 4: # Drawille uses sub-pixel coords
            # Map depth to ANSI Color (256 grayscale)
            depth_norm = int((z_depth[i] - r) / (2 * r) * 23) + 232
            color_code = f"\033[38;5;{depth_norm}m"
            
            # Drawille works on integer pixel coords (2x4 per char)
            # We must scale our terminal coords to drawille coords
            canvas.set_pixel(px, py)

    # 4. Output with Color
    # Note: Drawille outputs plain text. We must inject color based on depth.
    # For advanced shading, custom Braille mapping is required instead of drawille's binary buffer.
    frame_str = canvas.frame()
    
    # Clear and Print
    sys.stdout.write(term.home + term.clear)
    sys.stdout.write(frame_str)
    sys.stdout.flush()

# Animation Loop
try:
    i = 0
    while True:
        render_frame(i * 0.1)
        i += 1
        time.sleep(0.05)
except KeyboardInterrupt:
    print(term.normal)
```

### 5. Advanced Research: Custom Braille Shading
`drawille` is binary (dot on/off). To render *continuous* shading on a manifold, you must implement a **Custom Glyph Mapper**.

1.  **Grid:** Divide terminal cell into 2x4 sub-pixels.
2.  **Accumulation:** For each frame, calculate how many sub-pixels are covered by the manifold surface within that cell.
3.  **Intensity:** Map coverage count (0..8) to Braille character intensity.
4.  **Color:** Map average Z-depth of covered sub-pixels to ANSI foreground/background.

**Algorithm for Custom Mapper:**
```python
BRAILLE_MAP = {
    0: ' ', 1: '⠁', 2: '⠂', ... # Map bitmasks to chars
}

def get_braille_char(subpixel_mask):
    # subpixel_mask is an integer 0-255 representing the 8 dots
    return chr(0x2800 + subpixel_mask)
```

### 6. Handling High-Dimensional Manifolds (12D+)
You cannot render 12 dimensions directly. You must use **Manifold Learning**.

1.  **Input:** Data points $X \in \mathbb{R}^{12}$.
2.  **Reduction:** Use `umap-learn` or `sklearn.manifold.TSNE` to project $X \to X' \in \mathbb{R}^2$.
3.  **Hyperbolic Embedding:** If the data is hierarchical, use **Poincaré Embeddings** (hyperbolic space).
    *   Project 12D data to Poincaré Ball $B^{12}$.
    *   Stereographically project $B^{12} \to B^2$ (2D Disk).
    *   Render the 2D Disk using the Braille method.
4.  **Visualization:** Points near the edge of the Poincaré disk represent "infinity" in hyperbolic space. Use color saturation to indicate radial distance from the origin.

### 7. Performance Optimization
*   **Vectorization:** Never loop over points in Python. Use `numpy` broadcasting for all coordinate transformations.
*   **Dirty Rectangles:** In `textual` or `curses`, only redraw cells that changed.
*   **Buffering:** Construct the entire frame string in memory before writing to `stdout` to prevent flickering.
*   **Resolution Scaling:** If the manifold is complex, render at 1/4 resolution and use Block elements (`▄`) to smooth edges, rather than full Braille resolution which consumes more CPU for bitmask calculation.

### 8. Recommended Stack for Production
For a robust research tool, combine the libraries as follows:
1.  **Math:** `numpy` + `scipy` (for manifold equations).
2.  **Projection:** `umap-learn` (for 12D->2D reduction).
3.  **UI Framework:** `textual` (handles input, resizing, layout).
4.  **Rendering Engine:** Custom Braille mapper (inside `textual-canvas`) for shading control, falling back to `drawille` for simple wireframes.
5.  **Color:** ANSI TrueColor (24-bit) for smooth depth gradients.

### Summary of Methods
| Feature | Method | Library Support |
| :--- | :--- | :--- |
| **Wireframe** | Braille Dots | `drawille` |
| **Solid Surface** | Half-Blocks + Color | `textual-canvas` / Custom |
| **Depth Shading** | Z-Buffer -> ANSI 256 | Custom / `blessed` |
| **High-D Projection** | UMAP / Poincaré Embed | `umap-learn` / `geoopt` |
| **Interaction** | Event Loop | `textual` |

This approach allows you to visualize complex topological structures within the strict constraints of a text terminal, leveraging Unicode density to approximate continuous geometry.

---
