# How to Capture Timing from Leaderboard Submissions

## The Problem

When you submit with `--mode leaderboard`, the popcorn CLI shows:
```
Runs:
  - leaderboard on MI355X: passed (score: -)
```

The timing data is NOT shown directly in the CLI output!

## How to Get the Actual Timing

### Method 1: Check the Popcorn Website

1. Go to: `https://kernels.luma.io`
2. Find your leaderboard
3. Find your submission in the list
4. The timing is shown in the Score column

### Method 2: Wait for Score Propagation

The Score column in `popcorn-cli submissions list` eventually shows the timing:
```bash
popcorn-cli submissions list --leaderboard amd-mixed-mla
```

Output will show:
```
ID       Leaderboard          File    Time                     GPU(s)    Status  Score
------------------------------------------------------------------------------------------------
720690   amd-mixed-mla        sub.py  2026-04-04T07:07...      MI355X    done    45.2µs  ← TIMING HERE
```

### Method 3: Continuous Monitoring Script

```bash
#!/bin/bash
# monitor_leaderboard.sh

LEADERBOARD="amd-mixed-mla"
SUBMISSION_ID="720690"

while true; do
    RESULT=$(timeout 10 popcorn-cli submissions list --leaderboard $LEADERBOARD 2>/dev/null | grep $SUBMISSION_ID)
    SCORE=$(echo $RESULT | awk '{print $NF}')
    
    if [[ "$SCORE" != "-" ]]; then
        echo "[$(date)] Score: $SCORE"
        break
    fi
    
    echo "[$(date)] Waiting for score..."
    sleep 60
done
```

## Verification: What a Successful Leaderboard Submission Looks Like

### Submission Structure

```
Submission #720690
Leaderboard:    amd-mixed-mla (id: 765)
Status:         done

Runs:
  - test on MI355X: passed (score: -)
  - benchmark on MI355X: passed (score: -)
  - leaderboard on MI355X: passed (score: -)  ← THIS IS THE KEY
```

### List Output (After Score Propagation)

```
720690   amd-mixed-mla   submission.py   2026-04-04T07:07...   MI355X   done   45.2µs
```

## Current Status (Our Submissions)

| Submission | Leaderboard | Status | Has Leaderboard Run |
|------------|-------------|--------|---------------------|
| 720690 | amd-mixed-mla | done | ✅ YES |
| 724153 | amd-moe-mxfp4 | done | ⏳ Checking... |
| 724152 | amd-mxfp4-mm | done | ⏳ Checking... |

## Automated Capture Strategy

```bash
#!/bin/bash
# capture_scores.sh

capture_score() {
    local id=$1
    local leaderboard=$2
    local name=$3
    
    echo "Capturing $name ($id)..."
    
    # Get full submission details
    timeout 15 popcorn-cli submissions show $id > /tmp/${name}_${id}.txt 2>&1
    
    # Check for leaderboard run
    if grep -q "leaderboard on" /tmp/${name}_${id}.txt; then
        echo "✅ $name has leaderboard run!"
        
        # Get timing from list
        timeout 10 popcorn-cli submissions list --leaderboard $leaderboard | 
            grep $id > /tmp/${name}_${id}_score.txt 2>&1
        
        SCORE=$(cat /tmp/${name}_${id}_score.txt | awk '{print $NF}')
        echo "Score: $SCORE"
    else
        echo "❌ $name does not have leaderboard run"
    fi
}

# Capture all three
capture_score "720690" "amd-mixed-mla" "MLA"
capture_score "724153" "amd-moe-mxfp4" "MoE"
capture_score "724152" "amd-mxfp4-mm" "GEMM"
```

## Quick Reference

```bash
# Submit to leaderboard
cd /path/to/kernel
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui

# Check if it has leaderboard run
timeout 15 popcorn-cli submissions show <ID> | grep "leaderboard on"

# Get timing (may need to wait)
timeout 10 popcorn-cli submissions list --leaderboard amd-mixed-mla | grep <ID>
```

## Notes

1. **Score propagation takes time**: Can be 30 seconds to several minutes
2. **Score shows as "-" initially**: Means processing not complete
3. **Website is fastest**: kernels.luma.io shows scores immediately
4. **CLI eventually updates**: Keep polling the list command
