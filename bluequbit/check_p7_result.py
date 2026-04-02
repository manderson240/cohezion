import bluequbit
import os

cohezion_root = "/home/mike-anderson/dev/cohezion"
api_token = None
with open(os.path.join(cohezion_root, ".env"), "r") as f:
    for line in f:
        if "BLUEQUBIT_API_TOKEN" in line:
            api_token = line.split("=")[1].strip()
            break

bq = bluequbit.init(api_token)

# Check the result from the running job
job_id = "tUfVijYQZZ8KkVxA"
print(f"Checking job {job_id}...")

result = bq.get(job_id)
print(f"Result: {result}")

if hasattr(result, "get_counts"):
    counts = result.get_counts()
    top = counts.most_common(1)[0]
    raw = top[0]
    answer = raw[::-1]
    prob = top[1] / 100000
    
    print(f"\nJob ID: {job_id}")
    print(f"Raw bitstring: {raw}")
    print(f"Answer (reversed): {answer}")
    print(f"Probability: {prob:.4f}")
    print(f"Length: {len(answer)} bits")
