"""GET /rl/policy/{agent_id} reports an uninspectable checkpoint as existing (200), never 500.

torch.load(weights_only=True) raises pickle.UnpicklingError on a checkpoint holding a non-tensor
object (ppo_trainer saves its config dataclass) and EOFError/UnpicklingError on a corrupt file.
The pre-#267 handler returned 200 {"exists": true}; the extracted one narrowed its except clause
and returned 500.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import torch
from httpx import ASGITransport, AsyncClient

from cohezion.api import app


@dataclass
class _Config:
    lr: float = 3e-4


async def _get(agent_id: str) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/rl/policy/{agent_id}")
    return resp.status_code, resp.json()


@pytest.fixture
def ckpt_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)  # the handler resolves data/rl/checkpoints relative to cwd
    d = tmp_path / "data" / "rl" / "checkpoints"
    d.mkdir(parents=True)
    return d


@pytest.mark.asyncio
async def test_ppo_style_checkpoint_is_reported_not_500(ckpt_dir: Path) -> None:
    torch.save({"policy_state": {}, "config": _Config()}, ckpt_dir / "policy_ppo.pt")
    status, body = await _get("ppo")
    assert status == 200 and body["exists"] is True and body["parameters"] is None


@pytest.mark.asyncio
async def test_corrupt_checkpoint_is_reported_not_500(ckpt_dir: Path) -> None:
    (ckpt_dir / "policy_junk.pt").write_bytes(b"\x80not a checkpoint")
    status, body = await _get("junk")
    assert status == 200 and body["exists"] is True


@pytest.mark.asyncio
async def test_missing_checkpoint_is_reported_absent(ckpt_dir: Path) -> None:
    assert await _get("nobody") == (200, {"exists": False, **_absent_defaults()})


def _absent_defaults() -> dict:
    from cohezion.api.routes.rl import RLPolicyResponse

    return {k: v for k, v in RLPolicyResponse(exists=False).model_dump().items() if k != "exists"}
