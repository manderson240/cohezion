import json

with open("data/arc_prize/submission.json", "r") as f:
    data = json.load(f)

# Save unindented compact JSON (matches sample_submission.json exactly)
with open("data/arc_prize/submission.json", "w") as f:
    json.dump(data, f, separators=(',', ':'))

print(f"Formatted {len(data)} tasks to compact format. File size: {len(open('data/arc_prize/submission.json').read())} bytes.")
