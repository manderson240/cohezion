import subprocess
import json
import time
import datetime
import os

LEADERBOARDS = ["amd-mxfp4-mm", "amd-mixed-mla", "amd-moe-mxfp4"]
VAULT_PATH = "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/LEADERBOARD_HISTORY.md"
EMAIL_PENDING_PATH = "/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/EMAIL_PENDING.json"

def get_leaderboard_status(lb_name):
    """Scrapes the top score for a given leaderboard."""
    cmd = ["/home/mike-anderson/.local/bin/popcorn-cli", "submissions", "list", "--leaderboard", lb_name, "--limit", "1"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.strip().split('\n')
        if len(lines) > 2:
            last_line = lines[-1]
            parts = last_line.split()
            if len(parts) >= 7:
                # Score is the last column
                return parts[-1]
    except Exception as e:
        return f"Error: {e}"
    return "-"

def parse_score(score_str):
    if not score_str or score_str == "-" or "Error" in score_str:
        return float('inf')
    try:
        # Expected format: "13.425µs" -> 13.425
        return float(score_str.replace('µs', '').replace('us', ''))
    except:
        return float('inf')

def queue_email(lb, old_score, new_score):
    data = {
        "leaderboard": lb,
        "old_score": old_score,
        "new_score": new_score,
        "timestamp": datetime.datetime.now().isoformat(),
        "sent": False
    }
    # Append to a list of pending emails
    pending = []
    if os.path.exists(EMAIL_PENDING_PATH):
        try:
            with open(EMAIL_PENDING_PATH, "r") as f:
                pending = json.load(f)
        except:
            pass
    
    pending.append(data)
    with open(EMAIL_PENDING_PATH, "w") as f:
        json.dump(pending, f, indent=2)
    print(f"📧 Email queued for {lb}: {old_score} -> {new_score}")

def update_vault(history):
    with open(VAULT_PATH, "a") as f:
        f.write(f"\n\n### Status Check: {datetime.datetime.now().isoformat()}\n")
        f.write("| Leaderboard | Our Best Score | Status |\n")
        f.write("|-------------|----------------|--------|\n")
        for lb, score in history.items():
            f.write(f"| {lb} | {score} | Logged |\n")

def main():
    print("🚀 Popcorn Leaderboard Monitor with Email Queue Started.")
    last_best = {lb: float('inf') for lb in LEADERBOARDS}
    
    # Initialize with current bests to avoid spamming at startup
    for lb in LEADERBOARDS:
        score_str = get_leaderboard_status(lb)
        last_best[lb] = parse_score(score_str)
        print(f"[{lb}] Initial best: {score_str} ({last_best[lb]})")

    while True:
        history = {}
        for lb in LEADERBOARDS:
            score_str = get_leaderboard_status(lb)
            current_score = parse_score(score_str)
            history[lb] = score_str
            
            if current_score < last_best[lb]:
                print(f"🔥 BREAKTHROUGH on {lb}! {last_best[lb]} -> {current_score}")
                queue_email(lb, last_best[lb], score_str)
                last_best[lb] = current_score
            
        update_vault(history)
        # Check every 10 minutes
        time.sleep(600)

if __name__ == "__main__":
    main()
