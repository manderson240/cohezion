"""_ask must read the answer from whichever channel the local router used.

FLM can ignore ``enable_thinking: False`` and return ``content=""`` with the answer in
``reasoning_content``. Reading ``content`` alone turned a real verdict into UNKNOWN.
The prior revision fails ``test_answer_in_reasoning_channel_is_parsed`` (returns '').
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest import mock


_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "local_adversarial_review.py"
_spec = importlib.util.spec_from_file_location("ci_local_adversarial_review", _PATH)
assert _spec is not None and _spec.loader is not None
lar = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lar
_spec.loader.exec_module(lar)


class _Resp(io.BytesIO):
    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _ask_with(message: dict) -> str:
    body = json.dumps({"choices": [{"message": message}]}).encode()
    with mock.patch.object(lar.urllib.request, "urlopen", return_value=_Resp(body)):
        return lar._ask("model", "prompt")


def test_answer_in_reasoning_channel_is_parsed() -> None:
    text = _ask_with(
        {"content": "", "reasoning_content": '<think>x</think>{"verdict":"ship","findings":[]}'}
    )
    assert lar.parse_lane("rigor", "model", text, 0.0).verdict == "ship"


def test_content_channel_still_wins_and_think_is_stripped() -> None:
    text = _ask_with(
        {
            "content": '<think>draft</think>{"verdict":"hold","findings":[]}',
            "reasoning_content": "ignored",
        }
    )
    assert "<think>" not in text
    assert lar.parse_lane("rigor", "model", text, 0.0).verdict == "hold"


def test_missing_reasoning_key_is_tolerated() -> None:
    assert _ask_with({"content": '{"verdict":"ship","findings":[]}'}).startswith("{")
