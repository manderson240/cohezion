"""Experience vault for ARC task → program mappings using compound engineering."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arc_solver import Grid


@dataclass
class TaskSignature:
    """Extractable properties of an ARC task that indicate its transformation type."""

    input_rows: int
    input_cols: int
    output_rows: int
    output_cols: int
    input_colors: int
    output_colors: int
    color_delta: int
    shape_changed: bool
    size_ratio: float
    dominant_color_in: int
    dominant_color_out: int
    symmetry_score: float
    object_count_in: int
    object_count_out: int
    background_changed: bool

    def as_vector(self) -> list[float]:
        return [
            float(self.input_rows),
            float(self.input_cols),
            float(self.output_rows),
            float(self.output_cols),
            float(self.input_colors),
            float(self.output_colors),
            float(self.color_delta),
            1.0 if self.shape_changed else 0.0,
            self.size_ratio,
            float(self.dominant_color_in),
            float(self.dominant_color_out),
            self.symmetry_score,
            float(self.object_count_in),
            float(self.object_count_out),
            1.0 if self.background_changed else 0.0,
        ]


def extract_signature(task_train: list[dict[str, Grid]]) -> TaskSignature:
    """Extract a task signature from training examples."""
    ex = task_train[0]
    inp, out = ex["input"], ex["output"]

    rows_in, cols_in = len(inp), len(inp[0]) if inp else 0
    rows_out, cols_out = len(out), len(out[0]) if out else 0

    colors_in = len({c for row in inp for c in row})
    colors_out = len({c for row in out for c in row})

    cnt_in = Counter(c for row in inp for c in row)
    cnt_out = Counter(c for row in out for c in row)
    dom_in = cnt_in.most_common(1)[0][0] if cnt_in else 0
    dom_out = cnt_out.most_common(1)[0][0] if cnt_out else 0

    # Simple symmetry: check if grid equals its transpose
    sym = 0.0
    if rows_in == cols_in and rows_in > 1:
        matches = sum(1 for r in range(rows_in) for c in range(cols_in) if inp[r][c] == inp[c][r])
        sym = matches / (rows_in * cols_in)

    # Approximate object count (non-background connected components)
    bg_in = dom_in
    visited = [[False] * cols_in for _ in range(rows_in)]
    obj_in = 0
    for r in range(rows_in):
        for c in range(cols_in):
            if not visited[r][c] and inp[r][c] != bg_in:
                obj_in += 1
                stack = [(r, c)]
                visited[r][c] = True
                while stack:
                    cr, cc = stack.pop()
                    for nr, nc in [(cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)]:
                        if 0 <= nr < rows_in and 0 <= nc < cols_in:
                            if not visited[nr][nc] and inp[nr][nc] != bg_in:
                                visited[nr][nc] = True
                                stack.append((nr, nc))

    bg_out = dom_out
    visited = [[False] * cols_out for _ in range(rows_out)]
    obj_out = 0
    for r in range(rows_out):
        for c in range(cols_out):
            if not visited[r][c] and out[r][c] != bg_out:
                obj_out += 1
                stack = [(r, c)]
                visited[r][c] = True
                while stack:
                    cr, cc = stack.pop()
                    for nr, nc in [(cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)]:
                        if 0 <= nr < rows_out and 0 <= nc < cols_out:
                            if not visited[nr][nc] and out[nr][nc] != bg_out:
                                visited[nr][nc] = True
                                stack.append((nr, nc))

    return TaskSignature(
        input_rows=rows_in,
        input_cols=cols_in,
        output_rows=rows_out,
        output_cols=cols_out,
        input_colors=colors_in,
        output_colors=colors_out,
        color_delta=colors_out - colors_in,
        shape_changed=(rows_in != rows_out or cols_in != cols_out),
        size_ratio=(rows_out * cols_out) / max(1, rows_in * cols_in),
        dominant_color_in=dom_in,
        dominant_color_out=dom_out,
        symmetry_score=sym,
        object_count_in=obj_in,
        object_count_out=obj_out,
        background_changed=(dom_in != dom_out),
    )


def sig_distance(a: TaskSignature, b: TaskSignature) -> float:
    """Euclidean distance between task signatures."""
    va, vb = a.as_vector(), b.as_vector()
    # Normalize each dimension by its max to prevent scale dominance
    maxs = [max(abs(va[i]), abs(vb[i]), 1.0) for i in range(len(va))]
    return sum(((va[i] - vb[i]) / maxs[i]) ** 2 for i in range(len(va))) ** 0.5


@dataclass
class ExperienceEntry:
    """A single learned experience: task signature + successful program metadata."""

    task_id: str
    signature: TaskSignature
    program_names: list[str]
    solved: bool
    solve_time_ms: float


class ExperienceVault:
    """Stores and queries task → program experiences."""

    def __init__(self, path: str = ".pi/experience_arc.json") -> None:
        self.path = Path(path)
        self.entries: list[ExperienceEntry] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.entries = [
                ExperienceEntry(
                    task_id=e["task_id"],
                    signature=TaskSignature(**e["signature"]),
                    program_names=e["program_names"],
                    solved=e["solved"],
                    solve_time_ms=e["solve_time_ms"],
                )
                for e in data
            ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "task_id": e.task_id,
                "signature": {
                    "input_rows": e.signature.input_rows,
                    "input_cols": e.signature.input_cols,
                    "output_rows": e.signature.output_rows,
                    "output_cols": e.signature.output_cols,
                    "input_colors": e.signature.input_colors,
                    "output_colors": e.signature.output_colors,
                    "color_delta": e.signature.color_delta,
                    "shape_changed": e.signature.shape_changed,
                    "size_ratio": e.signature.size_ratio,
                    "dominant_color_in": e.signature.dominant_color_in,
                    "dominant_color_out": e.signature.dominant_color_out,
                    "symmetry_score": e.signature.symmetry_score,
                    "object_count_in": e.signature.object_count_in,
                    "object_count_out": e.signature.object_count_out,
                    "background_changed": e.signature.background_changed,
                },
                "program_names": e.program_names,
                "solved": e.solved,
                "solve_time_ms": e.solve_time_ms,
            }
            for e in self.entries
        ]
        self.path.write_text(json.dumps(data, indent=2))

    def add(self, entry: ExperienceEntry) -> None:
        self.entries.append(entry)

    def find_similar(
        self, sig: TaskSignature, top_k: int = 5
    ) -> list[tuple[float, ExperienceEntry]]:
        """Find top-k most similar solved experiences."""
        solved = [e for e in self.entries if e.solved]
        scored = [(sig_distance(sig, e.signature), e) for e in solved]
        scored.sort(key=lambda x: x[0])
        return scored[:top_k]

    def stats(self) -> dict[str, Any]:
        solved = [e for e in self.entries if e.solved]
        return {
            "total_tasks": len(self.entries),
            "solved": len(solved),
            "solve_rate": round(len(solved) / len(self.entries), 3) if self.entries else 0,
            "unique_programs": len({tuple(e.program_names) for e in solved}),
        }
