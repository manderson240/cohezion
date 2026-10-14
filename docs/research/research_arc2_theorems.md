# ARC-AGI-2 Bleeding-Edge Theorem Sprint

We need answer with Python code. Need formulate 2 pure Python AutoHarness invariant functions. Need understand ARC-AGI-2? Need likely functions for grid tasks. Need return valid Python code enclosed. Need no exec/eval. Need type hints. Need implement verify_euler_characteristic(input_grid, output_grid) checking topological component invariants, and verify_d4_symmetry_preservation(grid) checking dihedral symmetry group invariants.

Need think carefully. The user asks "We are competing in ARC Prize 2026 ARC-AGI-2 (current score 31.81%, target >= 33.89% Top 10 solo). Formulate 2 pure Python AutoHarness invariant functions: (1) `verify_euler_characteristic(input_grid, output_grid)` checking topological component invariants, (2) `verify_d4_symmetry_preservation(grid)` checking dihedral symmetry group invariants. Return valid Python code enclosed in ```python ``` with type hints and no exec/eval."

Need produce code only? They ask formulate functions. Need likely include imports? Pure Python. Need type hints. Need no exec/eval. Need maybe define helper functions. Need ensure functions are useful for ARC tasks. Need infer expected behavior.

We need design invariant functions. "AutoHarness invariant functions" maybe from ARC-AGI-2? Need check topological component invariants and dihedral symmetry group invariants. Need implement robust.

Let's parse: verify_euler_characteristic(input_grid, output_grid) checking topological component invariants. In ARC grids, components of same color? Euler characteristic for binary image? Could compute for grid as graph of foreground cells? Need compare input and output? "checking topological component invariants" likely returns bool if Euler characteristic invariant preserved between input and output. Need define Euler characteristic for colored grid components. Could compute number of connected components minus number of holes? For each color? Need maybe compare multiset of Euler characteristics per color? Need decide.

verify_d4_symmetry_preservation(grid) checking dihedral symmetry group invariants. Could return bool if grid has D4 symmetry? Or compute invariants? "checking dihedral symmetry group invariants" maybe verify that grid is invariant under D4? But name "preservation" maybe check if grid has D4 symmetry? Need implement.

Need think of ARC tasks. ARC grids are 2D arrays of integers 0-9. Invariants often include number of objects, symmetry, topology. AutoHarness maybe functions that verify invariants between input and output. Need likely used in program synthesis to filter candidates. Need functions return True if invariant holds. For verify_euler_characteristic(input_grid, output_grid), should return True if Euler characteristic of input equals output? "checking topological component invariants" maybe yes. For verify_d4_symmetry_preservation(grid), maybe returns True if grid is D4 symmetric? Or if D4 symmetry group invariants preserved? It takes single grid, so likely check if grid has D4 symmetry. But "preservation" maybe check if grid's D4 symmetry invariants are consistent? Hmm.

Need formulate pure Python. Need no exec/eval. Need type hints. Could include List, Tuple, Set, etc.

Let's design robust functions.

First, Euler characteristic.

For a binary grid (foreground vs background), Euler characteristic χ = #connected components - #holes. In 2D digital topology, using 4-connectivity for foreground and 8-connectivity for background, or vice versa. For colored grids, we can compute per color? Need maybe treat each color as foreground separately, background all other colors. Then compute χ for each color. Compare multiset? But output may change colors? ARC tasks often preserve colors? Could compare per-color χ where color exists in both? Need maybe compute total Euler characteristic over all non-zero cells? Hmm.

"topological component invariants" maybe includes number of connected components and holes. Euler characteristic is components - holes. Need compare input and output. Could compute for each color and compare sorted list of χ for colors present in both? Need decide.

Maybe simpler: For each color 0-9, compute Euler characteristic of cells of that color (foreground) against all other cells (background). Then compare the multiset of χ values for colors that appear in input or output? But if output introduces new color, invariant fails? In ARC, output can introduce colors not in input? Usually output colors are subset of input plus maybe background? Actually ARC tasks can use colors in output not in input? Usually all colors in output are from input? Not necessarily? But often yes. Invariant should not be too strict. Could compare for colors present in both input and output; ignore colors only in one? But then not invariant. Hmm.

