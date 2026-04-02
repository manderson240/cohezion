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

job_id = "xg1wuFcwg3xJzceI"
result = bq.get(job_id)

print(f"Job {job_id}:")
print(f"  Status: {result.run_status}")

if result.run_status == "COMPLETED":
    counts = result.get_counts()
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nTop 3 results:")
    for raw, cnt in sorted_counts[:3]:
        answer = raw[::-1]
        prob = cnt / 100000
        print(f"  Answer: {answer}")
        print(f"  Probability: {prob:.4f}")
        print(f"  {'✅' if prob > 0.002 else '⚠️'}\n")
else:
    print(f"  Still running...")
