"""Simple AIMO3 solver using local Ollama models."""

import re
import polars as pl
from kaggle_evaluation.core.templates import InferenceServer


class AIMO3SimpleSolver(InferenceServer):
    """Minimal working solver that uses Ollama for math reasoning."""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.model = "qwen3-coder:30b"  # Best local model for math
        
    def setup(self):
        """Initialize Ollama client."""
        import ollama
        self.client = ollama
        print(f"Solver initialized with model: {self.model}")
    
    def predict(self, data_batch: pl.DataFrame, transforms=None) -> pl.DataFrame:
        """
        Solve math problems and return integer answers.
        
        Args:
            data_batch: Polars DataFrame with 'id' and 'problem' columns
            
        Returns:
            Polars DataFrame with 'id' and 'answer' columns
        """
        if self.client is None:
            self.setup()
        
        results = []
        
        for row in data_batch.iter_rows(named=True):
            problem_id = row['id']
            problem_text = row['problem']
            
            print(f"\nSolving problem {problem_id}:")
            print(f"Problem: {problem_text[:100]}...")
            
            try:
                answer = self.solve_problem(problem_text)
                print(f"Answer: {answer}")
            except Exception as e:
                print(f"Error solving: {e}")
                answer = 0  # Fallback
            
            results.append({'id': problem_id, 'answer': answer})
        
        return pl.DataFrame(results)
    
    def solve_problem(self, problem_text: str) -> int:
        """
        Solve a single math problem.
        
        Strategy: Use LLM to reason and extract final integer.
        """
        prompt = f"""You are solving a mathematical olympiad problem. 

Problem: {problem_text}

Think step-by-step and provide your reasoning. 
At the end, write your final answer as a single integer on its own line in this exact format:

FINAL ANSWER: <your integer>"""

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                'temperature': 0.0,  # Deterministic
                'num_predict': 2048,  # Reasonable limit
            }
        )
        
        response_text = response['response']
        
        # Extract integer from FINAL ANSWER line
        answer = self.extract_answer(response_text)
        
        return answer
    
    def extract_answer(self, text: str) -> int:
        """Extract integer answer from model response."""
        
        # Look for "FINAL ANSWER: <number>"
        match = re.search(r'FINAL ANSWER:\s*(-?\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Fallback: Look for any integer at end of text
        lines = text.strip().split('\n')
        for line in reversed(lines):
            numbers = re.findall(r'-?\d+', line)
            if numbers:
                return int(numbers[-1])
        
        # Ultimate fallback
        return 0


# For local testing
def test_on_reference():
    """Test solver on reference problems."""
    import ollama
    
    # Load reference problems
    ref_df = pl.read_csv('../aimo3_data/reference.csv')
    
    solver = AIMO3SimpleSolver()
    solver.client = ollama
    
    correct = 0
    total = len(ref_df)
    
    print(f"Testing on {total} reference problems...\n")
    
    for row in ref_df.iter_rows(named=True):
        predicted = solver.solve_problem(row['problem'])
        expected = row['answer']
        
        status = "✓" if predicted == expected else "✗"
        print(f"{status} Problem {row['id']}: Predicted={predicted}, Expected={expected}")
        
        if predicted == expected:
            correct += 1
    
    print(f"\nScore: {correct}/{total} ({100*correct/total:.1f}%)")
    return correct / total


if __name__ == '__main__':
    test_on_reference()
