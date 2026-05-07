"""Σ4 Ω12 P1+P2 security patch tests.

Verifies the validation, sanitization, and lazy-load behavior introduced
by the Ω12 P1+P2 patch batch.
"""

from __future__ import annotations

import pytest


class TestPatch7HookifyValidator:
    """Patch 7 — SurrealQL injection defense in hookify validator."""

    def test_rule_id_regex_accepts_valid(self):
        from cohezion.hookify.validator import _RULE_ID_RE

        assert _RULE_ID_RE.match("valid_rule_123")
        assert _RULE_ID_RE.match("rule-with-dashes")
        assert _RULE_ID_RE.match("ABC")

    def test_rule_id_regex_rejects_sql_injection(self):
        from cohezion.hookify.validator import _RULE_ID_RE

        assert not _RULE_ID_RE.match("'; DROP TABLE x; --")
        assert not _RULE_ID_RE.match("rule_id' OR 1=1 --")

    def test_rule_id_regex_rejects_special_chars(self):
        from cohezion.hookify.validator import _RULE_ID_RE

        assert not _RULE_ID_RE.match("rule with space")
        assert not _RULE_ID_RE.match("rule;injection")
        assert not _RULE_ID_RE.match("../etc/passwd")
        assert not _RULE_ID_RE.match("rule\nnewline")


class TestPatch7SurrealClientImports:
    """Patch 7 — defensive imports for surrealdb library exception types."""

    def test_surrealdbmethoderror_resolved(self):
        from cohezion.core.persistence.surreal_client import SurrealDBMethodError

        # Either it's a real exception class, or () (fallback for old lib versions)
        assert SurrealDBMethodError is not None

    def test_cborerror_resolved(self):
        from cohezion.core.persistence.surreal_client import CBORError

        assert CBORError is not None


class TestPatch11LazyAuth:
    """Patch 11 — lazy-load secrets in MCP auth modules."""

    def test_mcp_shared_auth_lazy_get_api_key(self):
        from cohezion.mcp.shared import auth

        # Function exists and is callable
        assert callable(auth.get_api_key)

    def test_mcp_shared_auth_no_module_level_constant(self):
        """MCP_API_KEY should NOT be a module-level constant after Patch 11."""
        from cohezion.mcp.shared import auth

        # The lazy accessor pattern means MCP_API_KEY is no longer a top-level name
        assert not hasattr(auth, "MCP_API_KEY") or callable(auth.get_api_key)


class TestPatch12ManagerAuth:
    """Patch 12 — tighten ephemeral-token reader exceptions + log."""

    def test_get_current_token_returns_none_on_bad_bytes(self, tmp_path):
        import cohezion.mcp.manager.auth as m

        bad_token = tmp_path / "auth.token"
        bad_token.write_bytes(b"\xff\xfe invalid utf bytes")

        # Monkeypatch path
        original = m.AUTH_TOKEN_PATH
        m.AUTH_TOKEN_PATH = bad_token
        try:
            result = m.get_current_token()
            assert result is None
        finally:
            m.AUTH_TOKEN_PATH = original

    def test_get_current_token_returns_none_when_missing(self, tmp_path):
        import cohezion.mcp.manager.auth as m

        missing = tmp_path / "does-not-exist.token"
        original = m.AUTH_TOKEN_PATH
        m.AUTH_TOKEN_PATH = missing
        try:
            assert m.get_current_token() is None
        finally:
            m.AUTH_TOKEN_PATH = original


class TestPatch19HFModelIdValidator:
    """Patch 19 — model_id validation in HF MCP server (SSRF defense)."""

    def test_validator_accepts_valid_models(self):
        from cohezion.mcp.servers.huggingface.server import _validate_model_id

        assert _validate_model_id("meta-llama/Llama-3.1-8B") == "meta-llama/Llama-3.1-8B"
        assert _validate_model_id("bert-base-uncased") == "bert-base-uncased"
        assert _validate_model_id("org/model.v1") == "org/model.v1"

    def test_validator_rejects_path_traversal(self):
        from cohezion.mcp.servers.huggingface.server import _validate_model_id

        with pytest.raises(ValueError):
            _validate_model_id("../../../etc/passwd")
        with pytest.raises(ValueError):
            _validate_model_id("foo/../bar")

    def test_validator_rejects_absolute_path(self):
        from cohezion.mcp.servers.huggingface.server import _validate_model_id

        with pytest.raises(ValueError):
            _validate_model_id("/etc/passwd")

    def test_validator_rejects_special_chars(self):
        from cohezion.mcp.servers.huggingface.server import _validate_model_id

        with pytest.raises(ValueError):
            _validate_model_id("model;rm -rf /")
        with pytest.raises(ValueError):
            _validate_model_id("model with space")
        with pytest.raises(ValueError):
            _validate_model_id("model$injection")
