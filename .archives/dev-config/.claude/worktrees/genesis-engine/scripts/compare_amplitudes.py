import logging

import quimb.tensor as qtn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Compare")


def compare():
    path = "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"
    with open(path) as f:
        qasm_str = f.read()

    logger.info("Loading circuit...")
    circ = qtn.Circuit.from_qasm(qasm_str)

    # Candidates to test
    # 1. The one that failed 0/36
    failed_str = "000111100010001010101101010100000001"
    # 2. Top candidate from Bond 128 (Big Endian)
    new_cand = "011100001000011100100100110111111110"
    # 3. Little Endian version of failed
    failed_rev = failed_str[::-1]
    # 4. Little Endian version of new
    new_rev = new_cand[::-1]

    targets = [
        ("Failed (Big)", failed_str),
        ("New (Big)", new_cand),
        ("Failed (Little)", failed_rev),
        ("New (Little)", new_rev),
    ]

    logger.info(f"Computing amplitudes for {len(targets)} strings...")
    for label, bstr in targets:
        try:
            # We use contract='auto-hq' for high quality heuristics
            # 36 qubits and 4400 gates might be tough, let's see.
            amp = circ.amplitude(bstr)
            prob = abs(amp) ** 2
            print(f"{label}: Prob {prob:.2e}")
        except Exception as e:
            print(f"{label}: Error {e}")


if __name__ == "__main__":
    compare()
