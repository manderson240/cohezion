"""
ARC Bitboard Engine
===================
Elegantly simple, high-performance bitboard representation for ARC-AGI $30 \\times 30$ grids.
Packs grid states into 10 color bitplanes of row bitmasks ($0 \\le \\text{color} \\le 9$),
executing spatial transformations, bounding boxes, overlaps, and color frequency queries
via native single-cycle bitwise operations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArcBitboard:
    """Zero-allocation 10-color bitboard for ARC grids up to 30x30."""

    height: int
    width: int
    # 10 planes (one per ARC color 0..9). Each plane is a tuple of H integers (row bitmasks).
    planes: tuple[tuple[int, ...], ...]

    @classmethod
    def from_grid(cls, grid: Sequence[Sequence[int]]) -> ArcBitboard:
        """Construct an ArcBitboard from a 2D integer grid."""
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0
        if h > 32 or w > 32:
            raise ValueError(
                f"Grid dimensions ({h}x{w}) exceed maximum supported 32x32 bitboard size."
            )

        # Initialize 10 planes of height H
        raw_planes = [[0] * h for _ in range(10)]
        for y, row in enumerate(grid):
            for x, val in enumerate(row):
                if 0 <= val <= 9:
                    raw_planes[val][y] |= 1 << x
                else:
                    raise ValueError(
                        f"Invalid ARC color {val} at ({y}, {x}). Must be in range 0..9."
                    )

        frozen_planes = tuple(tuple(plane) for plane in raw_planes)
        return cls(height=h, width=w, planes=frozen_planes)

    def to_grid(self) -> list[list[int]]:
        """Reconstruct 2D grid from bitboard planes."""
        grid = [[0] * self.width for _ in range(self.height)]
        for color, plane in enumerate(self.planes):
            for y, row_mask in enumerate(plane):
                m = row_mask
                while m > 0:
                    lsb = m & -m
                    x = lsb.bit_length() - 1
                    grid[y][x] = color
                    m ^= lsb
        return grid

    def color_count(self, color: int) -> int:
        """Count total pixels of the specified color using popcount."""
        return sum(row.bit_count() for row in self.planes[color])

    def color_counts(self) -> dict[int, int]:
        """Return counts for all colors present in the grid."""
        return {c: self.color_count(c) for c in range(10) if any(self.planes[c])}

    def has_color(self, color: int) -> bool:
        """Check if color is present in the grid in O(H) integer checks."""
        return any(row != 0 for row in self.planes[color])

    def bounding_box(self, color: int) -> tuple[int, int, int, int] | None:
        """Compute (min_y, max_y, min_x, max_x) for a color mask. Returns None if color absent."""
        plane = self.planes[color]
        active_rows = [(y, r) for y, r in enumerate(plane) if r != 0]
        if not active_rows:
            return None

        min_y = active_rows[0][0]
        max_y = active_rows[-1][0]
        min_x = min((r & -r).bit_length() - 1 for _, r in active_rows)
        max_x = max(r.bit_length() - 1 for _, r in active_rows)
        return (min_y, max_y, min_x, max_x)

    def translate(self, dy: int, dx: int, fill_color: int = 0) -> ArcBitboard:
        """Translate the grid by (dy, dx) with boundary clipping."""
        h, w = self.height, self.width
        col_mask = (1 << w) - 1

        new_planes = []
        for color in range(10):
            plane = self.planes[color]
            shifted_rows = [0] * h
            for y in range(h):
                src_y = y - dy
                if 0 <= src_y < h:
                    row = plane[src_y]
                    if dx >= 0:
                        shifted_rows[y] = (row << dx) & col_mask
                    else:
                        shifted_rows[y] = (row >> abs(dx)) & col_mask
            new_planes.append(shifted_rows)

        # Fill newly uncovered regions with fill_color
        all_occupied = [0] * h
        for color in range(10):
            for y in range(h):
                all_occupied[y] |= new_planes[color][y]

        for y in range(h):
            uncovered = col_mask ^ all_occupied[y]
            if uncovered:
                new_planes[fill_color][y] |= uncovered

        return ArcBitboard(height=h, width=w, planes=tuple(tuple(p) for p in new_planes))

    def reflect_h(self) -> ArcBitboard:
        """Horizontal reflection (flip across vertical axis / reverse columns)."""
        w = self.width
        new_planes = []
        for color in range(10):
            plane = self.planes[color]
            flipped_rows = []
            for row in plane:
                # Reverse bits of row up to width w
                rev = 0
                temp = row
                for i in range(w):
                    if (temp >> i) & 1:
                        rev |= 1 << (w - 1 - i)
                flipped_rows.append(rev)
            new_planes.append(tuple(flipped_rows))
        return ArcBitboard(height=self.height, width=w, planes=tuple(new_planes))

    def reflect_v(self) -> ArcBitboard:
        """Vertical reflection (flip across horizontal axis / reverse rows)."""
        new_planes = tuple(plane[::-1] for plane in self.planes)
        return ArcBitboard(height=self.height, width=self.width, planes=new_planes)

    def rotate90(self) -> ArcBitboard:
        """Rotate grid 90 degrees clockwise."""
        old_h, old_w = self.height, self.width
        new_h, new_w = old_w, old_h

        new_planes = []
        for color in range(10):
            plane = self.planes[color]
            rot_rows = [0] * new_h
            for old_y, row_mask in enumerate(plane):
                m = row_mask
                while m > 0:
                    lsb = m & -m
                    old_x = lsb.bit_length() - 1
                    # In 90 clockwise: new_y = old_x, new_x = old_h - 1 - old_y
                    new_y = old_x
                    new_x = old_h - 1 - old_y
                    rot_rows[new_y] |= 1 << new_x
                    m ^= lsb
            new_planes.append(tuple(rot_rows))

        return ArcBitboard(height=new_h, width=new_w, planes=tuple(new_planes))

    def d4_symmetries(self) -> list[ArcBitboard]:
        """Generate all 8 symmetries of the D4 dihedral group."""
        r0 = self
        r90 = r0.rotate90()
        r180 = r90.rotate90()
        r270 = r180.rotate90()
        return [
            r0,
            r90,
            r180,
            r270,
            r0.reflect_h(),
            r90.reflect_h(),
            r180.reflect_h(),
            r270.reflect_h(),
        ]

    def overlap_area(self, other: ArcBitboard, color: int) -> int:
        """Calculate bitwise pixel overlap area for a specific color."""
        if self.height != other.height or self.width != other.width:
            raise ValueError("Dimensions must match to compute overlap.")
        return sum((r1 & r2).bit_count() for r1, r2 in zip(self.planes[color], other.planes[color]))

    def total_overlap(self, other: ArcBitboard) -> int:
        """Calculate total identical color pixel count across all 10 planes."""
        if self.height != other.height or self.width != other.width:
            return 0
        return sum(
            sum((r1 & r2).bit_count() for r1, r2 in zip(p1, p2))
            for p1, p2 in zip(self.planes, other.planes)
        )
