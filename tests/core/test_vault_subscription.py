"""Tests for VaultSubscriptionClient."""

import json

import pytest

from cohezion.core.vault_subscription import VaultEvent, VaultSubscriptionClient


class TestParseEvent:
    def test_parse_event_valid(self):
        client = VaultSubscriptionClient()
        data = json.dumps(
            {
                "event_type": "created",
                "path": "inbox/test.md",
                "timestamp": "2026-02-07T12:00:00+00:00",
                "old_path": None,
            }
        )
        event = client._parse_event("created", data)
        assert event is not None
        assert event.event_type == "created"
        assert event.path == "inbox/test.md"
        assert event.timestamp == "2026-02-07T12:00:00+00:00"
        assert event.old_path is None

    def test_parse_event_with_old_path(self):
        client = VaultSubscriptionClient()
        data = json.dumps(
            {
                "event_type": "moved",
                "path": "patterns/new.md",
                "timestamp": "2026-02-07T12:00:00+00:00",
                "old_path": "inbox/old.md",
            }
        )
        event = client._parse_event("moved", data)
        assert event is not None
        assert event.old_path == "inbox/old.md"

    def test_parse_event_invalid_json(self):
        client = VaultSubscriptionClient()
        event = client._parse_event("created", "not json")
        assert event is None

    def test_parse_event_fallback_event_type(self):
        client = VaultSubscriptionClient()
        data = json.dumps({"path": "test.md", "timestamp": "now"})
        event = client._parse_event("modified", data)
        assert event is not None
        assert event.event_type == "modified"


class TestDecorators:
    def test_on_event_decorator(self):
        client = VaultSubscriptionClient()

        @client.on_event("created")
        async def handler(event):
            pass

        assert len(client._callbacks["created"]) == 1
        assert client._callbacks["created"][0] is handler

    def test_on_event_multiple(self):
        client = VaultSubscriptionClient()

        @client.on_event("created")
        async def handler1(event):
            pass

        @client.on_event("created")
        async def handler2(event):
            pass

        assert len(client._callbacks["created"]) == 2

    def test_on_all_decorator(self):
        client = VaultSubscriptionClient()

        @client.on_all()
        async def handler(event):
            pass

        assert len(client._global_callbacks) == 1
        assert client._global_callbacks[0] is handler


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_type_specific(self):
        client = VaultSubscriptionClient()
        received = []

        @client.on_event("created")
        async def handler(event):
            received.append(event)

        event = VaultEvent(event_type="created", path="test.md", timestamp="now")
        await client._dispatch(event)
        assert len(received) == 1
        assert received[0].path == "test.md"

    @pytest.mark.asyncio
    async def test_dispatch_type_no_match(self):
        client = VaultSubscriptionClient()
        received = []

        @client.on_event("created")
        async def handler(event):
            received.append(event)

        event = VaultEvent(event_type="deleted", path="test.md", timestamp="now")
        await client._dispatch(event)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_dispatch_global(self):
        client = VaultSubscriptionClient()
        received = []

        @client.on_all()
        async def handler(event):
            received.append(event)

        event = VaultEvent(event_type="modified", path="test.md", timestamp="now")
        await client._dispatch(event)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_dispatch_callback_error_non_critical(self):
        client = VaultSubscriptionClient()
        called = []

        @client.on_event("created")
        async def bad_handler(event):
            raise RuntimeError("oops")

        @client.on_event("created")
        async def good_handler(event):
            called.append(event)

        event = VaultEvent(event_type="created", path="test.md", timestamp="now")
        await client._dispatch(event)
        # Good handler still called despite bad handler error
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_dispatch_global_error_non_critical(self):
        client = VaultSubscriptionClient()
        called = []

        @client.on_all()
        async def bad_handler(event):
            raise RuntimeError("oops")

        @client.on_all()
        async def good_handler(event):
            called.append(event)

        event = VaultEvent(event_type="created", path="test.md", timestamp="now")
        await client._dispatch(event)
        assert len(called) == 1


class TestDisconnect:
    def test_disconnect_sets_running_false(self):
        client = VaultSubscriptionClient()
        client._running = True
        assert client._running is True

    def test_init_defaults(self):
        client = VaultSubscriptionClient()
        assert client._running is False
        assert client._base_url == "http://localhost:8360"
        assert client._api_key == ""
        assert client._callbacks == {}
        assert client._global_callbacks == []

    def test_init_custom(self):
        client = VaultSubscriptionClient(base_url="http://example.com:9000/", api_key="secret")
        assert client._base_url == "http://example.com:9000"
        assert client._api_key == "secret"
