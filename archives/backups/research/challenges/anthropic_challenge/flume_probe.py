import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
sys.path.append(os.getcwd())

try:
    from anthropic_challenge.problem import Input, Tree
except ImportError:
    # Fallback or assume running from root
    pass


def simple_probe():
    print("Running Pure Python FLUME Probe...")

    # Generate data
    num_sequences = 1000
    rounds = 16

    try:
        t = Tree.generate(12)  # 4096 nodes
        print(f"Tree generated with {len(t.values)} nodes.")
        inp = Input.generate(t, 256, rounds)
    except NameError:
        print("Could not import problem.py classes. Ensure PYTHONPATH is set.")
        return

    idxs = inp.indices[:]
    vals = inp.values[:]

    history_bits = []

    for i in range(256):  # Per batch item
        c_idx = idxs[i]
        c_val = vals[i]

        seq = []
        for r in range(rounds):
            if c_idx >= len(t.values):
                c_idx = 0
            n_val = t.values[c_idx]

            # Hash logic (simplified simulation of problem.py)
            x = c_val ^ n_val
            for _ in range(4):
                x = (x + 0x12345678) & 0xFFFFFFFF
                x = (x ^ (x >> 13)) & 0xFFFFFFFF
                x = (x * 0x90ABCDEF) & 0xFFFFFFFF
                x = (x ^ (x << 17)) & 0xFFFFFFFF
            c_val = x

            # 0 if even (Left), 1 if odd (Right)
            bit = 1 if (c_val % 2 != 0) else 0
            seq.append(bit)

            if bit == 0:
                c_idx = 2 * c_idx + 1
            else:
                c_idx = 2 * c_idx + 2

            if c_idx >= len(t.values):
                c_idx = 0

        history_bits.append(seq)

    # Analysis
    total_bits = 0
    ones = 0
    transitions = [[0, 0], [0, 0]]  # [prev][curr]

    for seq in history_bits:
        total_bits += len(seq)
        ones += sum(seq)
        for i in range(len(seq) - 1):
            prev = seq[i]
            curr = seq[i + 1]
            transitions[prev][curr] += 1

    avg_val = ones / total_bits if total_bits > 0 else 0
    print(f"Average Bit Value (Target 0.5): {avg_val:.4f}")

    # Markov Probabilities
    # P(0|0) = transitions[0][0] / sum(transitions[0])
    # P(1|0) = transitions[0][1] / sum(transitions[0])

    sum_0 = sum(transitions[0])
    sum_1 = sum(transitions[1])

    p00 = transitions[0][0] / sum_0 if sum_0 > 0 else 0
    p10 = transitions[0][1] / sum_0 if sum_0 > 0 else 0

    p01 = transitions[1][0] / sum_1 if sum_1 > 0 else 0
    p11 = transitions[1][1] / sum_1 if sum_1 > 0 else 0

    print("\nTransition Probabilities (Markov Chain Order 1):")
    print(f"P(0|0)={p00:.3f}, P(1|0)={p10:.3f}")
    print(f"P(0|1)={p01:.3f}, P(1|1)={p11:.3f}")

    max_pred_0 = max(p00, p10)
    max_pred_1 = max(p01, p11)
    avg_pred = (max_pred_0 * sum_0 + max_pred_1 * sum_1) / (sum_0 + sum_1)

    print(f"Markov Predictability Score: {avg_pred:.4f}")

    if avg_pred > 0.55:
        print("RESULT: PREDICTABLE STRUCTURE FOUND (Markov)!")
    else:
        print("RESULT: NO OBVIOUS PREDICTABILITY (Random Walk)")


if __name__ == "__main__":
    simple_probe()
