from base_specialist import BaseSpecialist
from math_parser import MathParser


def diagnose():
    parser = MathParser()
    problem = "Let $n = 3^3 \\cdot 11^3$. Find the number of distinct positive divisors of $n$."
    print(f"Problem: {problem}")
    
    # Use NumberTheorist with default model
    specialist = BaseSpecialist("NumberTheorist")
    print(f"Model: {specialist.model_name}")
    
    response = specialist.solve(problem)
    print("\n--- Model Response ---")
    print(response)
    print("--- End Response ---\n")
    
    answer = specialist.extract_answer(response)
    print(f"Extracted Answer: {answer}")
    print(f"Expected Answer: 16")

if __name__ == "__main__":
    diagnose()
