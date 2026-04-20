import unittest
import os
import bluequbit
from solve_peaked_circuit import solve_peaked_circuit


class TestSolvePeakedCircuit(unittest.TestCase):
    def test_solve_q0_peaked(self):
        # x q[0] should flip bit 0
        qasm_content = (
            'OPENQASM 2.0; include "qelib1.inc"; qreg q[4]; creg c[4]; x q[0]; measure q -> c;'
        )
        test_file = "test_q0.qasm"
        with open(test_file, "w") as f:
            f.write(qasm_content)
        try:
            result = solve_peaked_circuit(test_file, shots=100)
            self.assertEqual(result["bitstring"], "0001")
            self.assertGreater(result["probability"], 0.9)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_solve_q3_peaked(self):
        # x q[3] should flip bit 3
        qasm_content = (
            'OPENQASM 2.0; include "qelib1.inc"; qreg q[4]; creg c[4]; x q[3]; measure q -> c;'
        )
        test_file = "test_q3.qasm"
        with open(test_file, "w") as f:
            f.write(qasm_content)
        try:
            result = solve_peaked_circuit(test_file, shots=100)
            self.assertEqual(result["bitstring"], "1000")
            self.assertGreater(result["probability"], 0.9)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == "__main__":
    unittest.main()
