import os
import time

import polars as pl
from knowledge_graft import KnowledgeGraft


def capture_loop():
    grafter = KnowledgeGraft()
    print("Starting Learning Capture Loop (runs every 30 minutes)...")

    while True:
        try:
            if os.path.exists("research_results.tsv"):
                df = pl.read_csv("research_results.tsv", separator="\t")
                # Look for 'best' configs that haven't been processed
                # (Simple heuristic: check hypothesis name against existing skills)
                for row in df.filter(pl.col("best") == True).iter_rows():
                    hypothesis = row[1]  # hypothesis column
                    accuracy = row[2]  # accuracy column
                    grafter.graft_winning_strategy(hypothesis, accuracy)

            # Health Check: Check if log has been updated in last 20 mins
            if os.path.exists("sprint_monitor.log"):
                mtime = os.path.getmtime("sprint_monitor.log")
                if (time.time() - mtime) > 1200:  # 20 minutes
                    print(
                        "WARNING: sprint_monitor.log hasn't been updated in 20 mins. Possible stall."
                    )

        except Exception as e:
            print(f"Error in capture loop: {e!s}")

        time.sleep(1800)  # 30 minutes


if __name__ == "__main__":
    capture_loop()
