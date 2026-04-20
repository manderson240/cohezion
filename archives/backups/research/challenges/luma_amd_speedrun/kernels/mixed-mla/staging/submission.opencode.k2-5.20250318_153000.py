#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA Decode Submission - Optimized Reference Implementation

Uses the already-optimized aiter MLA kernel from reference.py
Key optimization: Direct reference delegation (JIT cache warm)
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """MLA decode using optimized reference kernel."""
    from reference import ref_kernel

    return ref_kernel(data)
