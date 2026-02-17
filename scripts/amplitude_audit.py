import ast
import logging
import operator
import re

import numpy as np
import quimb.tensor as qtn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AmplitudeAudit")


def _safe_parse_param(expr: str) -> float:
    """Safely parse a QASM gate parameter using AST-based evaluation."""
    expr = expr.strip()
    expr = re.sub(r"\bpi\b", str(np.pi), expr)
    if not re.match(r"^[\d\.\+\-\*/eE\s]+$", expr):
        raise ValueError(f"Unsafe QASM parameter expression: {expr!r}")

    _ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _ops:
            return float(_ops[type(node.op)](_eval_node(node.left), _eval_node(node.right)))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ops:
            return float(_ops[type(node.op)](_eval_node(node.operand)))
        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree)


def load_qasm_manual(qasm_path):
    with open(qasm_path) as f:
        lines = f.readlines()

    N = 0
    for line in lines:
        if line.startswith("qreg"):
            N = int(line.split("[")[1].split("]")[0])
            break

    circ = qtn.Circuit(N)

    for line in lines:
        line = line.strip().replace(";", "")
        if not line or line.startswith(("OPENQASM", "include", "qreg", "//")):
            continue
        if line.startswith("cz"):
            parts = line.split()[1].split(",")
            q1 = int(parts[0].split("[")[1].split("]")[0])
            q2 = int(parts[1].split("[")[1].split("]")[0])
            circ.apply_gate("CZ", q1, q2)
        elif line.startswith("u("):
            params_str = line.split("(")[1].split(")")[0]
            params = [_safe_parse_param(p) for p in params_str.split(",")]
            q_str = line.split(")")[1].strip()
            q = int(q_str.split("[")[1].split("]")[0])
            circ.apply_gate("U3", *params, q)
    return circ


def audit():
    qasm_path = "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"
    candidates = {
        "Rank1_BigE": "011110010001001111111111100101100010",
        "Rank1_LittleE": "011110010001001111111111100101100010"[::-1],
        "Old_Failed": "000111100010001010101101010100000001",
        "Marginal_Winner_BigE": "010010010001011011100101100101100010",
    }

    logger.info("Loading circuit manually...")
    circ = load_qasm_manual(qasm_path)

    print("\n--- EXACT AMPLITUDE AUDIT ---")
    for name, bstr in candidates.items():
        try:
            logger.info(f"Computing amplitude for {name}: {bstr}...")
            # We'll try auto-hq first. If it's too slow, we'll try something else.
            amp = circ.amplitude(bstr, optimize="auto-hq")
            prob = abs(amp) ** 2
            print(f"{name}: Prob = {prob:.2e} (Abs Amp = {abs(amp):.2e})")
        except Exception as e:
            logger.error(f"Failed to compute {name}: {e}")
    print("--- END AUDIT ---")


if __name__ == "__main__":
    audit()
