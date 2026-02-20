import time
import timeit

import numpy as np


def test_workload():
    # Small 12D manifold calculation
    x = np.random.rand(1000, 12)
    return np.mean(x, axis=0)


def benchmark():
    print("--- Temporal Precision Benchmark ---")

    # 1. time.time()
    t1 = time.time()
    for _ in range(100):
        test_workload()
    t2 = time.time()
    print(f"time.time(): {(t2 - t1) / 100:.8f} s average")

    # 2. time.perf_counter()
    p1 = time.perf_counter()
    for _ in range(100):
        test_workload()
    p2 = time.perf_counter()
    print(f"time.perf_counter(): {(p2 - p1) / 100:.8f} s average")

    # 3. timeit
    timer = timeit.Timer(test_workload)
    t_timeit = timer.timeit(number=100)
    print(f"timeit (100 runs): {t_timeit / 100:.8f} s average")


if __name__ == "__main__":
    benchmark()