Maybe compute Euler characteristic of entire non-background as one foreground? But color changes? Need maybe use all nonzero cells as foreground. Then compare χ. That checks topology of shapes ignoring color. But "component invariants" maybe per color.

Let's search memory: ARC-AGI-2 AutoHarness? There are "invariant functions" like `verify_euler_characteristic`, `verify_d4_symmetry_preservation`. Maybe from ARC-AGI-2 benchmark? They might expect specific semantics. Need infer from names.

`verify_euler_characteristic(input_grid, output_grid)` likely checks if Euler characteristic is preserved between input and output. It might compute Euler characteristic for each connected component? Need maybe return True if input and output have same Euler characteristic. Could be for binary grids? ARC grids are colored. Need maybe convert to binary by considering non-zero as foreground. That is common.

`verify_d4_symmetry_preservation(grid)` likely checks if grid has D4 symmetry (invariant under rotations/reflections). It takes one grid, returns True if grid is symmetric under dihedral group D4. That is straightforward.

Need produce code with type hints. Need maybe include docstrings.

Let's plan Euler characteristic implementation.

Option 1: Binary Euler characteristic:
- Treat any nonzero cell as foreground, zero as background.
- Compute connected components of foreground using 4-connectivity.
- Compute holes in background using 8-connectivity? Need digital topology: For foreground 4-connected, background 8-connected; holes = number of background connected components not touching border minus 1? Actually Euler characteristic χ = C - H, where C = number of 4-connected foreground components, H = number of 8-connected background components completely enclosed by foreground? Need compute holes correctly.

In digital image, for 4-connected foreground and 8-connected background, number of holes = number of 8-connected background components not connected to image border. Because each hole is a background region completely surrounded by foreground. But if there are multiple background components inside a foreground component, each is a hole. So H = number of 8-connected background components that do not touch border. Then χ = C - H. This works for binary images.

Need handle empty grid? If no foreground, C=0, H=0? Background all connected to border if grid has border? If grid empty? Need maybe return 0. If grid all foreground, background none, H=0, C=1, χ=1. Good.

But for colored grids, if we treat nonzero as foreground, holes are zero regions enclosed. That ignores color holes of other colors. Could be okay.

Could also compute per color: For each color c, foreground = cells equal c, background = all other cells (including zero and other colors). Then compute χ_c. Compare multiset of χ_c for colors present in both? Need maybe more informative. But function name "verify_euler_characteristic" singular maybe total.

Maybe implement both? Could compute total binary Euler characteristic and compare. That is simple and likely expected.

But need "topological component invariants" maybe includes number of components and holes. Euler characteristic is one invariant. Could compare both C and H? The function name says Euler characteristic, so compare χ. But maybe also compare number of components? Hmm.

Let's design `verify_euler_characteristic(input_grid, output_grid)`:
- Compute Euler characteristic for input and output using binary foreground (nonzero).
- Return True if equal.
- Maybe also if both empty? Return True.
- Need handle grids of different dimensions? Euler characteristic can be computed regardless. If input and output shapes differ, still compare scalar.

Need implement `euler_characteristic(grid)` helper.

Need compute connected components. Use BFS/DFS. Need avoid recursion for large grids? ARC grids up to 30x30, recursion okay but use stack.

Need compute foreground components with 4-connectivity. Need compute background holes with 8-connectivity not touching border. Need be careful: background cells are zero. Need find 8-connected components of zero cells. Count those with no cell on border. That is H.

But is that always correct? Example: foreground ring of 1s enclosing zero hole. Foreground C=1. Background zero cells: hole inside (not touching border) and outside (touching border). 8-connected components: inside hole not touching border => H=1. χ=0. Good.

Example: two separate rings: C=2, H=2, χ=0. Good.

Example: solid block: C=1, H=0, χ=1.

Example: foreground with two components one ring one solid: C=2, H=1, χ=1.

Need compare.

Potential issue: If grid has no zero background (all nonzero), H=0. Good.

Need maybe use 8-connectivity for foreground and 4 for background? Digital topology requires complementary connectivities to avoid paradox. We choose 4 foreground, 8 background. That's standard.

Now D4 symmetry
