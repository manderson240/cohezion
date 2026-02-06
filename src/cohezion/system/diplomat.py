import logging
import threading
from typing import Any

from flask import Flask, jsonify

logger = logging.getLogger(__name__)


class DiplomatAgent:
    """
    The Diplomat: Bridges the Interface Simulation with the External Network.
    Uses a lightweight Flask server to expose the Universe State.
    """

    def __init__(self, port=5000):
        self.port = port
        self.app = Flask(__name__)
        self.latest_state = {}
        self.chaos_requested = False
        self.lock = threading.Lock()
        self.server_thread = None

        # Define Routes
        self.app.add_url_rule("/state", "get_state", self.get_state, methods=["GET"])
        self.app.add_url_rule(
            "/join", "join_universe", self.join_universe, methods=["POST"]
        )
        self.app.add_url_rule(
            "/chaos", "trigger_chaos", self.trigger_chaos, methods=["POST"]
        )

    def update_state(self, state: dict[str, Any]):
        """Updates the internal state snapshot (Thread-safe)."""
        with self.lock:
            self.latest_state = state

    def get_state(self):
        """Returns the current Universe Snapshot."""
        with self.lock:
            return jsonify(self.latest_state)

    def join_universe(self):
        """Endpoint for other nodes to register."""
        # For MVP, just acknowledge
        return jsonify({"status": "Welcome to the Federation", "role": "Observer"})

    def trigger_chaos(self):
        """Red Team Endpoint: Spikes Entropy to Critical Levels."""
        with self.lock:
            # We set a flag in the state that the Sim Agent reads?
            # Or better, we manipulate the state directly if possible.
            # Since 'latest_state' is just a snapshot, this won't affect physics.
            # We need a callback or shared memory.
            # For this MVP, we set a flag that the Sim Agent checks.
            self.chaos_requested = True
            import logging

            logging.getLogger(__name__).critical(
                f"DEBUG: Chaos Flag SET to True in Method. Self ID: {id(self)}"
            )
        return jsonify({"status": "CHAOS INITIATED", "entropy": 0.99})

    def start(self):
        """Starts the Flask server in a background thread."""
        if self.server_thread is None:
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            logger.info(f"🌐 Diplomat Agent listening on port {self.port}")

    def _run_server(self):
        # Disable Flask banner
        try:
            logger.info(f"Flask starting on 127.0.0.1:{self.port}...")
            self.app.run(
                host="127.0.0.1", port=self.port, debug=False, use_reloader=False
            )
        except Exception as e:
            logger.error(f"Flask Server Failed: {e}")
