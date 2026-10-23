"""scripts/ci/local_adversarial_review.py::_ask must honour the local-LLM chat contract.

The chokepoint gate (scripts/ci/check_local_llm_chokepoint.sh) flagged `_ask` as a raw
chat/completions call site that read only ``message.content``. Two consequences:
  * a reasoning model that answers in ``reasoning_content`` (content == "") loses its
    verdict -> the lane reads as UNKNOWN;
  * a reply that drafts JSON inside ``<think>`` before the final answer can have the
    DRAFT parsed instead of the answer.
The fix delegates to ``gaia_adapter._answer_only`` (the shared contract). urlopen is
mocked: no request reaches the live router.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "local_adversarial_review.py"
_spec = importlib.util.spec_from_file_location("ci_local_adversarial_review", _SCRIPT)
assert _spec is not None and _spec.loader is not None
lar = importlib.util.module_from_spec(_spec)
sys.modules["ci_local_adversarial_review"] = lar
_spec.loader.exec_module(lar)


def _fake_urlopen(message: dict):
    def _urlopen(req, timeout=None):
        body = json.dumps({"choices": [{"message": message}]}).encode()
        return io.BytesIO(body)

    return _urlopen


SHIP = '{"verdict": "ship", "findings": []}'
HOLD_DRAFT = '{"verdict": "hold", "findings": [{"claim": "draft only"}]}'


def test_ask_falls_back_to_reasoning_content_when_content_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lar.urllib.request, "urlopen", _fake_urlopen({"content": "", "reasoning_content": SHIP})
    )
    text = lar._ask("m", "p")
    assert text == SHIP
    assert lar.parse_lane("l", "m", text, 0.0).verdict == "ship"


def test_ask_strips_think_block_so_draft_json_is_not_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lar.urllib.request,
        "urlopen",
        _fake_urlopen({"content": f"<think>{HOLD_DRAFT}</think>{SHIP}"}),
    )
    res = lar.parse_lane("l", "m", lar._ask("m", "p"), 0.0)
    assert res.verdict == "ship"
    assert res.findings == []


def test_ask_plain_content_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lar.urllib.request, "urlopen", _fake_urlopen({"content": SHIP}))
    assert lar._ask("m", "p") == SHIP
