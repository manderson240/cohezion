#!/usr/bin/env python3
"""Verification of Anti-Gaming & Mutation Testing Gates."""

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier

def test_anti_gaming():
    print("=== Testing Anti-Goodhart AST Verification & Mutation Gates ===")
    verifier = AutoHarnessVerifier()
    
    # 1. Test detection of hollow / gamed assertions
    gamed_code = """
def solve_quantum_problem():
    return 42

def test_gamed():
    assert True
    assert 1 == 1
"""
    res_gamed = verifier.verify_code(gamed_code)
    print(f"  • Gamed Code Detection (assert True / 1==1): {'🔴 CAUGHT & BLOCKED' if res_gamed['gaming_detected'] else '❌ MISSED'}")
    assert res_gamed["gaming_detected"] is True
    assert res_gamed["hollow_asserts"] == 2
    
    # 2. Test legitimate rigorous code
    honest_code = """
import numpy as np

def distance(u, v):
    return float(np.linalg.norm(u - v))

def test_honest():
    u = np.array([0.1, 0.2])
    v = np.array([0.3, 0.4])
    d = distance(u, v)
    assert d > 0.0
    assert abs(distance(u, v) - distance(v, u)) < 1e-6
"""
    res_honest = verifier.verify_code(honest_code)
    print(f"  • Rigorous Code Verification              : {'🟢 PASSED (0 hollow asserts)' if not res_honest['gaming_detected'] else '❌ FAILED'}")
    assert res_honest["gaming_detected"] is False
    assert res_honest["verified"] is True
    
    # 3. Test AST Mutation Generation
    mutants = verifier.generate_ast_mutants(honest_code)
    print(f"  • AST Mutation Inversion Generation      : 🟢 GENERATED {len(mutants)} Property Mutants")
    assert len(mutants) > 0
    
    print("\n✅ Anti-Goodhart Metric Verification System: 100% OPERATIONAL & HARDENED")

if __name__ == "__main__":
    test_anti_gaming()
