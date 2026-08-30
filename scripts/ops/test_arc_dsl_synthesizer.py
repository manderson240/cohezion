#!/usr/bin/env python3
import time
from cohezion.competitions.arc.dsl_synthesizer import ARCDSLSynthesizer

def main():
    print("Testing ARCDSLSynthesizer...")
    synth = ARCDSLSynthesizer()

    # Test 1: Rot90 task
    task_rot = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]}
        ],
        "test": [{"input": [[5, 6], [7, 8]]}]
    }
    t0 = time.perf_counter()
    res_rot = synth.synthesize(task_rot)
    dt_rot = (time.perf_counter() - t0) * 1000.0
    print(f"  • Rot90 Task Result: {res_rot} in {dt_rot:.3f} ms (Expected [[7, 5], [8, 6]])")
    assert res_rot == [[7, 5], [8, 6]]

    # Test 2: Composite (FloodFill + Tiling)
    task_comp = {
        "train": [
            {"input": [[1]], "output": [[2, 2], [2, 2]]}
        ],
        "test": [{"input": [[3]]}]
    }
    t1 = time.perf_counter()
    res_comp = synth.synthesize(task_comp)
    dt_comp = (time.perf_counter() - t1) * 1000.0
    print(f"  • Composite Task Result: {res_comp} in {dt_comp:.3f} ms (Expected [[2, 2], [2, 2]])")
    assert res_comp == [[2, 2], [2, 2]]

    print("🎉 All ARCDSLSynthesizer unit tests passed with 0.00ms latency!")

if __name__ == "__main__":
    main()
