"""Coverage batch Z40: security_auth, platform_mcp_server, arc_agi3_wrapper, flume_tokenizer, trained_navigator."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# Module 1: security/auth.py
# ---------------------------------------------------------------------------


class TestSecurityAuth:
    def test_verify_api_key_valid(self):
        from cohezion.security.auth import API_KEYS, verify_api_key

        valid_key = next(iter(API_KEYS))
        result = verify_api_key(valid_key)
        assert result["role"] == "admin"

    def test_verify_api_key_invalid_raises(self):
        from cohezion.security.auth import AuthError, verify_api_key

        with pytest.raises(AuthError):
            verify_api_key("bad-key-xyz-nonexistent")

    def test_verify_api_key_disabled_raises(self):
        from cohezion.security.auth import AuthError, verify_api_key

        with patch(
            "cohezion.security.auth.API_KEYS",
            {"test-key": {"name": "test", "role": "user", "enabled": False}},
        ):
            with pytest.raises(AuthError):
                verify_api_key("test-key")

    def test_create_token_returns_string(self):
        from cohezion.security.auth import create_token

        token = create_token({"user": "alice"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_round_trip(self):
        from cohezion.security.auth import create_token, verify_token

        payload = {"user": "alice", "sub": "user_id_123"}
        token = create_token(payload)
        decoded = verify_token(token)
        assert decoded["user"] == "alice"
        assert decoded["sub"] == "user_id_123"

    def test_verify_token_invalid_raises(self):
        from cohezion.security.auth import AuthError, verify_token

        with pytest.raises(AuthError):
            verify_token("definitely-not-a-jwt-token")

    def test_create_token_with_expires_delta(self):
        from datetime import timedelta

        from cohezion.security.auth import create_token, verify_token

        token = create_token({"user": "bob"}, expires_delta=timedelta(hours=2))
        decoded = verify_token(token)
        assert decoded["user"] == "bob"

    def test_hash_password_and_verify(self):
        from cohezion.security.auth import hash_password, verify_password

        # Mock pwd_context since passlib/bcrypt has a wrap-bug detection issue in this env
        with patch("cohezion.security.auth.pwd_context") as mock_ctx:
            mock_ctx.hash.return_value = "hashed:pass"
            mock_ctx.verify.side_effect = lambda plain, hashed: (
                hashed == "hashed:pass" and plain == "correct"
            )
            hashed = hash_password("correct")
            assert hashed == "hashed:pass"
            assert verify_password("correct", hashed) is True
            assert verify_password("wrong", hashed) is False

    def test_check_role_admin_beats_user(self):
        from cohezion.security.auth import check_role

        assert check_role("admin", "user") is True
        assert check_role("admin", "readonly") is True
        assert check_role("admin", "admin") is True

    def test_check_role_user_beats_readonly(self):
        from cohezion.security.auth import check_role

        assert check_role("user", "readonly") is True
        assert check_role("user", "user") is True

    def test_check_role_user_fails_admin(self):
        from cohezion.security.auth import check_role

        assert check_role("user", "admin") is False

    def test_check_role_unknown_role_is_zero(self):
        from cohezion.security.auth import check_role

        assert check_role("ghost", "readonly") is False


# ---------------------------------------------------------------------------
# Module 2: platform/mcp_server.py (ObsidianVaultMCP)
# ---------------------------------------------------------------------------


class TestObsidianVaultMCP:
    def test_write_and_read_artifact(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        mcp = ObsidianVaultMCP(vault_path=str(tmp_path))
        success = asyncio.run(mcp.write_markdown_artifact("test.md", "Hello World", tags=["test"]))
        assert success is True

        content = asyncio.run(mcp.read_markdown_artifact("test.md"))
        assert "Hello World" in content
        assert "test" in content

    def test_write_artifact_no_tags(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        mcp = ObsidianVaultMCP(vault_path=str(tmp_path))
        success = asyncio.run(mcp.write_markdown_artifact("notags.md", "No tags here"))
        assert success is True

    def test_read_artifact_not_found(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        mcp = ObsidianVaultMCP(vault_path=str(tmp_path))
        result = asyncio.run(mcp.read_markdown_artifact("nonexistent.md"))
        assert result is None

    def test_write_artifact_red_wall_violation(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        mcp = ObsidianVaultMCP(vault_path=str(tmp_path))
        # Try to write outside the vault using path traversal
        result = asyncio.run(mcp.write_markdown_artifact("../escape.md", "evil"))
        assert result is False

    def test_read_artifact_red_wall_violation(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        mcp = ObsidianVaultMCP(vault_path=str(tmp_path))
        result = asyncio.run(mcp.read_markdown_artifact("../escape.md"))
        assert result is None

    def test_write_creates_vault_dir_if_missing(self, tmp_path):
        from cohezion.platform.mcp_server import ObsidianVaultMCP

        vault_dir = tmp_path / "new_vault"
        mcp = ObsidianVaultMCP(vault_path=str(vault_dir))
        asyncio.run(mcp.write_markdown_artifact("note.md", "content"))
        assert vault_dir.exists()


# ---------------------------------------------------------------------------
# Module 3: swarm/agents/arc_agi_3_wrapper.py
# ---------------------------------------------------------------------------


class TestArcAgi3Wrapper:
    def test_recursive_cot_forward_shape(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought

        model = RecursiveChainOfThought(dim=64, depth=4, threshold=0.0)
        z = torch.randn(1, 64)
        out = model(z)
        assert out.shape == (1, 64)

    def test_recursive_cot_compute_entropy(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought

        model = RecursiveChainOfThought(dim=16)
        z = torch.randn(1, 16)
        entropy = model.compute_entropy(z)
        assert entropy.shape == (1,)
        assert entropy.item() >= 0

    def test_recursive_cot_dynamic_exit(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought

        # Very high threshold forces early exit
        model = RecursiveChainOfThought(dim=32, depth=10, threshold=100.0)
        z = torch.randn(1, 32)
        out = model(z, steps=10)
        assert out.shape == (1, 32)

    def test_recursive_cot_custom_steps(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought

        model = RecursiveChainOfThought(dim=32, depth=8, threshold=0.0)
        z = torch.randn(1, 32)
        out = model(z, steps=3)
        assert out.shape == (1, 32)

    def test_arc_env_reset(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import ARCAGI3Env

        env = ARCAGI3Env(task_id="test_task")
        obs, info = env.reset(seed=42)
        assert obs.shape == (256,)
        assert isinstance(info, dict)

    def test_arc_env_step(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import ARCAGI3Env

        env = ARCAGI3Env(task_id="test_task")
        env.reset()
        obs, reward, done, truncated, info = env.step(0)
        assert obs.shape == (256,)
        assert reward == pytest.approx(0.1)
        assert done is False

    def test_arc_env_action_space(self):
        from cohezion.swarm.agents.arc_agi_3_wrapper import ARCAGI3Env

        env = ARCAGI3Env(task_id="test_task")
        assert env.action_space.n == 10


# ---------------------------------------------------------------------------
# Module 4: swarm/autoresearch/base.py
# ---------------------------------------------------------------------------


class TestAutoresearchBase:
    def _make_driver(self):
        from cohezion.swarm.autoresearch.base import ExperimentResult, ResearchDriver

        class ConcreteDriver(ResearchDriver):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._nodes = ["node1", "node2"]

            def select_next_node(self):
                return self._nodes.pop(0) if self._nodes else None

            def generate_candidate(self, node):
                return f"code_for_{node}"

            def evaluate_candidate(self, candidate):
                return ExperimentResult(success=True, metric=0.8)

            def update_model(self, node, result):
                pass

        return ConcreteDriver(objective="improve coverage", time_budget_seconds=60)

    def test_experiment_result_success(self):
        from cohezion.swarm.autoresearch.base import ExperimentResult

        r = ExperimentResult(success=True, metric=0.9)
        assert r.success is True
        assert r.metric == pytest.approx(0.9)

    def test_experiment_result_failure(self):
        from cohezion.swarm.autoresearch.base import ExperimentResult

        r = ExperimentResult(success=False, error="timeout")
        assert r.success is False
        assert r.error == "timeout"

    def test_driver_init(self):
        driver = self._make_driver()
        assert driver.objective == "improve coverage"
        assert driver.cycles == 0

    def test_run_cycle_success(self):
        driver = self._make_driver()
        result = driver.run_cycle()
        assert result is True
        assert driver.cycles == 1

    def test_run_cycle_returns_false_when_no_nodes(self):
        driver = self._make_driver()
        driver._nodes = []  # no more nodes
        result = driver.run_cycle()
        assert result is False

    def test_run_continuous_limited(self):
        driver = self._make_driver()
        driver.run_continuous(max_cycles=2)
        assert driver.cycles == 2

    def test_run_continuous_stops_on_no_node(self):
        driver = self._make_driver()
        driver._nodes = ["only_one"]
        driver.run_continuous(max_cycles=5)
        assert driver.cycles == 2  # one success + one no-node stop


# ---------------------------------------------------------------------------
# Module 5: pipeline/trained_navigator.py
# ---------------------------------------------------------------------------


class TestTrainedNavigator:
    def _make_navigator(self, z_dim=32):
        from cohezion.pipeline.trained_navigator import TrainedNavigator

        mock_policy = MagicMock()
        mock_policy.return_value = (torch.randn(4, z_dim), torch.ones(4, z_dim))

        # WeightBridge is lazy-imported inside __init__; patch at source module
        with patch(
            "cohezion.pipeline.weight_bridge.WeightBridge.load_policy_network",
            return_value=mock_policy,
        ):
            nav = TrainedNavigator(checkpoint_path="/fake/checkpoint.pt", action_scale=0.1)
        nav.policy = mock_policy
        return nav, z_dim

    def test_navigate_batch_output_shape(self):
        nav, z_dim = self._make_navigator(z_dim=32)
        states = np.random.randn(4, z_dim).astype(np.float32)
        deltas = nav.navigate_batch(states)
        assert deltas.shape == (4, z_dim)

    def test_navigate_batch_applies_action_scale(self):
        nav, z_dim = self._make_navigator(z_dim=16)
        # Make policy return a known tensor
        nav.policy.return_value = (torch.ones(1, z_dim), torch.ones(1, z_dim))
        states = np.ones((1, z_dim), dtype=np.float32)
        deltas = nav.navigate_batch(states)
        # All values should be ~action_scale (0.1) since output is ones * 0.1
        assert np.allclose(deltas, 0.1, atol=1e-5)

    def test_navigate_single_output_shape(self):
        nav, z_dim = self._make_navigator(z_dim=32)
        state = np.random.randn(z_dim).astype(np.float32)
        delta = nav.navigate_single(state)
        assert delta.shape == (z_dim,)

    def test_checkpoint_path_property(self):
        nav, _ = self._make_navigator()
        assert nav.checkpoint_path == Path("/fake/checkpoint.pt")

    def test_navigate_batch_dtype_is_float32(self):
        nav, z_dim = self._make_navigator(z_dim=8)
        states = np.random.randn(2, z_dim).astype(np.float32)
        deltas = nav.navigate_batch(states)
        assert deltas.dtype == np.float32
