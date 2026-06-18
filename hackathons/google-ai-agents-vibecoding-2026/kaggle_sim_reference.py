"""
kaggle_sim_reference.py — submission mechanics for a Kaggle Simulations agent comp.

Pre-stage for the June-2026 "Kaggriculture" capstone (5-Day AI Agents Vibe Coding course).
We do NOT yet have the Kaggriculture env; this uses ConnectX as a stand-in to make the
submission loop muscle-memory. When Kaggriculture drops (~Jun 15-19), only three things
change: the env name in make(...), the observation/action shapes inside the agent, and the
strategy. The packaging + validation flow below is identical.

The ONE thing people get wrong: Kaggle scores a STANDALONE AGENT FILE, not your notebook
globals. Your `def agent(observation, configuration)` must run with everything it needs
defined inside the file (or importable on the Kaggle image). Validate by re-loading from the
written file and running it — that's what the grader does.

Run: /home/mike-anderson/dev/cohezion/.venv/bin/python kaggle_sim_reference.py
"""
from __future__ import annotations

from pathlib import Path

from kaggle_environments import evaluate, make


ENV_NAME = "connectx"  # <- swap for the Kaggriculture env id when published


# --- 1. Agent signature: agent(observation, configuration) -> action ----------------
# observation/configuration are dict-like (attr access works: observation.board, configuration.columns).
def heuristic_agent(observation, configuration):
    """Baseline: win-if-you-can / block-if-you-must / else center-biased random."""
    cols, rows, inarow = configuration.columns, configuration.rows, configuration.inarow
    board = observation.board
    mark = observation.mark

    def drop_row(c, b):
        for r in range(rows - 1, -1, -1):
            if b[c + r * cols] == 0:
                return r
        return -1

    def wins(c, who):
        b = list(board)
        r = drop_row(c, b)
        if r < 0:
            return False
        b[c + r * cols] = who
        # check 4 directions from (r,c)
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            count = 1
            for sign in (1, -1):
                rr, cc = r + dr * sign, c + dc * sign
                while 0 <= rr < rows and 0 <= cc < cols and b[cc + rr * cols] == who:
                    count += 1
                    rr += dr * sign
                    cc += dc * sign
            if count >= inarow:
                return True
        return False

    valid = [c for c in range(cols) if board[c] == 0]
    for c in valid:                                  # take a win
        if wins(c, mark):
            return c
    opp = 3 - mark
    for c in valid:                                  # block a loss
        if wins(c, opp):
            return c
    valid.sort(key=lambda c: abs(c - cols // 2))     # prefer center
    return valid[0] if valid else 0


# --- 2. Run a single episode (for replay/debug) -------------------------------------
def run_one():
    env = make(ENV_NAME, debug=True)
    env.run([heuristic_agent, "random"])
    final = env.steps[-1]
    print(f"[run_one] steps={len(env.steps)} rewards(p0,p1)={[s['reward'] for s in final]}")
    return env


# --- 3. Evaluate win-rate vs a baseline (this is your dev signal) --------------------
def win_rate(agent, opponent="random", n=20):
    # play both seats to remove first-move advantage
    a = evaluate(ENV_NAME, [agent, opponent], num_episodes=n // 2)
    b = evaluate(ENV_NAME, [opponent, agent], num_episodes=n // 2)
    wins = sum(1 for r in a if r[0] == 1) + sum(1 for r in b if r[1] == 1)
    print(f"[win_rate] {wins}/{n} vs {opponent}")
    return wins / n


# --- 4. Package a STANDALONE submission file and validate it the way Kaggle does -----
SUBMISSION = Path(__file__).parent / "submission.py"

SUBMISSION_SRC = '''\
def agent(observation, configuration):
    import random
    cols, rows, inarow = configuration.columns, configuration.rows, configuration.inarow
    board, mark = observation.board, observation.mark
    def drop_row(c, b):
        for r in range(rows - 1, -1, -1):
            if b[c + r * cols] == 0:
                return r
        return -1
    def wins(c, who):
        b = list(board); r = drop_row(c, b)
        if r < 0: return False
        b[c + r * cols] = who
        for dr, dc in ((0,1),(1,0),(1,1),(1,-1)):
            n = 1
            for s in (1,-1):
                rr, cc = r+dr*s, c+dc*s
                while 0<=rr<rows and 0<=cc<cols and b[cc+rr*cols]==who:
                    n+=1; rr+=dr*s; cc+=dc*s
            if n>=inarow: return True
        return False
    valid=[c for c in range(cols) if board[c]==0]
    for c in valid:
        if wins(c, mark): return c
    opp=3-mark
    for c in valid:
        if wins(c, opp): return c
    valid.sort(key=lambda c: abs(c-cols//2))
    return valid[0] if valid else 0
'''


def package_and_validate():
    SUBMISSION.write_text(SUBMISSION_SRC)
    # Kaggle runs your agent FROM THE FILE. Validate exactly that path:
    env = make(ENV_NAME, debug=True)
    env.run([str(SUBMISSION), "random"])
    status = [s["status"] for s in env.steps[-1]]
    ok = status[0] == "DONE"
    print(f"[package] wrote {SUBMISSION.name} | file-agent statuses={status} | loads_ok={ok}")
    return ok


# --- 5. On-theme LLM-policy skeleton (vibe-coding angle: Gemini in the loop) ---------
# Kaggriculture rewards an autonomous resource manager. An LLM policy reads the state,
# reasons, and emits an action each tick. Keep it ROBUST: hard timeouts + a heuristic
# fallback, because the harness kills slow/erroring agents (actTimeout in the config).
LLM_AGENT_SKELETON = '''\
def agent(observation, configuration):
    # 1) summarize observation -> compact text state
    # 2) call Gemini with a tight system prompt: "You manage resources to maximize <reward>.
    #    Respond with ONLY a valid action token." (low max_tokens, temperature ~0.2)
    # 3) parse + VALIDATE the action against the legal action set
    # 4) on timeout/parse-failure/illegal -> fall back to a fast heuristic (never crash)
    try:
        action = call_gemini_policy(observation, configuration)   # wrap with a deadline
        if action in legal_actions(observation, configuration):
            return action
    except Exception:
        pass
    return heuristic_fallback(observation, configuration)
'''


if __name__ == "__main__":
    run_one()
    win_rate(heuristic_agent, "random", n=20)
    assert package_and_validate(), "submission.py failed to load/run as a file agent"
    print("\nREADY: agent signature, env.run, evaluate, and file-based submission all verified.")
    print("When Kaggriculture opens: change ENV_NAME, adapt obs/action handling, keep this flow.")
