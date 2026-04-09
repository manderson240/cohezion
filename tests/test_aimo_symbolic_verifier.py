import unittest
import sys
import os

# Ensure we can import from the kernel directory
sys.path.append(os.path.join(os.getcwd(), "sandbox/aimo/kaggle_kernel"))

# Note: We need to import the class directly from the file if possible, 
# but for now we'll test the one we just updated in submission_transformers.py
import submission_transformers

class TestSymbolicVerifier(unittest.TestCase):
    def setUp(self):
        # The class needs sympy, np to be in namespace
        # In the actual script it uses global imports.
        pass

    def test_basic_arithmetic(self):
        verifier = submission_transformers.SymbolicVerifier()
        code = "```python\nx = 2 + 2\n```"
        self.assertTrue(verifier.verify(code, 4))
        self.assertFalse(verifier.verify(code, 5))

    def test_sympy_algebra(self):
        verifier = submission_transformers.SymbolicVerifier()
        code = """```python
import sympy
x = sympy.symbols('x')
res = sympy.solve(x**2 - 9, x)
# res is [-3, 3]
ans = max(res)
```"""
        self.assertTrue(verifier.verify(code, 3))

    def test_modular_arithmetic(self):
        verifier = submission_transformers.SymbolicVerifier()
        code = "```python\nans = (15 + 7) % 11\n```"
        self.assertTrue(verifier.verify(code, 0))

    def test_syntax_error_handling(self):
        verifier = submission_transformers.SymbolicVerifier()
        code = "```python\nthis is not valid python\n```"
        # Should return False instead of crashing
        self.assertFalse(verifier.verify(code, 1))

if __name__ == "__main__":
    unittest.main()
