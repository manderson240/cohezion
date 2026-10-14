# SKILL: AUTOHARNESS_ZERO_LATENCY_INVARIANT_COMPILER_PRIME

## DOMAIN EXPERTISE
Zero-cost deterministic AST/bytecode compilation and domain invariant verification for agentic execution pipelines and competitive ML submissions without runtime LLM overhead.

## KEY TEXTS & CONCEPTS
- Zero-Latency Code Verification: Replacing runtime LLM self-checks with deterministic Python compile() and ast.NodeVisitor traversals with 0 ms latency
- Declarative Invariant Registration: Abstract Factory pattern binding domain rules (MonotonicAttemptInvariant, SoftKolmogorovMonotonicityInvariant, TautomerCanonicalInChIKeyInvariant, ZobristCycleInvariant) to competition manifests
- Universal Preflight Gate: Blocking invalid candidate submissions before cloud or Kaggle dispatch with explicit violation diagnostics and remediation hints
- Two-Party Separation Enforcement: Coupling AST verification directly with HMAC cryptographic authority assertions to prevent self-certification regressions

## INSTRUCTION
1. **Define a domain invariant subclassing BaseInvariant and implement verify_ast(tree, raw_code, context)**
```python
res = AutoHarnessInvariantFactory.compile_and_verify(code_path, competition_id)
if res.has_critical_violations or not res.bytecode_valid:
    raise RuntimeError(f'AutoHarness invariant failure: {res.violations}')
```

## VERSION
v1.0

## SEE ALSO
- KAGGLE_COMPETITIVE_EVALUATION_PRIME
- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME
