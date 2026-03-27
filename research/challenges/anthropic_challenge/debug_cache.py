import random

from optimizer import KernelConfig, OptimizedKernelBuilder
from perf_takehome import (
    N_CORES,
    Input,
    Machine,
    Tree,
    build_mem_image,
)


def debug_trace():
    forest_height = 10
    rounds = 1
    batch_size = 32
    seed = 123

    random.seed(seed)
    forest = Tree.generate(forest_height)
    print(f"Forest[0]: {forest.values[0]}")

    inp = Input.generate(forest, batch_size, rounds)
    mem = build_mem_image(forest, inp)

    kb = OptimizedKernelBuilder(KernelConfig(crown_depth=1, disable_hash_opt=True))
    instrs = kb.build_kernel(
        forest.height,
        len(forest.values),
        len(inp.indices),
        rounds,
        [(("+", 0, "+", "<<", 0))],
    )

    value_trace = {}

    class DebugInfo:
        def __init__(self, scratch_map):
            self.scratch_map = scratch_map

    machine = Machine(
        mem,
        instrs,
        DebugInfo(kb.scratch_names),
        n_cores=N_CORES,
        value_trace=value_trace,
    )
    machine.prints = True

    # Run
    machine.run()

    # Check Result
    inp_values_p = 6  # Val base? No, dynamic.
    # We need to find input values dest.
    # In perf_takehome: inp_values_p = load_list offsets...
    # Just print scratch trace
    print("Execution Finished")


debug_trace()
