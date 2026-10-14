# ARC-AGI-3 Macro-Action Planner

We need answer user asks: "In ARC-AGI-3 Interactive Agent track (Kaggle unlimited CPU quota, current 0.25), provide a robust Python BFS pathfinder function `compile_macro_path(grid, start, target, bg_color)` that returns a list of directional integers (1:Up, 2:Down, 3:Left, 4:Right) navigating around non-bg obstacles. Enclose valid Python code in ```python ```."

We need provide code only likely. Need think about requirements. ARC-AGI-3 Interactive Agent track? Need robust Python BFS pathfinder. Function compile_macro_path(grid, start, target, bg_color) returns list directional ints 1 Up, 2 Down, 3 Left, 4 Right navigating around non-bg obstacles. Need valid Python code in code block.

Need infer grid representation: likely list of lists of ints/colors. start, target likely (row, col) or maybe (x,y)? Need robust. Direction mapping: 1 Up (row-1), 2 Down (row+1), 3 Left (col-1), 4 Right (col+1). Need BFS shortest path avoiding obstacles: cells not equal bg_color? "navigating around non-bg obstacles" means obstacles are any cell whose color != bg_color. Start and target presumably bg_color? Could be not? Need handle if start/target are obstacles? Maybe allow start/target regardless? Usually path can start at start even if not bg? But target maybe non-bg? Need robust: treat start and target as traversable even if not bg? But "non-bg obstacles" implies all non-bg cells are obstacles, but start/target might be non-bg? In ARC tasks, agent moves on background; start and target likely bg. But robust: allow start and target cells even if not bg? Hmm.

Need implement BFS. Return list of ints or maybe empty list if no path. Need maybe include docstring. Need ensure no imports? Could use collections.deque.

Need consider grid boundaries. Need maybe if start==target return [].

Need maybe if start or target out of bounds return [].

Need maybe if grid empty.

Need maybe if target is non-bg obstacle? If target is non-bg, BFS would not enter it if we treat non-bg as obstacle. But target should be reachable. In ARC tasks, target might be a colored cell? Actually "navigating around non-bg obstacles" maybe target is a point on bg? Could be target cell is not obstacle? Need decide. The prompt says "navigating around non-bg obstacles" meaning obstacles are non-bg. So target likely bg. But robust pathfinder could allow target even if non-bg by treating it as traversable. Similarly start. But if start is non-bg, we start there. I'd implement: traversable if cell == bg_color or cell == start or cell == target? But if target is non-bg, we need allow it. However if there are other non-bg cells same color as target, they would be obstacles. That's fine. But if start/target are non-bg and we allow them, path might go through them only at endpoints. That seems robust.

But careful: if start or target are tuples, comparing cell value to start/target? cell value is color int, start is tuple. Need compare coordinates. So traversable check: if (r,c) == start or (r,c) == target: True else grid[r][c] == bg_color. That allows endpoints regardless of color. But if start/target are not bg, they are not obstacles. Good.

Need BFS from start to target. Use queue of (r,c). Keep visited set or 2D bool. Keep parent dict mapping child -> (parent, direction). Direction from parent to child. BFS explores neighbors in order maybe Up, Down, Left, Right corresponding 1,2,3,4. Need return path directions. Reconstruct from target back to start using parent dict.

Need handle if start==target: return [].

Need maybe if grid rows not rectangular? assume rectangular.

Need maybe if start/target are lists? Convert to tuple.

Need maybe if target is not reachable: return [] or None? Prompt says returns list. So return [] if no path.

Need maybe if start or target out of bounds: return [].

Need maybe if grid is None: return [].

Need maybe if bg_color is None? Not likely.

Need maybe if there are multiple bg colors? No.

Need maybe if grid values are not ints? Could be strings? But bg_color likely int. Use equality.

Need maybe if start/target coordinates are (x,y) with x column? In ARC, usually row, col. Direction mapping given Up/Down/Left/Right implies row/col. We'll assume start=(row, col). Could mention in docstring.

Need maybe "Kaggle unlimited CPU quota, current 0.25" irrelevant.

Need produce code block with python. Could include type hints. Need ensure valid Python.

Let's craft robust function:

```python
from collections import deque

def compile_macro_path(grid, start, target, bg_color):
    """
    BFS shortest path on grid avoiding non-bg obstacles.
    grid: 2D list of colors
    start: (row, col)
    target: (row, col)
    bg_color: background color
    Returns list of ints: 1 Up, 2 Down, 3 Left, 4 Right.
    """
    if not grid or not grid[0]:
        return []
    rows = len(grid)
    cols = len(grid[0])
    start = tuple(start)
    target = tuple(target)
    sr, sc = start
    tr, tc = target
    if not (0 <= sr < rows and 0 <= sc < cols):
        return []
    if not (0 <= tr < rows and 0 <= tc < cols):
        return []
    if start == target:
        return []
    
    # Directions: (dr, dc, code)
    dirs = [(-1, 0, 1), (1, 0, 2), (0, -1, 3), (0, 1, 4)]
    
    q = deque([start])
    visited = {start}
    parent = {}
    
    while q:
        r, c = q.popleft()
        if (r, c) == target:
            # reconstruct path
            path = []
            cur = target
            while cur != start:
                prev, d = parent[cur]
                path.append(d)
                cur = prev
            path.reverse()
            return path
        
        for dr, dc, d in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                nxt = (nr, nc)
                if nxt in visited:
                    continue
                # traversable if bg or endpoint
                if nxt == target or grid[nr][nc] == bg_color:
                    visited.add(nxt)
                    parent[nxt] = ((r, c), d)
                    q.append(nxt)
    
    return []
```

Need consider if start is non-bg and we don't explicitly allow start in traversable check because we start there. That's fine. But if start is non-bg, we don't need to check. However if start is non-bg and we later might try to re-enter start? Not needed. But if start is non-bg and we mark visited, okay.

But what if start is non-bg and target is bg, path might need to go through start? Already there. Fine.

Potential issue: if start is non-bg and we don't allow other non-bg cells, but start is visited. Good.

Potential issue: if target is non-bg, we allow it via `nxt == target`. Good.

Potential issue: if start is non-bg and target is same as start? handled.

Potential issue: if grid has non-rectangular rows? Could use cols = len(grid[0]) but some rows shorter. Could cause index error. Could compute max cols? But ARC grids are rectangular. Fine.

Potential issue: if start or target are not tuples but lists, tuple conversion works.

Potential issue: if grid values are e.g. numpy ints, equality works.

Potential issue: if bg_color is not comparable? no.

Need maybe include `from collections import deque` inside code block. That's fine.

Could also implement without deque using list as queue for simplicity, but deque is efficient.

Need maybe mention "robust" maybe handle if start/target are out of bounds, no path, etc.

Need maybe if grid is empty list or None. We check `if not grid or not grid[0]: return []`. But if grid is None, `not grid` True, returns. Good.

Need maybe if grid[0] is empty list, `not grid[0]` True, returns. Good.

Need maybe if start or target are not valid indices, return [].

Need maybe if target is non-bg but there is a non-bg obstacle of same color? We allow only target coordinate, not all same color. That's correct.

Need maybe if start is non-bg and there is another non-bg cell same color? We don't allow it. Good.

Need maybe if start is non-bg and we want to allow start as traversable for potential path? Not needed.

But there is subtle: if start is non-bg and we start there, but if we later need to move back to start? BFS visited prevents cycles, so no need.
