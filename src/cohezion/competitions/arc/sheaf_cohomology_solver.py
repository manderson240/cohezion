r"""Sheaf Cohomology Local-to-Global Grid Gluer for ARC-AGI.

Implements Čech 1-cocycle obstruction checking:
delta^0(s)_{ij} = s_j|_{U_i \cap U_j} - s_i|_{U_i \cap U_j} = 0
Prunes local transformation hypotheses that cannot be smoothly glued into a global grid.
"""


def check_sheaf_gluing_consistency(
    local_patches: list[tuple[tuple[int, int, int, int], list[list[int]]]],
) -> bool:
    """Verifies that overlapping local grid sections agree on all intersection coordinates."""
    # Each patch is ((min_r, max_r, min_c, max_c), subgrid) where max_r, max_c are inclusive
    for i in range(len(local_patches)):
        (r1_min, r1_max, c1_min, c1_max), g1 = local_patches[i]
        for j in range(i + 1, len(local_patches)):
            (r2_min, r2_max, c2_min, c2_max), g2 = local_patches[j]

            # Compute intersection bounds
            inter_r_min = max(r1_min, r2_min)
            inter_r_max = min(r1_max, r2_max)
            inter_c_min = max(c1_min, c2_min)
            inter_c_max = min(c1_max, c2_max)

            if inter_r_min <= inter_r_max and inter_c_min <= inter_c_max:
                for r in range(inter_r_min, inter_r_max + 1):
                    for c in range(inter_c_min, inter_c_max + 1):
                        r_idx1 = r - r1_min
                        c_idx1 = c - c1_min
                        r_idx2 = r - r2_min
                        c_idx2 = c - c2_min
                        if (
                            0 <= r_idx1 < len(g1)
                            and 0 <= c_idx1 < len(g1[0])
                            and 0 <= r_idx2 < len(g2)
                            and 0 <= c_idx2 < len(g2[0])
                        ) and g1[r_idx1][c_idx1] != g2[r_idx2][c_idx2]:
                            # Non-vanishing Čech 1-cocycle obstruction!
                            return False
    return True
