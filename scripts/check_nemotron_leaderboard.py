#!/usr/bin/env python3
"""
Check leaderboard position for NVIDIA Nemotron Model Reasoning Challenge.
"""

import asyncio
import os

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

# Set Kaggle credentials for all libraries
username = os.getenv("KAGGLE_USERNAME") or os.getenv("username")
api_token = os.getenv("KAGGLE_API_TOKEN")

if api_token and api_token.startswith("KGAT_"):
    api_token = api_token[5:]

if username:
    os.environ["KAGGLE_USERNAME"] = username
if api_token:
    os.environ["KAGGLE_KEY"] = api_token

from kaggle.api.kaggle_api_extended import KaggleApi


async def check_leaderboard():
    """Check our position on the NVIDIA Nemotron Model Reasoning Challenge leaderboard."""
    if not username or not api_token:
        print("❌ Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return

    print(f"🏆 Checking leaderboard for user: {username}")

    # Use direct Kaggle API for leaderboard access
    api = KaggleApi()
    try:
        api.authenticate()
    except Exception as e:
        print(f"❌ Failed to authenticate with Kaggle API: {e}")
        return

    try:
        # Get competition leaderboard
        competition_id = "nvidia-nemotron-model-reasoning-challenge"
        print(f"🔍 Fetching leaderboard for competition: {competition_id}")

        # Get submissions (this serves as leaderboard)
        submissions = api.competition_submissions(competition_id)

        if submissions:
            print("\n" + "=" * 80)
            print(f"🏆 NEMOTRON MODEL REASONING CHALLENGE LEADERBOARD")
            print("=" * 80)
            print(f"{'Rank':<6} {'Team Name':<25} {'Score':<12} {'Submission Date':<20} {'Status'}")
            print("-" * 80)

            # Show top 15 entries
            for i, submission in enumerate(submissions[:15], 1):
                team_name = getattr(submission, "teamName", "Unknown")
                # Handle both float and string scores
                score_raw = getattr(submission, "score", "N/A")
                if score_raw != "N/A":
                    try:
                        score = f"{float(score_raw):.6f}"
                    except (ValueError, TypeError):
                        score = str(score_raw)
                else:
                    score = "N/A"
                date = getattr(submission, "date", "N/A")
                status = getattr(submission, "status", "N/A")

                # Format date if it's a datetime object
                if hasattr(date, "strftime"):
                    date_str = date.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = str(date)[:19] if len(str(date)) > 19 else str(date)

                # Highlight our submission
                highlight = (
                    "👉"
                    if username.lower() in team_name.lower() or "manderson" in team_name.lower()
                    else "  "
                )
                print(f"{highlight}{i:<5} {team_name:<25} {score:<12} {date_str:<20} {status}")

            print("-" * 80)

            # Check if we're on the leaderboard
            our_entries = [
                submission
                for submission in submissions
                if hasattr(submission, "teamName")
                and (
                    username.lower() in submission.teamName.lower()
                    or "manderson" in submission.teamName.lower()
                )
            ]

            if our_entries:
                print(f"🎉 FOUND {len(our_entries)} ENTRY(IES) FROM YOU ON THE LEADERBOARD!")
                for entry in our_entries:
                    rank = submissions.index(entry) + 1
                    score_raw = getattr(entry, "score", "N/A")
                    if score_raw != "N/A":
                        try:
                            score = f"{float(score_raw):.6f}"
                        except (ValueError, TypeError):
                            score = str(score_raw)
                    else:
                        score = "N/A"
                    print(f"   Rank #{rank}: Score {score}")

                if len(our_entries) == 1:
                    rank = submissions.index(our_entries[0]) + 1
                    print(f"\n🎯 You are currently ranked #{rank}!")
                else:
                    ranks = [str(submissions.index(entry) + 1) for entry in our_entries]
                    print(f"\n🎯 You are currently ranked at positions: {', '.join(ranks)}!")

                # Show best score
                best_score = None
                for entry in our_entries:
                    score_raw = getattr(entry, "score", "N/A")
                    if score_raw != "N/A":
                        try:
                            score_val = float(score_raw)
                            if best_score is None or score_val > best_score:
                                best_score = score_val
                        except (ValueError, TypeError):
                            pass

                if best_score is not None:
                    print(f"🏆 Your best score: {best_score:.6f}")
            else:
                print(f"📭 No entries found from you on the leaderboard yet.")
                print(f"💡 Make sure to:")
                print(f"   1. Complete training and retrieve your adapter")
                print(f"   2. Submit the adapter using the submission script")
                print(f"   3. Check back here to see your position")

            print("=" * 80)

            # Show total number of submissions
            print(f"📊 Total submissions in competition: {len(submissions)}")
        else:
            print("📭 No submission data available yet.")

    except Exception as e:
        print(f"❌ Error checking leaderboard: {e}")
        import traceback

        traceback.print_exc()


async def main():
    print("🚀 NEMOTRON LEADERBOARD CHECKER")
    print("=" * 50)

    await check_leaderboard()

    print("\n💡 TIPS:")
    print("  - Run this script periodically to check your progress")
    print("  - The leaderboard updates as submissions are processed")
    print("  - Check the competition page for scoring details:")
    print("    https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge")
    print("  - Higher scores are typically better (verify with competition description)")
    print("  - Keep improving your model to climb the ranks!")


if __name__ == "__main__":
    asyncio.run(main())
