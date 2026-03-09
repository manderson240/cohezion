import logging
from pathlib import Path

import requests


# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
SCOUT_MODEL = "qwen3-coder:30b"  # Fast, good at code reading
STRATEGIST_MODEL = "deepseek-r1:70b"  # Deep reasoning for architecture
TARGET_DIRS = ["src/cohezion", "scripts"]
OUTPUT_FILE = "AUTOMATION_OPPORTUNITIES.md"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AutoExplorer")


def call_ollama(model: str, prompt: str) -> str:
    logger.info(f"Subagent {model} thinking...")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30000000,
        )  # Long timeout for reasoning
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        logger.error(f"Error calling {model}: {e}")
        return ""


def scan_codebase(dirs: list[str]) -> dict[str, str]:
    """Read a random sample of files to look for patterns."""
    files_content = {}
    total_chars = 0
    MAX_CHARS = 20000  # Context window budget

    for d in dirs:
        path = Path(d)
        if not path.exists():
            continue

        for p in path.rglob("*.py"):
            if "venv" in str(p) or "__pycache__" in str(p):
                continue

            try:
                content = p.read_text()
                # Heuristic: only read files that look like 'boilerplate' or 'scripts'
                # or just sample substantial files
                if len(content) > 500:
                    files_content[str(p)] = content[:2000]  # First 2k chars
                    total_chars += 2000

                if total_chars > MAX_CHARS:
                    break
            except Exception as e:
                logger.warning(f"Skipping {p}: {e}")

        if total_chars > MAX_CHARS:
            break

    return files_content


def run_exploration():
    logger.info("Initializing Automation Exploration...")

    # 1. Scout Loop
    files = scan_codebase(TARGET_DIRS)
    context_str = "\n".join([f"--- {f} ---\n{c}\n" for f, c in files.items()])

    scout_prompt = f"""
    You are a Code Scout subagent. Scan these file snippets for:
    1. Repetitive manual tasks (e.g., hardcoded lists, manual data loading).
    2. Missing error handling or logging details.
    3. Opportunities for 'Self-Healing' or 'Auto-Configuration'.

    Code Snippets:
    {context_str}

    List 5 specific files/areas that need automation.
    """

    scout_report = call_ollama(SCOUT_MODEL, scout_prompt)
    if not scout_report:
        return

    logger.info("Scout Report Received.")

    # 2. Strategist Loop
    strategist_prompt = f"""
    The Code Scout has identified these areas:
    {scout_report}

    You are the Principal Architect. Design 3 specific Automation Workflows to address these.
    For each workflow:
    - Name it (e.g., 'Auto-Log-Rotator').
    - Describe the trigger (Cron? Event? File change?).
    - Sketch the Python implementation logic.

    Output in Markdown.
    """

    strategy = call_ollama(STRATEGIST_MODEL, strategist_prompt)
    if not strategy:
        return

    logger.info("Strategist Plan Received.")

    # Save Report
    with open(OUTPUT_FILE, "w") as f:
        f.write("# Automation Opportunities\n\n")
        f.write(f"## Scout Findings ({SCOUT_MODEL})\n")
        f.write(scout_report + "\n\n")
        f.write(f"## Strategic Plan ({STRATEGIST_MODEL})\n")
        f.write(strategy + "\n")

    logger.info(f"Report saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    run_exploration()
