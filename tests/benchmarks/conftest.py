"""conftest for benchmarks tests — register FlumeNav environment."""

from __future__ import annotations

import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.rl.environment import FlumeNavEnv  # noqa: F401 - triggers gym.register
