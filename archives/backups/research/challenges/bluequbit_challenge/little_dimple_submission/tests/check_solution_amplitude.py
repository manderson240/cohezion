import sys


# Add submission dir to path
sys.path.append("/home/mike-anderson/dev/cohezion/bluequbit_challenge/little_dimple_submission")
from peaked_solver import PeakedCircuitSolver


def check_prob(bitstring):
    qasm_path = "/home/mike-anderson/dev/cohezion/bluequbit_challenge/little_dimple_submission/P1_little_dimple.qasm"
    solver = PeakedCircuitSolver(qasm_path)
    solver.load_circuit()

    print(f"Computing amplitude for bitstring: {bitstring}")
    import time

    start = time.time()
    # Use auto-hq for high quality contraction path
    amp = solver.circ.amplitude(bitstring, optimize="auto-hq")
    prob = abs(amp) ** 2
    end = time.time()

    print(f"Amplitude: {amp}")
    print(f"Probability: {prob:.2e}")
    print(f"Uniform Prob (1/2^36): {1 / (2**36):.2e}")
    print(f"Ratio: {prob / (1 / (2**36)):.2f} x Uniform")
    print(f"Time: {end - start:.2f}s")
    return prob


if __name__ == "__main__":
    if len(sys.argv) > 1:
        bstr = sys.argv[1]
    else:
        # Value from solution.txt
        bstr = "011111001010001110100101001101100110"

    check_prob(bstr)

    # Also check reversed
    print("\n--- Checking REVERSED ---")
    check_prob(bstr[::-1])
