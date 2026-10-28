from typing import Any


class SymbolicExecutor:
    """
    The 'Doer' layer's execution tool.
    Provides a sandboxed environment for symbolic and numerical computation.
    """

    # name -> "module" or "module:attr". Strings, not objects: code now runs OUT OF PROCESS
    # (sandboxed_exec, H5) and the child imports each binding itself.
    BINDINGS: dict[str, str] = {
        "sympy": "sympy",
        "np": "numpy",
        "sp": "sympy",
        **{
            name: f"sympy:{name}"
            for name in (
                "sqrt", "exp", "log", "sin", "cos", "tan", "pi", "I", "symbols", "Eq", "solve",
                "nsolve", "simplify", "expand", "factor", "limit", "diff", "integrate", "Sum",
                "Product", "oo",
                # Number Theory helpers
                "isprime", "primerange", "factorint", "gcd", "lcm", "mod_inverse",
            )
        },
    }  # fmt: skip

    def __init__(self, timeout_s: float = 30.0):
        self.timeout_s = timeout_s

    def execute(self, code: str) -> dict[str, Any]:
        """Execute ``code`` OUT OF PROCESS and return its top-level variables.

        H5 durable fix: the previous in-process ``exec`` under ``safe_exec_globals`` was escapable
        (``collections._sys.modules['os']``). ``run_untrusted`` applies kernel rlimits (no fork,
        no file/socket open) and fails closed. Values come back JSON-coerced: sympy integers as
        int, other exact-evaluable expressions as float, the rest as str. Callables are omitted.
        """
        from cohezion.compound.sandboxed_exec import is_plain_json, run_untrusted

        r = run_untrusted(code, collect=True, bindings=self.BINDINGS, timeout_s=self.timeout_s)
        if r.ok:
            # Post-exec output is UNTRUSTED (the child can forge its own result line): accept only
            # the schema `collect=True` produces -- a bounded dict[str, plain-JSON].
            if r.value is None:
                return {"success": True, "results": {}}
            if isinstance(r.value, dict) and is_plain_json(r.value):
                return {"success": True, "results": r.value}
            return {
                "success": False,
                "error": "sandbox result failed validation",
                "traceback": "sandbox result failed validation",
            }
        # aimo_reasoning feeds `traceback` into its repair prompt; it is the child's real
        # traceback (untrusted frames carry source lines via linecache), not the one-line error.
        # Both are untrusted text; cap the size.
        return {
            "success": False,
            "error": r.error[:2000],
            "traceback": (r.traceback or r.error)[:4000],
        }

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


import re


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
