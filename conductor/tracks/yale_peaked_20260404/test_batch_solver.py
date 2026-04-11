import unittest
import os
import time
from batch_solver import BatchSolver


class TestBatchSolver(unittest.TestCase):
    def test_batch_solve(self):
        # Create 2 dummy QASM files
        qasm1 = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[0]; measure q -> c;'
        qasm2 = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[1]; measure q -> c;'

        with open("test1.qasm", "w") as f:
            f.write(qasm1)
        with open("test2.qasm", "w") as f:
            f.write(qasm2)

        try:
            problems = {"P1": "test1.qasm", "P2": "test2.qasm"}

            solver = BatchSolver()
            results = solver.solve_all(problems, shots=100)

            self.assertEqual(len(results), 2)
            self.assertIn("P1", results)
            self.assertIn("P2", results)

            # Check bitstrings (with reversal logic verified in single solver)
            # P1 (x q0): BlueQubit 10 -> Reverse 01
            # P2 (x q1): BlueQubit 01 -> Reverse 10
            self.assertEqual(results["P1"]["bitstring"], "01")
            self.assertEqual(results["P2"]["bitstring"], "10")

        finally:
            if os.path.exists("test1.qasm"):
                os.remove("test1.qasm")
            if os.path.exists("test2.qasm"):
                os.remove("test2.qasm")


if __name__ == "__main__":
    unittest.main()
