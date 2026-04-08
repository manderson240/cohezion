#!/usr/bin/env python3
"""Simple AIMO3 solver using HTTP requests to local Ollama."""

import re
import json
import requests
from typing import List, Dict, Tuple


class AIMO3Solver:
    """Minimal solver that uses Ollama HTTP API for math reasoning."""
    
    def __init__(self, model: str = "qwen3-coder:30b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        
    def solve_problem(self, problem_text: str, timeout: int = 300) -> int:
        """
        Solve a single math problem using Ollama.
        
        Args:
            problem_text: The math problem in LaTeX format
            timeout: Timeout in seconds
            
        Returns:
            Integer answer (0 if parsing fails)
        """
        prompt = f"""You are solving a mathematical olympiad problem. 

Problem: {problem_text}

Think step-by-step about the solution.
At the end, write your final answer as a single integer in this exact format:

FINAL ANSWER: <integer>

Do not include any other text after the FINAL ANSWER line."""

        try:
            response = requests.post(
                self.generate_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.0,
                        'num_predict': 4096,
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # Extract answer
            answer = self._extract_answer(response_text)
            return answer
            
        except Exception as e:
            print(f"Error solving problem: {e}")
            return 0
    
    def _extract_answer(self, text: str) -> int:
        """Extract integer answer from model response."""
        
        # Look for "FINAL ANSWER: <number>"
        match = re.search(r'FINAL ANSWER:\s*(-?\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Fallback: Look for any integer in last few lines
        lines = text.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            numbers = re.findall(r'-?\d+', line)
            if numbers:
                return int(numbers[-1])
        
        return 0
    
    def test_on_reference(self, reference_path: str = "../aimo3_data/reference.csv") -> Tuple[int, int, float]:
        """
        Test solver on reference problems.
        
        Returns:
            (correct_count, total_count, accuracy)
        """
        import csv
        
        problems = []
        with open(reference_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problems.append({
                    'id': row['id'],
                    'problem': row['problem'],
                    'expected': int(row['answer'])
                })
        
        print(f"Testing on {len(problems)} reference problems...")
        print(f"Using model: {self.model}")
        print("-" * 60)
        
        correct = 0
        results = []
        
        for i, p in enumerate(problems, 1):
            print(f"\n[{i}/{len(problems)}] Problem {p['id']}: {p['problem'][:60]}...")
            
            predicted = self.solve_problem(p['problem'])
            expected = p['expected']
            
            status = "✓" if predicted == expected else "✗"
            print(f"   {status} Predicted: {predicted}, Expected: {expected}")
            
            if predicted == expected:
                correct += 1
            
            results.append({
                'id': p['id'],
                'predicted': predicted,
                'expected': expected,
                'correct': predicted == expected
            })
        
        accuracy = correct / len(problems) * 100
        print("\n" + "=" * 60)
        print(f"RESULTS: {correct}/{len(problems)} correct ({accuracy:.1f}%)")
        print("=" * 60)
        
        return correct, len(problems), accuracy


def test_on_public():
    """Quick test on public test set (3 simple problems)."""
    solver = AIMO3Solver(model="qwen2-math:1.5b")  # Fastest model for testing
    
    test_problems = [
        ("000aaa", "What is $1-1$?", 0),
        ("111bbb", "What is $0\\times10$?", 0),
        ("222ccc", "Solve $4+x=4$ for $x$.", 0),
    ]
    
    print("Testing on public test problems (using lightweight model)...")
    print("-" * 50)
    
    for problem_id, problem, expected in test_problems:
        print(f"\n{problem_id}: {problem}")
        predicted = solver.solve_problem(problem, timeout=30)
        status = "✓" if predicted == expected else "✗"
        print(f"   {status} Answer: {predicted} (expected {expected})")


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-public":
        test_on_public()
    else:
        # Test on reference problems with better model
        solver = AIMO3Solver(model="qwen3-coder:30b")
        solver.test_on_reference()


if __name__ == '__main__':
    main()
