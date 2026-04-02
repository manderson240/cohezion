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

# Check all P7 jobs
job_ids = ["tUfVijYQZZ8KkVxA"]

for job_id in job_ids:
    try:
        result = bq.get(job_id)
        print(f"\nJob {job_id}:")
        print(f"  Status: {result.run_status}")
        
        if hasattr(result, 'get_counts'):
            counts = result.get_counts()
            top = counts.most_common(3)
            print(f"  Top results:")
            for raw, cnt in top:
                answer = raw[::-1]
                prob = cnt / 100000
                print(f"    {answer} (prob: {prob:.4f})")
    except Exception as e:
        print(f"Job {job_id}: {e}")
