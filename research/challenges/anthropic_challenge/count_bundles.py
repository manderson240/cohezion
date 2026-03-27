from optimizer import KernelConfig, OptimizedKernelBuilder
from problem import HASH_STAGES


def count_bundles():
    builder = OptimizedKernelBuilder(KernelConfig(smart_load_depth=4, crown_depth=5))
    h, n, b, r = 10, 16, 256, 1
    instrs = builder.build_kernel(h, n, b, r, HASH_STAGES)

    print(f"Total Bundles for 1 Round, 256 Items: {len(instrs)}")
    # Total vector-rounds = 256 / 8 = 32
    print(f"Bundles per Vector-Round (Approx): {len(instrs) / 32:.2f}")


if __name__ == "__main__":
    count_bundles()
