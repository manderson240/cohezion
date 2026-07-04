---
title: "Tmux Orchestration"
date: "2026-06-03"
tags: [pattern, tmux, terminal-orchestration]
neural:
  activation: 0.85
  stage: mature
  synapse_in: 0
  synapse_out: 0
---

## Problem
AI developer agents frequently execute long-running background tasks (e.g., testing campaigns, database migrations, server processes, or multi-agent swarm loops). Running these commands synchronously blocks the agent's turn. Running them using simple background shells (e.g., standard `nohup` or raw fork/daemon processes) exposes them to premature termination if the parent SSH/terminal session disconnects or if the prompt environment times out. This results in orphaned zombie processes, lost execution outputs, and untrackable logs.

## Solution
Programmatically wrap background task execution inside isolated, named, detached `tmux` sessions. Use the built-in `pipe-pane` command to stream live output directly to a dedicated log file, allowing non-blocking log tailing and scraping by the parent agent. Capture the terminal exit code of the target process using trailing command-chain echoes, and ensure garbage collection of dead sessions using `tmux kill-session`.

## Code Example

### Asynchronous Execution & Log Piping via Bash CLI
```bash
# 1. Start a command in a detached, named tmux session
tmux new-session -d -s test-runner "pytest tests/test_mycelium.py; echo \$? > /tmp/test-runner.exit"

# 2. Start continuous log piping to a file
tmux pipe-pane -t test-runner:1.1 -o "cat >> /tmp/test-runner.log"

# 3. Stream or scrape logs asynchronously
tail -n 20 /tmp/test-runner.log

# 4. Stop log piping when done
tmux pipe-pane -t test-runner:1.1

# 5. Clean up the session
tmux kill-session -t test-runner
```

### Python Automation (`libtmux`)
```python
import libtmux
import time

server = libtmux.Server()
session = server.new_session(session_name="agent-task", attach=False)
pane = session.active_window.active_pane

# Send command to run in the background
pane.send_keys("python3 -m cohezion.swarm.agent", enter=True)

# Scrape output until a sentinel string is found
while True:
    time.sleep(2)
    output = pane.capture_pane(start="-", end="-")
    if any("===COMPLETED===" in line for line in output):
        break

session.kill_session()
```

## When to Use
Use this pattern when managing any remote background execution that must survive agent session boundaries, particularly during long-running testing campaigns, multi-agent coordination, and active telemetry log streaming.
