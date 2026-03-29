"""Tests for OllamaCloudProvider."""

from __future__ import annotations


class TestOllamaCloudProvider:
    def test_init_without_url_uses_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_CLOUD_URL", raising=False)
        from cohezion.swarm.providers.ollama_cloud_provider import OllamaCloudProvider

        provider = OllamaCloudProvider(config={})
        assert provider.base_url == "https://api.ollama.com"

    def test_init_with_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_CLOUD_URL", "https://cloud.ollama.com")
        monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-key-123")
        from cohezion.swarm.providers.ollama_cloud_provider import OllamaCloudProvider

        provider = OllamaCloudProvider()
        assert provider.base_url == "https://cloud.ollama.com"
        assert provider._api_key == "cloud-key-123"

    def test_inherits_ollama_provider(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_CLOUD_URL", "https://cloud.ollama.com")
        from cohezion.swarm.providers.ollama_cloud_provider import OllamaCloudProvider
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaCloudProvider()
        assert isinstance(provider, OllamaProvider)

    def test_timeout_default_is_120(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_CLOUD_URL", "https://cloud.ollama.com")
        from cohezion.swarm.providers.ollama_cloud_provider import OllamaCloudProvider

        provider = OllamaCloudProvider()
        assert provider.timeout == 120
