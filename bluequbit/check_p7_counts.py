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

job_id = "tUfVijYQZZ8KkVxA"
result = bq.get(job_id)

counts = result.get_counts()
sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

print(f"Total unique bitstrings: {len(counts)}")
print(f"\nTop 5 results (raw data):")
for raw, cnt in sorted_counts[:5]:
    answer = raw[::-1]
    print(f"  Raw: {raw}, Count: {cnt}, Answer: {answer}")

# Check total shots
total = sum(counts.values())
print(f"\nTotal shots: {total}")
print(f"Top probability: {sorted_counts[0][1] / total:.6f}")
