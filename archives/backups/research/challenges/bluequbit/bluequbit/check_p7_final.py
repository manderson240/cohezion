import os

import bluequbit


cohezion_root = "/home/mike-anderson/dev/cohezion"
api_token = None
with open(os.path.join(cohezion_root, ".env")) as f:
    for line in f:
        if "BLUEQUBIT_API_TOKEN" in line:
            api_token = line.split("=")[1].strip()
            break

bq = bluequbit.init(api_token)

job_id = "tUfVijYQZZ8KkVxA"
result = bq.get(job_id)

print(f"Job {job_id}:")
print(f"  Status: {result.run_status}")
print(f"  Result type: {type(result)}")

counts = result.get_counts()
print(f"  Counts type: {type(counts)}")

if isinstance(counts, dict):
    # Sort by count
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 3 results:")
    for raw, cnt in sorted_counts[:3]:
        answer = raw[::-1]
        prob = cnt / 100000
        print(f"    Raw: {raw}")
        print(f"    Answer: {answer}")
        print(f"    Probability: {prob:.4f}")
        print(f"    {'✅' if prob > 0.002 else '⚠️'}\n")
