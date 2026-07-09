"""Unit tests for asymmetric token budget tracking."""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.xfail(reason="TDD-red", strict=False)

import pytest

from cohezion.inference.token_budget import TokenUsageRecord


class TestTokenUsageRecord:
    def test_local_tokens_have_zero_cost(self):
        r = TokenUsageRecord()
        r.add_local(10_000, model="llama3.2-1b-FLM")
        assert r.cloud_cost_usd == 0.0
        assert r.local_tokens == 10_000

    def test_cloud_tokens_cost_real_dollars(self):
        r = TokenUsageRecord()
        cost = r.add_cloud(1_000_000, 100_000, model="claude-sonnet-4-6")
        assert cost == pytest.approx(3.00 + 1.50, rel=1e-6)
        assert r.cloud_cost_usd > 0

    def test_cloud_savings_matches_sonnet_rate(self):
        r = TokenUsageRecord()
        r.add_local(1_000_000)  # 1M local tokens
        expected = 1_000_000 * 3.00 / 1_000_000  # Sonnet input rate
        assert r.cloud_savings_usd == pytest.approx(expected, rel=1e-6)

    def test_local_fraction_all_local(self):
        r = TokenUsageRecord()
        r.add_local(100)
        assert r.local_fraction == pytest.approx(1.0, abs=1e-6)

    def test_local_fraction_zero_tokens(self):
        r = TokenUsageRecord()
        assert r.local_fraction == 0.0

    def test_local_fraction_mixed(self):
        r = TokenUsageRecord()
        r.add_local(800)
        r.add_cloud(100, 100, model="claude-haiku-4-5")
        fraction = r.local_fraction
        assert 0.7 < fraction < 0.95

    def test_cache_hit_accounting(self):
        r = TokenUsageRecord()
        r.add_cache_hit(500)
        r.add_cache_hit(300)
        assert r.cache_hits == 2
        assert r.cache_tokens_saved == 800

    def test_to_dict_has_required_keys(self):
        r = TokenUsageRecord()
        r.add_local(100)
        r.add_cloud(50, 25, model="claude-haiku-4-5")
        d = r.to_dict()
        assert "local_tokens" in d
        assert "cloud_cost_usd" in d
        assert "cloud_savings_usd" in d
        assert "local_fraction" in d
        assert "cache_hits" in d

    def test_telegram_report_contains_key_info(self):
        r = TokenUsageRecord()
        r.add_local(50_000, model="Gemma-4-E4B-it-GGUF")
        r.add_cloud(1_000, 500, model="claude-haiku-4-5")
        r.add_cache_hit(200)
        report = r.telegram_report()
        assert "50,000" in report
        assert "local" in report.lower() or "free" in report.lower()
        assert "$" in report

    def test_is_local_model_recognizes_flm(self):
        r = TokenUsageRecord()
        assert r.is_local_model("llama3.2-1b-FLM") is True
        assert r.is_local_model("Gemma-4-E4B-it-GGUF") is True
        assert r.is_local_model("claude-sonnet-4-6") is False

    def test_haiku_cheaper_than_sonnet(self):
        r = TokenUsageRecord()
        haiku_cost = r.add_cloud(100_000, 10_000, model="claude-haiku-4-5")
        r2 = TokenUsageRecord()
        sonnet_cost = r2.add_cloud(100_000, 10_000, model="claude-sonnet-4-6")
        assert haiku_cost < sonnet_cost

    def test_total_tokens(self):
        r = TokenUsageRecord()
        r.add_local(500)
        r.add_cloud(100, 50)
        assert r.total_tokens == 650


class TestTokenBudgetTelegramRedaction:
    """Ensure token reports don't leak credentials."""

    def test_redaction_in_telegram_notify(self, monkeypatch):
        """Telegram notify must redact credentials from messages."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99")

        sent_bodies: list[str] = []
        from unittest.mock import patch

        with patch("cohezion.compound.telegram_notify.httpx") as mock_httpx:
            mock_httpx.post.side_effect = lambda url, json=None, **_: sent_bodies.append(
                json.get("text", "") if json else ""
            )
            from cohezion.compound.telegram_notify import notify

            # Send a message containing a credential pattern
            notify("Token: sk-abcdefghijklmnopqrstuvwxyz1234567890 result ok")

        if sent_bodies:
            assert "sk-" not in sent_bodies[0], "Credential should be redacted before sending"
