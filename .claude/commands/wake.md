Wake up the Cohezion system (API, DB, Recorder).

Run: `uv run python3 scripts/wake_up.py`

If the wake script fails, check:
1. SurrealDB status: `systemctl --user status surrealdb` or check if it's running on ws://localhost:8001
2. Ollama status: `ollama list` to verify models are available
3. Report which services came up and which need attention.
