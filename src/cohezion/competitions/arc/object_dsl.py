"""ARC Connected Component & Object Segmentation DSL Module."""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Tuple, Any

def find_objects(grid: List[List[int]], connectivity: int = 4, background: int = 0) -> List[Dict[str, Any]]:
    """Extracts connected component object masks, bounding boxes, and color attributes."""
    arr = np.array(grid)
    h, w = arr.shape
    visited = np.zeros((h, w), dtype=bool)
    objects = []

    for r in range(h):
        for c in range(w):
            color = arr[r, c]
            if color == background or visited[r, c]:
                continue
            
            # BFS flood fill
            coords = []
            queue = [(r, c)]
            visited[r, c] = True
            while queue:
                cr, cc = queue.pop(0)
                coords.append((cr, cc))
                
                neighbors = [(cr-1, cc), (cr+1, cc), (cr, cc-1), (cr, cc+1)]
                if connectivity == 8:
                    neighbors += [(cr-1, cc-1), (cr-1, cc+1), (cr+1, cc-1), (cr+1, cc+1)]
                
                for nr, nc in neighbors:
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and arr[nr, nc] == color:
                        visited[nr, nc] = True
                        queue.append((nr, nc))
            
            rows = [pt[0] for pt in coords]
            cols = [pt[1] for pt in coords]
            r_min, r_max = min(rows), max(rows)
            c_min, c_max = min(cols), max(cols)
            
            mask = [[1 if (rr, cc) in coords else 0 for cc in range(c_min, c_max + 1)] for rr in range(r_min, r_max + 1)]
            objects.append({
                "color": int(color),
                "size": len(coords),
                "coords": coords,
                "bbox": (r_min, c_min, r_max, c_max),
                "mask": mask
            })
            
    return sorted(objects, key=lambda x: x["size"], reverse=True)

def flood_fill_region(grid: List[List[int]], start_r: int, start_c: int, fill_color: int) -> List[List[int]]:
    """Performs boundary-respecting flood fill."""
    res = [row[:] for row in grid]
    h, w = len(res), len(res[0])
    target_color = res[start_r][start_c]
    if target_color == fill_color:
        return res
    
    queue = [(start_r, start_c)]
    visited = set([(start_r, start_c)])
    while queue:
        r, c = queue.pop(0)
        res[r][c] = fill_color
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and res[nr][nc] == target_color:
                visited.add((nr, nc))
                queue.append((nr, nc))
    return res
