#!/usr/bin/env python3
"""Test streaming fix for Ollama timeout."""

import time

from base_specialist import BaseSpecialist


def test_simple_problem():
    specialist = BaseSpecialist('Algebraist', model_name='qwen2-math:1.5b', timeout=600)
    
    t0 = time.time()
    result = specialist.solve('What is 5+7?')
    elapsed = time.time() - t0
    
    print(f"Time: {elapsed:.1f}s")
    print(f"Result: {result[:100]}...")
    answer = specialist.extract_answer(result)
    print(f"Extracted: {answer}")
    print(f"Expected: 12")
    print(f"PASS" if answer == 12 else "FAIL")

if __name__ == "__main__":
    test_simple_problem()
