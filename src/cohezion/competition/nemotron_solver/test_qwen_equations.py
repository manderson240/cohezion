"""Test qwen3.5 cloud model on a few equation problems."""
import csv
import ollama
import random

with open("/tmp/train.csv") as f:
    rows = list(csv.DictReader(f))

eqs = [r for r in rows if "equation" in r["prompt"].lower() or "transformation rules" in r["prompt"].lower()]

# Test on a small sample
random.seed(42)
sample = random.sample(eqs, 10)

correct = 0
for r in sample:
    prompt = r["prompt"]
    answer = r["answer"].strip()
    
    # Format prompt for the model: show ALL examples + test + request answer
    system_msg = "You are solving a reasoning puzzle. Reply with ONLY the answer, nothing else. No explanations. Just the final answer."
    user_msg = prompt + "\n\nThe numerical answer is:"
    
    try:
        response = ollama.chat(
            model="qwen3.5:cloud",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            options={"temperature": 0.1, "num_predict": 32},
        )
        pred = response["message"]["content"].strip()
        is_correct = pred == answer
        if is_correct:
            correct += 1
        print(f"A: {answer:10s} | P: {pred:10s} | {'✅' if is_correct else '❌'}")
    except Exception as e:
        print(f"Error: {e}")
        break

print(f"\nCorrect: {correct}/{len(sample)}")
