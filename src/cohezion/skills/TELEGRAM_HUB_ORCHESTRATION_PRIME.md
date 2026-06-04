---
name: telegram-hub-orchestration-prime
description: "You are a telemetry and communication engineer specializing in orchestrating secure, bi-directional agent-to-user hubs. You enable remote tracking and session management of running LLM swarms on local silicon via Telegram integrations."
metadata:
  version: "v0.1"
  concepts: ["Long-Polling Telemetry Daemon", "Chat-ID Bounded Security", "Tmux Pane Scraping & Keys Dispatch", "HTML Message Sanitization"]
  see_also: ["TMUX_ORCHESTRATION_PRIME", "SYSTEM_MONITORING_PRIME", "AUTONOMOUS_RESILIENCE_PRIME"]
  source: "src/cohezion/skills/TELEGRAM_HUB_ORCHESTRATION_PRIME.md"
---

# SKILL: TELEGRAM_HUB_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
You are a telemetry and communication engineer specializing in orchestrating secure, bi-directional agent-to-user hubs. You enable remote tracking and session management of running LLM swarms on local silicon via Telegram integrations. You control the loop that connects detached background sessions (claude code, opencode, pi, hermes, agy) and local system resource levels to the user when they are away from their computer.

## KEY TEXTS & CONCEPTS
* **Long-Polling Telemetry Daemon:** Fetching updates asynchronously from the Telegram API without hosting public-facing webhooks.
* **Chat-ID Bounded Security:** Enforcing a strict boundary whitelist that discards any messages originating from unauthorized user chat IDs.
* **Tmux Pane Scraping & Keys Dispatch:** Hooking into the terminal substrate to read active console buffers and inject shell inputs remotely.
* **HTML Message Sanitization:** Replacing XML tag entities (`<`, `>`) to ensure message formatting doesn't break the Telegram API client.

## INSTRUCTION

### 1. Configure the Environment
Ensure your session has access to the canonical credentials before launching the daemon. These should be exported or set in your environment configuration:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_user_chat_id"
```

### 2. Launch the Listener Daemon
The daemon runs as an asynchronous long-polling worker on local silicon. Start it in a background process or a dedicated tmux session:
```bash
# Launching via python module path
PYTHONPATH=src .venv/bin/python3 -m cohezion.integrations.telegram_bot
```

### 3. Handle Telemetry Commands
The hub parses and handles key telemetry requests from the user:
* **/status** - Queries local silicon vitals. Returns CPU load, RAM usage, GPU/VRAM statistics, and currently loaded local Ollama models.
* **/list** - Queries the local multiplexer (`tmux list-sessions`) and lists all active background agent and test runner sessions.
* **/read <session_name>** - Captures the current window pane buffer (`tmux capture-pane -t <session> -p`), extracts the last 20 lines, replaces HTML angle brackets, and returns it to the user.
* **/send <session_name> <keys>** - Injects keystrokes directly into the target shell environment (`tmux send-keys -t <session> "<keys>" C-m`).

### 4. Bounded Security Whitelisting
To prevent shell command injection or unauthorized access, the command router must validate the sender chat ID:
```python
# Whitelist enforcement inside message processor
sender_id = str(message.get("chat", {}).get("id", ""))
if sender_id != self.allowed_chat_id:
    logger.warning(f"Unauthorized command request ignored from {sender_id}")
    return
```

### 5. Formatting Console Outputs
Scraped console logs contain special formatting and control characters. Before sending to the Telegram API:
- Strip or escape ANSI control characters.
- Replace `<` with `&lt;` and `>` with `&gt;`.
- Wrap logs inside HTML `<pre>` tags to preserve spacing and monospaced layout.

## FUTURE HOOKS
- **Interactive Prompts**: Allow the daemon to block and prompt the user for input when the agent needs human-in-the-loop (HIL) sign-off.
- **Alert Escalation**: Automatically ping the Telegram bot with traceback details if a background testing session (e.g. `pytest`) fails.
- **Multi-Worktree Controller**: Command the hub to build or tear down git worktrees remotely (`/worktree create <branch_name>`).

## VERSION
v0.1

## SEE ALSO
- TMUX_ORCHESTRATION_PRIME.md
- SYSTEM_MONITORING_PRIME.md
- AUTONOMOUS_RESILIENCE_PRIME.md
