"""Neural Write-Back — syncs SurrealDB-owned fields to vault frontmatter."""

import sys
import time
import re

from .client import SurrealClient
from .config import VAULT_ROOT
from .helpers import _NEURAL_BLOCK_RE, _writeback_paths

WRITEBACK_THROTTLE_SECS = 300  # 5 minutes


class NeuralWriteBack:
    """Writes SurrealDB-owned fields back to vault frontmatter neural: blocks.

    Domain ownership: SurrealDB owns activation, stage, synapse_in, synapse_out.
    This class reads those values and updates the neural: YAML block in each note.
    """

    def __init__(self, db: SurrealClient):
        self.db = db
        self._last_run = 0.0

    def maybe_run(self, force: bool = False) -> bool:
        now = time.time()
        if not force and now - self._last_run < WRITEBACK_THROTTLE_SECS:
            return False
        self._last_run = now
        return self._run()

    def _run(self) -> bool:
        cutoff = self._last_run - WRITEBACK_THROTTLE_SECS - 10
        try:
            neurons = self.db.query_result(
                "SELECT path, activation, stage, synapse_in, synapse_out "
                "FROM neuron WHERE modified > time::from::unix("
                f"{int(cutoff)}) OR synapse_in != synapse_in;"
            )
        except Exception as e:
            print(f"NeuralWriteBack query error: {e}", file=sys.stderr)
            try:
                neurons = self.db.query_result(
                    "SELECT path, activation, stage, synapse_in, synapse_out "
                    "FROM neuron;"
                )
            except Exception:
                return False

        if not neurons:
            return False

        updated = 0
        for n in neurons:
            path = n.get("path", "")
            if not path:
                continue
            fpath = VAULT_ROOT / path
            if not fpath.is_file():
                continue

            new_neural = {
                "activation": round(float(n.get("activation", 0)), 2),
                "stage": str(n.get("stage", "embryo")),
                "synapse_in": int(n.get("synapse_in", 0)),
                "synapse_out": int(n.get("synapse_out", 0)),
            }

            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            current_neural = self._parse_neural_block(text)
            if current_neural == new_neural:
                continue

            new_text = self._update_neural_block(text, new_neural)
            if new_text == text:
                continue

            _writeback_paths.add(path)

            try:
                fpath.write_text(new_text, encoding="utf-8")
                updated += 1
            except OSError as e:
                print(f"  WARN writeback {path}: {e}", file=sys.stderr)
                _writeback_paths.discard(path)

        if updated > 0:
            print(f"Neural write-back: {updated} files updated", file=sys.stderr)
        return updated > 0

    @staticmethod
    def _parse_neural_block(text: str) -> dict:
        """Extract current neural: values from frontmatter."""
        if not text.startswith("---"):
            return {}
        end = text.find("\n---", 3)
        if end == -1:
            return {}
        fm_text = text[3:end]

        result = {}
        in_neural = False
        for line in fm_text.split("\n"):
            if line.startswith("neural:"):
                in_neural = True
                continue
            if in_neural:
                if line.startswith("  ") or line.startswith("\t"):
                    key, _, val = line.strip().partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key in ("activation", "synapse_in", "synapse_out"):
                        try:
                            result[key] = (
                                round(float(val), 2)
                                if key == "activation"
                                else int(val)
                            )
                        except (ValueError, TypeError):
                            pass
                    elif key == "stage":
                        result[key] = val.strip('"').strip("'")
                else:
                    in_neural = False
        return result

    @staticmethod
    def _update_neural_block(text: str, neural: dict) -> str:
        """Replace or insert the neural: block in frontmatter."""
        if not text.startswith("---"):
            return text
        end = text.find("\n---", 3)
        if end == -1:
            return text

        fm_text = text[3:end]
        body = text[end:]

        neural_yaml = (
            "neural:\n"
            f"  activation: {neural['activation']}\n"
            f"  stage: {neural['stage']}\n"
            f"  synapse_in: {neural['synapse_in']}\n"
            f"  synapse_out: {neural['synapse_out']}\n"
        )

        cleaned = _NEURAL_BLOCK_RE.sub("", fm_text)

        if not cleaned.endswith("\n"):
            cleaned += "\n"

        return "---" + cleaned + neural_yaml + body
