"""TapeLogger — records every LLM call for deterministic compound replay.

Each tape is a JSONL file: one TapeEntry per line. Replay feeds recorded
responses back instead of issuing live LLM calls.
"""

import json
import threading
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class TapeEntry:
    sequence: int
    timestamp: str  # ISO-8601
    model: str
    prompt: str
    response: str
    temperature: float
    tokens_in: int
    tokens_out: int
    latency_ms: float


class TapeLogger:
    def __init__(self, tape_dir: str | Path = "data/tapes", enabled: bool = True) -> None:
        self._tape_dir = Path(tape_dir)
        self._enabled = enabled
        self._lock = threading.Lock()
        self._tape_path: Path | None = None
        self._sequence = 0
        self._handle = None

    def start_tape(self, execution_id: str) -> str:
        """Start a new tape for an execution. Returns tape file path."""
        if not self._enabled:
            return ""
        self._tape_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        self._tape_path = self._tape_dir / f"{execution_id}_{ts}.jsonl"
        self._sequence = 0
        self._handle = self._tape_path.open("a", encoding="utf-8")
        return str(self._tape_path)

    def record(
        self,
        model: str,
        prompt: str,
        response: str,
        temperature: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Append one LLM call to the active tape (crash-safe flush)."""
        if not self._enabled or self._handle is None:
            return
        with self._lock:
            entry = TapeEntry(
                sequence=self._sequence,
                timestamp=datetime.now(UTC).isoformat(),
                model=model,
                prompt=prompt,
                response=response,
                temperature=temperature,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
            )
            self._sequence += 1
            self._handle.write(json.dumps(asdict(entry)) + "\n")
            self._handle.flush()

    def stop_tape(self) -> str | None:
        """Stop recording. Returns tape file path or None if not recording."""
        if not self._enabled or self._handle is None:
            return None
        with self._lock:
            self._handle.close()
            self._handle = None
            path = str(self._tape_path)
            self._tape_path = None
            return path

    def replay(self, tape_path: str) -> Iterator[TapeEntry]:
        """Yield TapeEntry objects from a tape file in sequence order."""
        with Path(tape_path).open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield TapeEntry(**json.loads(line))

    def get_response(self, tape_path: str, sequence: int) -> str | None:
        """Return the recorded response for a given sequence number."""
        for entry in self.replay(tape_path):
            if entry.sequence == sequence:
                return entry.response
        return None
