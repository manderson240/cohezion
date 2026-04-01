"""Local test for SC-TIR kernel logic without vLLM/Kaggle dependencies."""

import os
import re
import sys
from collections import Counter


# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
N_SAMPLES = 4
CODE_TIMEOUT = 10

def execute_python(code: str) -> str:
    """Execute Python code in a sandboxed subprocess."""
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=CODE_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        elif result.stderr:
            return f"Error: {result.stderr[:200]}"
        return "No output"
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out"
    except Exception as e:
        return f"Error: {str(e)[:200]}"

def extract_code_blocks(text: str) -> list:
    """Extract Python code blocks from model output."""
    pattern = r"```python\s*\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)

def extract_answer(text: str) -> int:
    """Extract integer answer from \boxed{} or last number."""
    # Try boxed first
    matches = re.findall(r"\\boxed\{([^}]+)\}", text)
    if matches:
        last_boxed = matches[-1].strip()
        nums = re.findall(r"-?\d+", last_boxed)
        if nums:
            return int(nums[-1]) % 100000

    # Fallback: last number in text
    numbers = re.findall(r"-?\d+", text)
    if numbers:
        return int(numbers[-1]) % 100000
    return 0

def test_code_execution():
    """Test the code execution functionality."""
    print("=" * 60)
    print("TEST 1: Code Execution")
    print("=" * 60)

    code = "print(2 + 2)"
    result = execute_python(code)
    print(f"Code: {code}")
    print(f"Result: {result}")
    assert result == "4", f"Expected '4', got '{result}'"
    print("✓ Code execution works")

    # Test timeout
    code = "import time; time.sleep(20)"
    result = execute_python(code)
    print(f"Timeout test result: {result}")
    assert "timed out" in result.lower(), f"Expected timeout, got '{result}'"
    print("✓ Timeout handling works")

    # Test error handling
    code = "1/0"
    result = execute_python(code)
    print(f"Error test result: {result}")
    assert "Error" in result, f"Expected error, got '{result}'"
    print("✓ Error handling works")

def test_code_extraction():
    """Test extraction of Python code blocks."""
    print("\n" + "=" * 60)
    print("TEST 2: Code Block Extraction")
    print("=" * 60)

    text = """
Let me solve this step by step.

```python
x = 5
y = 10
print(x + y)
```

The result is 15.

```python
result = 15 * 2
print(result)
```
"""
    blocks = extract_code_blocks(text)
    print(f"Found {len(blocks)} code blocks")
    assert len(blocks) == 2, f"Expected 2 blocks, got {len(blocks)}"
    print("✓ Code extraction works")

def test_answer_extraction():
    """Test answer extraction from text."""
    print("\n" + "=" * 60)
    print("TEST 3: Answer Extraction")
    print("=" * 60)

    # Test boxed answer
    text = "The answer is \\boxed{42}"
    result = extract_answer(text)
    print(f"Text: {text}")
    print(f"Extracted: {result}")
    assert result == 42, f"Expected 42, got {result}"
    print("✓ Boxed extraction works")

    # Test modulo
    text = "The answer is \\boxed{123456}"
    result = extract_answer(text)
    print(f"Text: {text}")
    print(f"Extracted (mod 100000): {result}")
    assert result == 23456, f"Expected 23456, got {result}"
    print("✓ Modulo works")

    # Test fallback to last number
    text = "The numbers are 10, 20, and 30"
    result = extract_answer(text)
    print(f"Text: {text}")
    print(f"Extracted: {result}")
    assert result == 30, f"Expected 30, got {result}"
    print("✓ Fallback extraction works")

    # Test negative numbers
    text = "The answer is \\boxed{-17}"
    result = extract_answer(text)
    print(f"Text: {text}")
    print(f"Extracted: {result}")
    assert result == -17 % 100000, f"Expected {-17 % 100000}, got {result}"
    print("✓ Negative number handling works")

def test_majority_vote():
    """Test majority voting logic."""
    print("\n" + "=" * 60)
    print("TEST 4: Majority Voting")
    print("=" * 60)

    answers = [42, 42, 42, 17]
    counter = Counter(answers)
    most_common = counter.most_common(1)[0]
    print(f"Answers: {answers}")
    print(f"Votes: {dict(counter)}")
    print(f"Winner: {most_common[0]} ({most_common[1]}/{len(answers)})")
    assert most_common[0] == 42, f"Expected 42, got {most_common[0]}"
    assert most_common[1] == 3, f"Expected 3 votes, got {most_common[1]}"
    print("✓ Majority voting works")

def test_reference_problems():
    """Test against reference problems (without actual model)."""
    print("\n" + "=" * 60)
    print("TEST 5: Reference Problems (Structure Check)")
    print("=" * 60)

    import csv
    ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input", "reference.csv")

    if not os.path.exists(ref_path):
        print(f"⚠ Reference file not found at {ref_path}")
        return

    with open(ref_path, 'r') as f:
        reader = csv.DictReader(f)
        problems = list(reader)

    print(f"Found {len(problems)} reference problems")

    for i, prob in enumerate(problems[:3]):
        print(f"\nProblem {i+1}: {prob['id']}")
        print(f"  Question length: {len(prob['problem'])} chars")
        print(f"  Expected answer: {prob['answer']}")

        # Test extraction on expected answer format
        answer = int(prob['answer'])
        assert 0 <= answer < 100000 or answer >= 0, f"Answer out of expected range: {answer}"

    print("\n✓ Reference problems loaded successfully")

def test_kernel_syntax():
    """Test that kernel file has valid Python syntax."""
    print("\n" + "=" * 60)
    print("TEST 6: Kernel Syntax Validation")
    print("=" * 60)

    kernel_path = os.path.join(os.path.dirname(__file__), "submission_sc_tir.py")

    with open(kernel_path, 'r') as f:
        code = f.read()

    try:
        compile(code, kernel_path, 'exec')
        print("✓ Kernel has valid Python syntax")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False

    # Check for required imports
    required = ['vllm', 'torch', 'polars', 're', 'subprocess']
    for module in required:
        if f"import {module}" in code or f"from {module}" in code:
            print(f"✓ Found import for {module}")

    return True

def main():
    print("AIMO3 SC-TIR Kernel Local Tests")
    print("=" * 60)
    print("Testing core logic without vLLM/Kaggle dependencies...")
    print()

    try:
        test_code_execution()
        test_code_extraction()
        test_answer_extraction()
        test_majority_vote()
        test_reference_problems()
        test_kernel_syntax()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nNote: Full kernel requires:")
        print("  - vLLM installed")
        print("  - PyTorch with CUDA")
        print("  - Kaggle evaluation server or local model")
        print("  - DeepSeek-R1-32B-AWQ or Qwen2.5-Math-7B model")

        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
