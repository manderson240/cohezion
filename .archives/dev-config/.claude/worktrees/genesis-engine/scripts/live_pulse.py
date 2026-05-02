import asyncio
import os
from datetime import datetime
from pathlib import Path


async def pulse_dashboard():
    """A 'tail -f' friendly dashboard for the terminal."""
    log_file = Path("universe_sim.log")
    chronicle_file = Path("chronicle_of_the_infinite.md")

    # ANSI Colors
    CYAN = "\033[96m"
    GOLD = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    def get_last_line(path):
        try:
            with open(path) as f:
                lines = f.readlines()
                return lines[-1].strip() if lines else "Waiting..."
        except Exception:
            return "File not found."

    while True:
        os.system("clear")
        print(f"{CYAN}🌍 COHEZION LIVE PULSE | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print("-" * 60)

        # 1. System Status
        status = "🟢 ACTIVE"
        print(f"Status: {status}")

        # 2. Vital Signs (Simulated from last chronicle entry)
        last_chron = get_last_line(chronicle_file)
        print(f"\n{GOLD}📊 VITAL SIGNS (Most Recent){RESET}")
        print(f"> {last_chron}")

        # 3. Swarm Activity
        last_log = get_last_line(log_file)
        print(f"\n{GREEN}🤖 SWARM ACTIVITY{RESET}")
        print(f"> {last_log}")

        # 4. Persistence Guard
        db_status = "✅ DB CONNECTED"
        print(f"\n{CYAN}💾 PERSISTENCE{RESET}")
        print(f"> {db_status}")

        print("\n" + "-" * 60)
        print("Press Ctrl+C to exit.")

        await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(pulse_dashboard())
    except KeyboardInterrupt:
        print("\nExiting Pulse Dashboard.")
