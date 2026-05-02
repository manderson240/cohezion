---
name: math-command-prime
description: "This skill establishes a unified Internal Domain Specific Language (IDSL) for mathematical reasoning swarms. It abstracts complex SymPy/NumPy code generation into a standard set of \"Math Commands\" that LLM specialists use to ensure deterministic execution without needing to know low-level library syntax."
---

# SKILL: MATH_COMMAND_PRIME

## DOMAIN EXPERTISE
This skill establishes a unified Internal Domain Specific Language (IDSL) for mathematical reasoning swarms. It abstracts complex SymPy/NumPy code generation into a standard set of "Math Commands" that LLM specialists use to ensure deterministic execution without needing to know low-level library syntax.

## KEY TEXTS & CONCEPTS
- **Command Abstraction**: Using high-level commands like `SOLVE()`, `DIVISORS()`, and `SIMULATE()` to bridge the gap between LLM reasoning and symbolic execution.
- **State Persistence**: Maintaining a `SymbolicState` across reasoning steps so that variables defined in one command are available in the next.
- **Fail-Safe Translation**: Automatically translating LLM-generated math-speak into valid, sandboxed Python.

## INSTRUCTION
Specialists should be instructed to use the following command format:
1. **SOLVE(equation, variable)**: Solves algebraic equations.
   - *Example*: `SOLVE(x**2 - 5*x + 6 = 0, x)` -> `[2, 3]`
2. **DIVISORS(n)**: Returns prime factorization and divisor count.
   - *Example*: `DIVISORS(3**3 * 11**3)` -> `{"factors": {3:3, 11:3}, "count": 16}`
3. **SEQUENCE(formula, var, start, end)**: Generates and analyzes mathematical sequences.
   - *Example*: `SEQUENCE(2*n + 1, n, 1, 10)` -> `[3, 5, ..., 21]`
4. **FACTOR(n)**: Returns prime factorization.
   - *Example*: `FACTOR(100)` -> `{2: 2, 5: 2}`
5. **PRIME(n)**: Returns the n-th prime number.
   - *Example*: `PRIME(1)` -> `2`
6. **MOD(a, n)**: Calculates modular remainder.
   - *Example*: `MOD(10, 3)` -> `1`
7. **INTEGRATE(expression, variable)**: Performs symbolic integration.

## VERSION
v0.1

## SEE ALSO
- `MATH_REASONING_SWARM_PRIME`
- `SYMBOLIC_EXECUTION_PRIME`
