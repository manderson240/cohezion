import traceback  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402
import sympy  # noqa: E402


class SymbolicExecutor:
    """
    The 'Doer' layer's execution tool.
    Provides a sandboxed environment for symbolic and numerical computation.
    """

    def __init__(self):
        self.namespace = {
            "sympy": sympy,
            "np": np,
            "sp": sympy,
            "sqrt": sympy.sqrt,
            "exp": sympy.exp,
            "log": sympy.log,
            "sin": sympy.sin,
            "cos": sympy.cos,
            "tan": sympy.tan,
            "pi": sympy.pi,
            "I": sympy.I,
            "symbols": sympy.symbols,
            "Eq": sympy.Eq,
            "solve": sympy.solve,
            "nsolve": sympy.nsolve,
            "simplify": sympy.simplify,
            "expand": sympy.expand,
            "factor": sympy.factor,
            "limit": sympy.limit,
            "diff": sympy.diff,
            "integrate": sympy.integrate,
            "Sum": sympy.Sum,
            "Product": sympy.Product,
            "oo": sympy.oo,
            # Number Theory helpers
            "isprime": sympy.isprime,
            "primerange": sympy.primerange,
            "factorint": sympy.factorint,
            "gcd": sympy.gcd,
            "lcm": sympy.lcm,
            "mod_inverse": sympy.mod_inverse,
        }

    def execute(self, code: str) -> dict[str, Any]:
        """
        Executes a block of Python code and returns the local variables.
        """
        local_vars = {}
        # Merge global namespace into locals for the execution
        exec_globals = {**self.namespace}

        try:
            # H5 fix: a RESTRICTED __builtins__ allow-list so exec'd LLM code cannot reach
            # __import__/open/eval — CPython auto-injects the FULL builtins otherwise (the prior
            # comment was false; {**namespace} provided NO __builtins__ key). NOT a full sandbox;
            # durable fix is out-of-process (see safe_exec.py).
            from cohezion.compound.safe_exec import safe_exec_globals

            exec(code, safe_exec_globals(**exec_globals), local_vars)

            # Filter out non-serializable or internal objects
            clean_results = {}
            for k, v in local_vars.items():
                if k.startswith("_"):
                    continue
                # Convert SymPy objects to strings/floats for easier consumption
                if hasattr(v, "evalf"):
                    try:
                        clean_results[k] = float(v.evalf())
                    except (ValueError, TypeError):
                        clean_results[k] = str(v)
                else:
                    clean_results[k] = v

            return {"success": True, "results": clean_results}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def execute_command(self, command_str: str) -> dict[str, Any]:
        """
        Translates IDSL commands into executable Python/SymPy.
        Example: SOLVE(x**2 - 4 = 0, x)
        """
        command_str = command_str.strip()

        # 1. SOLVE(eq, var)
        solve_match = re.match(r"SOLVE\((.+?),\s*(.+?)\)", command_str, re.IGNORECASE)
        if solve_match:
            eq, var = solve_match.groups()
            # Convert = to Eq()
            if "=" in eq and "Eq(" not in eq:
                lhs, rhs = eq.split("=")
                eq = f"Eq({lhs.strip()}, {rhs.strip()})"
            code = f"{var} = symbols('{var}')\nresult = solve({eq}, {var})"
            return self.execute(code)

        # 2. DIVISORS(n)
        div_match = re.match(r"DIVISORS\((.+?)\)", command_str, re.IGNORECASE)
        if div_match:
            n_expr = div_match.group(1)
            code = f"""
n = {n_expr}
factors = factorint(n)
count = 1
for p, e in factors.items():
    count *= (e + 1)
result = {{"factors": factors, "count": count}}
"""
            return self.execute(code)

        # 3. SEQUENCE(formula, var, start, end)
        seq_match = re.match(
            r"SEQUENCE\((.+?),\s*(.+?),\s*(\d+),\s*(\d+)\)", command_str, re.IGNORECASE
        )
        if seq_match:
            formula, var, start, end = seq_match.groups()
            code = f"result = [{formula} for {var} in range({start}, {int(end) + 1})]"
            return self.execute(code)

        # 4. FACTOR(n)
        factor_match = re.match(r"FACTOR\((.+?)\)", command_str, re.IGNORECASE)
        if factor_match:
            n_expr = factor_match.group(1)
            return self.execute(f"result = factorint({n_expr})")

        # 5. PRIME(n)
        prime_match = re.match(r"PRIME\((.+?)\)", command_str, re.IGNORECASE)
        if prime_match:
            n_expr = prime_match.group(1)
            return self.execute(f"result = prime({n_expr})")

        # 6. MOD(a, n)
        mod_match = re.match(r"MOD\((.+?),\s*(.+?)\)", command_str, re.IGNORECASE)
        if mod_match:
            a, n = mod_match.groups()
            return self.execute(f"result = ({a}) % ({n})")

        return {"success": False, "error": f"Unknown command: {command_str}"}


import re  # noqa: E402


if __name__ == "__main__":
    executor = SymbolicExecutor()

    # Test 1: Algebra
    code1 = """
x = symbols('x')
eq = Eq(x**2 - 5*x + 6, 0)
ans = solve(eq, x)
"""
    print(f"Test 1 Results: {executor.execute(code1)}")

    # Test 2: Number Theory
    code2 = """
n = 3**3 * 11**3
divisors = factorint(n)
total_divisors = 1
for p, e in divisors.items():
    total_divisors *= (e + 1)
"""
    print(f"Test 2 Results: {executor.execute(code2)}")
