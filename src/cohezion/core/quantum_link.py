import fcntl
import json
import time
from pathlib import Path
from typing import Any

# Linux Shared Memory path (RAM Disk)
QUANTUM_PATH = Path("/dev/shm/cohezion_quantum_state.json")


class QuantumLink:
    """
    Quantum Link: Instantaneous Shared State for Agents.
    Uses /dev/shm (RAM) for sub-millisecond IPC.
    Handles file locking to prevent race conditions.
    """

    def __init__(self):
        self._ensure_init()

    def _ensure_init(self):
        if not QUANTUM_PATH.exists():
            with open(QUANTUM_PATH, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump({"system_status": "OK", "init_time": time.time()}, f)
                fcntl.flock(f, fcntl.LOCK_UN)

    def read(self) -> dict[str, Any]:
        """Read the shared state."""
        try:
            with open(QUANTUM_PATH) as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
                return data
        except Exception:
            return {}

    def update(self, **kwargs):
        """Update specific keys in shared state."""
        try:
            # R-M-W Cycle with Lock
            with open(QUANTUM_PATH, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    content = f.read()
                    data = json.loads(content) if content else {}
                except Exception:
                    data = {}

                # Update
                for k, v in kwargs.items():
                    data[k] = v

                # Write back
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                fcntl.flock(f, fcntl.LOCK_UN)
        except Exception:
            pass  # Creating new file if failed handled by init?


if __name__ == "__main__":
    link = QuantumLink()
    link.update(test="value")
    print(link.read())
