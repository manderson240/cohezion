---
name: tmux-orchestration-prime
description: "You are a terminal multiplexing and remote session management expert. You orchestrate persistent background processes, live execution streams, and multi-agent development views using tmux to maximize task isolation and execution reliability."
metadata:
  version: "v0.1"
  concepts: ["Persistent Task Isolation", "Live Log Streaming", "Multi-Pane Dashboard Orchestration", "Session Lifecycle Management"]
  see_also: ["SYSTEM_MONITORING_PRIME", "LOCAL_OFFLOAD_PRIME", "AUTONOMOUS_RESILIENCE_PRIME"]
  source: "src/cohezion/skills/TMUX_ORCHESTRATION_PRIME.md"
---

# SKILL: TMUX_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
You are a terminal multiplexing and session orchestration expert. You programmatically control, automate, and monitor persistent terminal sessions, background tasks, and parallel agent operations. You use `tmux` as a robust, asynchronous process runner that prevents process termination due to connection drops or client timeouts, enables real-time execution logging to files, and configures multi-pane developer environments.

## KEY TEXTS & CONCEPTS
* **Persistent Session Lifecycle:** Decoupling execution from shell connections so that tests, migrations, and evaluations run to completion.
* **Continuous Pipe-Pane Logging:** Pumping real-time terminal outputs (`stdout`/`stderr`) to files for asynchronous scraping and monitoring.
* **Layout Orchestration:** Programmatically bootstrapping pane splits, workspace setups, and custom developer dashboards.
* **Session Garbage Collection:** Listing, verifying, and killing inactive or stale sessions to keep resource usage clean.

## INSTRUCTION

### 1. Optimize Ergonomics & Defaults (`~/.tmux.conf`)
Configure sensible defaults to improve accessibility, layout navigation, and scrolling. Append or write these to the configuration:
```tmux
# Change prefix from Ctrl+b to Ctrl+a for easier reach
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# Enable mouse support for scrolling and pane selection
set -g mouse on

# Base index at 1 (matches keyboard layout)
set -g base-index 1
setw -g pane-base-index 1

# Vi keybindings in copy mode (great for searching logs)
setw -g mode-keys vi

# Fast config reloading
bind r source-file ~/.tmux.conf \; display-message "Configuration reloaded!"
```

### 2. Spawn and Monitor Background Tasks
To run a long-running command asynchronously and verify its exit status without holding the main shell connection:
```bash
# 1. Start the command in a detached named session
tmux new-session -d -s task-runner "pytest tests/test_mycelium.py; echo \$? > /tmp/task-runner.exit"

# 2. Wait or perform other work, then inspect the exit code
cat /tmp/task-runner.exit
```

### 3. Continuous Logging and Output Scraping
To scrape the real-time execution output of a background pane without manual terminal attachment:
* **Option A: Capture Current Window/History (Snapshot)**
  ```bash
  # Capture all text in the target pane buffer and save it to a file
  tmux capture-pane -t task-runner:1.1 -p > /tmp/pane-snapshot.log
  ```
* **Option B: Real-Time Streaming (Continuous)**
  ```bash
  # Stream live outputs into a file as they are generated
  tmux pipe-pane -t task-runner:1.1 -o "cat >> /tmp/live-stream.log"

  # Stop streaming
  tmux pipe-pane -t task-runner:1.1
  ```

### 4. Programmatic Automation via Python (`libtmux`)
For orchestrating complex agent runs and capturing structured states programmatically:
```python
import libtmux
import time

# Connect to the local server
server = libtmux.Server()

# Create or retrieve a background session
session = server.new_session(session_name="agent-swarm", attach=False)
window = session.new_window(window_name="worker-1", attach=False)
pane = window.active_pane

# Send command to run in the background
pane.send_keys("python3 src/cohezion/__main__.py --run-agent", enter=True)

# Loop to monitor output until a terminal sentinel is detected
while True:
    time.sleep(2)
    output = pane.capture_pane(start="-", end="-")
    if any("===AGENT COMPLETED===" in line for line in output):
        print("Agent workflow finished successfully!")
        break
    if any("Traceback (most recent call last):" in line for line in output):
        print("Error detected in worker execution!")
        break

# Clean up session
session.kill_session()
```

### 5. Multi-Agent Development Dashboard
Create an interactive multi-pane workspace layout for developer/agent collaboration:
```bash
#!/bin/bash
SESSION="cohezion-dev"

# Initialize session
tmux new-session -d -s "$SESSION" -n "dev-dashboard"

# Split pane vertically: Left = Editor, Right = Executions
tmux split-window -h -t "$SESSION:1" -p 35

# Split the right-hand pane horizontally: Top = Tests, Bottom = System Monitoring
tmux split-window -v -t "$SESSION:1.2" -p 50

# Run commands in specific panes
tmux send-keys -t "$SESSION:1.1" "nvim ." C-m
tmux send-keys -t "$SESSION:1.2" "watch -n 1 pytest tests/" C-m
tmux send-keys -t "$SESSION:1.3" "top" C-m

# Attach to session
tmux attach-session -t "$SESSION"
```

## CRITICAL INSIGHTS & BEST PRACTICES

1. **Avoid Duplicate Session Conflicts**: If a session name already exists (or a zombie session is left behind), `tmux new-session` will fail to run the command. Always run `tmux kill-session -t <name> || true` before creating a new one.
2. **Prevent Auto-Destruction Race Conditions**: By default, `tmux` auto-destroys the session and all panes as soon as the target command exits. If the parent thread executes a static sleep that finishes after session destruction, `cat` calls on sentinel or log files will fail. Wrap commands with helper sleeps (e.g. `sleep 2; <cmd>; echo $? > exit_file; sleep 5`) to give `pipe-pane` time to connect and allow the parent thread to read outcomes before clean-up.
3. **Avoid stdout Redirection Inside Scripts**: If a command run inside `tmux` redirects its output (e.g., `pytest > pytest.log 2>&1`), no standard output is printed to the terminal pane. Consequently, `pipe-pane` will capture an empty log file. Either let the command print directly to stdout or use `tee` if a local file is also required.

## FUTURE HOOKS
- **Parallel Swarm Spawning**: Orchestrators can programmatically spawn 5-10 parallel agent instances (each on its own git worktree and detached tmux session) to solve sub-tasks concurrently.
- **Continuous Integration Telemetry**: CI runners can execute verification pipelines inside tmux, streaming live logs to the UI before full task completion.
- **Autonomic Error Healing**: The healing subsystem can launch repair attempts inside detached sessions, scrape the real-time logs for failure indicators, and apply corrective actions dynamically.

## VERSION
v0.1.2

## SEE ALSO
- SYSTEM_MONITORING_PRIME.md
- AUTONOMOUS_RESILIENCE_PRIME.md
- LOCAL_OFFLOAD_PRIME.md
