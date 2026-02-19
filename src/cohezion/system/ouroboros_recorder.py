"""Ouroboros Flight Recorder - Universe Simulation Replay and Self-Healing.

Captures complete scenario execution data as JSONL for replay, analysis,
and divergence recovery. Named after the self-devouring serpent symbol
representing cyclical self-improvement.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = "data/ouroboros"
DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_RECORDINGS = 10


class OuroborosRecorder:
    """Flight recorder for universe simulation events.

    Stores events as JSONL (append-friendly, line-delimited JSON).
    Supports replay, divergence tracking, file rotation, and retention.
    """

    def __init__(
        self,
        data_dir: str = DEFAULT_DATA_DIR,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_recordings: int = DEFAULT_MAX_RECORDINGS,
    ) -> None:
        """Initialize recorder.

        Args:
            data_dir: Directory for JSONL recording files
            max_file_bytes: Max file size before rotation
            max_recordings: Max number of recording files to retain
        """
        self.data_dir = Path(data_dir)
        self.max_file_bytes = max_file_bytes
        self.max_recordings = max_recordings
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def start_recording(self, scenario_name: str) -> str:
        """Start a new recording session.

        Args:
            scenario_name: Name/description of the scenario

        Returns:
            Recording ID for this session
        """
        recording_id = f"{scenario_name}_{uuid4().hex[:8]}"
        logger.debug(f"Started recording: {recording_id}")
        return recording_id

    def record_event(
        self,
        recording_id: str,
        event_type: str,
        data: dict[str, object],
    ) -> None:
        """Append an event to a recording.

        Args:
            recording_id: Recording session ID
            event_type: Type of event (agent_step, evaluation, etc.)
            data: Event data payload
        """
        try:
            event = {
                "recording_id": recording_id,
                "event_type": event_type,
                "timestamp": time.time(),
                "data": data,
            }

            path = self._get_recording_path(recording_id)
            self._check_rotation(path)

            with open(path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Recording failed (non-blocking): {e}")

    def record_divergence(
        self,
        recording_id: str,
        divergence_type: str,
        last_good_state: dict[str, object],
        divergent_state: dict[str, object],
    ) -> None:
        """Record a divergence event for self-healing.

        Args:
            recording_id: Recording session ID
            divergence_type: Type of divergence (coherence_collapse, nan, etc.)
            last_good_state: Last known stable state
            divergent_state: State where divergence occurred
        """
        self.record_event(
            recording_id,
            event_type="divergence",
            data={
                "divergence_type": divergence_type,
                "last_good_state": last_good_state,
                "divergent_state": divergent_state,
            },
        )

    def replay(self, recording_id: str) -> list[dict[str, object]]:
        """Replay events from a recording.

        Args:
            recording_id: Recording session ID

        Returns:
            List of event dicts in chronological order
        """
        path = self._get_recording_path(recording_id)
        if not path.exists():
            return []

        events: list[dict[str, object]] = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Replay failed: {e}")

        return events

    def apply_retention(self) -> None:
        """Remove old recordings beyond max_recordings limit."""
        try:
            files = sorted(
                self.data_dir.glob("*.jsonl"),
                key=lambda p: p.stat().st_mtime,
            )
            while len(files) > self.max_recordings:
                oldest = files.pop(0)
                oldest.unlink()
                logger.debug(f"Removed old recording: {oldest.name}")
        except Exception as e:
            logger.warning(f"Retention cleanup failed: {e}")

    def _get_recording_path(self, recording_id: str) -> Path:
        """Get file path for a recording.

        Args:
            recording_id: Recording session ID

        Returns:
            Path to the JSONL file
        """
        return self.data_dir / f"{recording_id}.jsonl"

    def _check_rotation(self, path: Path) -> None:
        """Rotate file if it exceeds max size.

        Args:
            path: Path to check
        """
        try:
            if path.exists() and path.stat().st_size >= self.max_file_bytes:
                rotated = path.with_suffix(f".{int(time.time())}.jsonl")
                path.rename(rotated)
                logger.debug(f"Rotated {path.name} → {rotated.name}")
        except Exception as e:
            logger.warning(f"File rotation failed: {e}")
