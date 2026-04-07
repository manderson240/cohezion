import unittest
import os
import qiskit
from analyze_local_problems import analyze_circuit

class TestAnalyzeLocalProblems(unittest.TestCase):
    def test_analyze_circuit(self):
        # Create a dummy QASM file for testing
        qasm_content = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q -> c;'
        test_file = 'test_circuit.qasm'
        with open(test_file, 'w') as f:
            f.write(qasm_content)
        
        try:
            result = analyze_circuit(test_file)
            
            self.assertEqual(result['qubits'], 2)
            # h (1), cx (1), measure q[0] (1), measure q[1] (1) = 4 gates
            self.assertEqual(result['gates'], 4)
            self.assertTrue('h' in result['gate_types'])
            self.assertTrue('cx' in result['gate_types'])
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
