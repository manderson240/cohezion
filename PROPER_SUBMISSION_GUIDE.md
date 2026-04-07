# Proper Popcorn CLI Usage (From Official Docs)

## Installation Verified
```
CLI ID: 591b3cd1-363d-4b9d-a8da-3cf91c346126
Status: ✅ Registered
```

## Submission File Requirements

### 1. Must be SINGLE Python file
```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

def custom_kernel(data):
    # Your implementation
    return output
```

### 2. File Directives (optional but recommended)
- `#!POPCORN leaderboard <name>` - Auto-detects leaderboard
- `#!POPCORN gpu <type>` - Auto-detects GPU

## Correct Submission Flow

### Step 1: Test Mode (Verify Correctness)
```bash
popcorn submit submission.py \
  --mode test \
  --gpu MI355X \
  --leaderboard amd-mixed-mla \
  --no-tui
```
**Result**: Test passed/failed

### Step 2: Benchmark Mode (Get Timing)
```bash
popcorn submit submission.py \
  --mode benchmark \
  --gpu MI355X \
  --leaderboard amd-mixed-mla \
  --no-tui
```
**Result**: Timing data (unofficial)

### Step 3: Leaderboard Mode (Official Score)
```bash
popcorn submit submission.py \
  --mode leaderboard \
  --gpu MI355X \
  --leaderboard amd-mixed-mla \
  --no-tui \
  --output results.json
```
**Result**: Runs full pipeline (test → benchmark → leaderboard)

## Capturing Timing Data

### Method 1: List Submissions (Recommended)
```bash
popcorn submissions list --leaderboard amd-mixed-mla
```

Output includes Score column:
```
ID       Leaderboard    File        Time              GPU(s)   Status  Score
--------------------------------------------------------------------------------
720690   amd-mixed-mla  sub.py      2026-04-04T...    MI355X   done    45.2µs
```

**Note**: Score shows `-` initially, updates after leaderboard run completes.

### Method 2: Save to JSON
```bash
popcorn submit submission.py --mode leaderboard --output results.json ...
```
Check `results.json` for timing data.

### Method 3: Show Specific Submission
```bash
popcorn submissions show 720690
```
Shows full details including runs.

## Full Pipeline Status Check

A complete leaderboard submission shows:
```
Runs:
  - test on MI355X: passed (score: -)
  - benchmark on MI355X: passed (score: -)
  - leaderboard on MI355X: passed (score: -)
```

Only then is the Score column populated with actual timing.

## Rate Limits

- **1 submission per hour** per leaderboard
- Test/benchmark modes: 10/hour per leaderboard
- Leaderboard mode: 1/hour per leaderboard

## Troubleshooting

### "Rate limit exceeded"
Wait for next available slot (check with `submissions list`)

### "Your code contains work on another stream"
Code is using multiple CUDA streams. Simplify to single-stream.

### Score shows `-`
Leaderboard run hasn't completed yet. Wait and check again.

### Authentication issues
```bash
popcorn reregister discord  # or github
```

## Our Current Approach Issues

1. ❌ Submitting complex load_inline code causing stream errors
2. ❌ Not waiting for complete pipeline before checking score
3. ❌ Not using `--output` to capture results
4. ❌ Testing variations without file directives

## Corrected Approach

1. ✅ Use simple, single-stream implementations
2. ✅ Add file directives for auto-detection
3. ✅ Wait 5-10 minutes for leaderboard runs to complete
4. ✅ Check Score column with `submissions list`
5. ✅ Use `--no-tui --output results.json` for automation
