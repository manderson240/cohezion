"""V-model structural invariant tests for DataMesh EventBridge.

Structural tests verify interface contracts (types, presence of fields, method
signatures) before behavioral tests. All SurrealDB calls are mocked.
"""

import inspect

from cohezion.core.event_bus import EventType


class TestDataMeshEventTypesStructure:
    """O7: DataMesh EventType enum structural invariants."""

    def test_data_product_created_exists(self):
        """O7a: DATA_PRODUCT_CREATED must be a member of EventType."""
        assert hasattr(EventType, "DATA_PRODUCT_CREATED"), (
            "DATA_PRODUCT_CREATED missing from EventType — agents cannot react to new data products"
        )

    def test_data_product_updated_exists(self):
        """O7b: DATA_PRODUCT_UPDATED must be a member of EventType."""
        assert hasattr(EventType, "DATA_PRODUCT_UPDATED"), (
            "DATA_PRODUCT_UPDATED missing from EventType"
        )

    def test_data_product_quality_alert_exists(self):
        """O7c: DATA_PRODUCT_QUALITY_ALERT must be a member of EventType."""
        assert hasattr(EventType, "DATA_PRODUCT_QUALITY_ALERT"), (
            "DATA_PRODUCT_QUALITY_ALERT missing — corpus quality consumer cannot subscribe"
        )

    def test_lineage_updated_exists(self):
        """O7d: LINEAGE_UPDATED must be a member of EventType."""
        assert hasattr(EventType, "LINEAGE_UPDATED")

    def test_domain_health_degraded_exists(self):
        """O7e: DOMAIN_HEALTH_DEGRADED must be a member of EventType."""
        assert hasattr(EventType, "DOMAIN_HEALTH_DEGRADED")

    def test_datamesh_events_are_distinct(self):
        """O7f: DISCRIMINATING — all DataMesh event types must have distinct integer values.

        A wrong implementation might alias two variants to the same auto() slot
        if the enum class body is malformed. This test catches that.
        """
        datamesh_members = [
            EventType.DATA_PRODUCT_CREATED,
            EventType.DATA_PRODUCT_UPDATED,
            EventType.DATA_PRODUCT_QUALITY_ALERT,
            EventType.LINEAGE_UPDATED,
            EventType.DOMAIN_HEALTH_DEGRADED,
        ]
        values = [e.value for e in datamesh_members]
        assert len(values) == len(set(values)), (
            "DataMesh EventType values are not all distinct — enum aliasing bug"
        )

    def test_datamesh_events_do_not_overlap_core(self):
        """O7g: DISCRIMINATING — DataMesh event values must not collide with core events.

        If auto() slots overlap (e.g. two enum blocks sharing the same counter),
        routing by EventType would silently fire the wrong handlers.
        """
        core_members = {
            EventType.AGENT_START,
            EventType.AGENT_COMPLETE,
            EventType.AGENT_ERROR,
            EventType.LLM_CALL,
            EventType.LLM_RESPONSE,
            EventType.CACHE_HIT,
            EventType.CACHE_MISS,
            EventType.DB_QUERY,
            EventType.DB_ERROR,
            EventType.SECURITY_VIOLATION,
            EventType.METRIC_UPDATE,
            EventType.SYSTEM_HEALTH,
            EventType.JOURNEY_STEP,
            EventType.CUSTOM,
        }
        datamesh_members = {
            EventType.DATA_PRODUCT_CREATED,
            EventType.DATA_PRODUCT_UPDATED,
            EventType.DATA_PRODUCT_QUALITY_ALERT,
            EventType.LINEAGE_UPDATED,
            EventType.DOMAIN_HEALTH_DEGRADED,
        }
        overlap = {m.value for m in core_members} & {m.value for m in datamesh_members}
        assert not overlap, f"DataMesh EventType values collide with core: {overlap}"


class TestDataMeshEventBridgeStructure:
    """O8: DataMeshEventBridge structural signature invariants."""

    def test_event_bridge_importable(self):
        """O8a: DataMeshEventBridge must be importable from data_mesh.event_bridge."""
        from cohezion.data_mesh.event_bridge import DataMeshEventBridge  # noqa: F401

    def test_event_bridge_subscribe_signature(self):
        """O8b: DataMeshEventBridge.subscribe must accept an EventBus."""
        from cohezion.data_mesh.event_bridge import DataMeshEventBridge

        sig = inspect.signature(DataMeshEventBridge.subscribe)
        assert "bus" in sig.parameters, "subscribe() missing 'bus' parameter"

    def test_event_bridge_replay_since_signature(self):
        """O8c: replay_since must accept a float timestamp and return a list.

        DISCRIMINATING — a wrong implementation might return a dict or coroutine
        rather than a plain list. This catches that without needing SurrealDB live.
        """
        from cohezion.data_mesh.event_bridge import DataMeshEventBridge

        sig = inspect.signature(DataMeshEventBridge.replay_since)
        assert "since_ts" in sig.parameters, "replay_since() missing 'since_ts' parameter"

    def test_event_bridge_surreal_table_name(self):
        """O8d: DISCRIMINATING — DataMeshEventBridge must use exactly 'data_product_event'.

        A wrong table name (e.g. 'datamesh_event' or 'data_mesh_event') would
        silently write to a different table, making replay_since return no rows.
        """
        from cohezion.data_mesh.event_bridge import DataMeshEventBridge

        assert DataMeshEventBridge.TABLE == "data_product_event", (
            f"Wrong table name '{DataMeshEventBridge.TABLE}'; "
            "replay_since() would find no rows if table name drifts"
        )

    def test_event_bridge_subscribes_to_all_datamesh_types(self):
        """O8e: DataMeshEventBridge.SUBSCRIBED_TYPES must cover all 5 DataMesh EventTypes."""
        from cohezion.data_mesh.event_bridge import DataMeshEventBridge

        required = {
            EventType.DATA_PRODUCT_CREATED,
            EventType.DATA_PRODUCT_UPDATED,
            EventType.DATA_PRODUCT_QUALITY_ALERT,
            EventType.LINEAGE_UPDATED,
            EventType.DOMAIN_HEALTH_DEGRADED,
        }
        missing = required - set(DataMeshEventBridge.SUBSCRIBED_TYPES)
        assert not missing, f"DataMeshEventBridge does not subscribe to: {missing}"


class TestCorpusQualityConsumerStructure:
    """O9: CorpusQualityConsumer structural signature invariants."""

    def test_corpus_quality_consumer_importable(self):
        """O9a: CorpusQualityConsumer must be importable from data_mesh.corpus_quality_consumer."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer  # noqa: F401

    def test_subscribe_signature(self):
        """O9b: CorpusQualityConsumer.subscribe must accept an EventBus."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        sig = inspect.signature(CorpusQualityConsumer.subscribe)
        assert "bus" in sig.parameters

    def test_subscribes_to_quality_alert_only(self):
        """O9c: DISCRIMINATING — CorpusQualityConsumer must subscribe ONLY to QUALITY_ALERT.

        If it subscribed to DATA_PRODUCT_UPDATED as well, every routine catalog
        refresh would trigger a Lemonade augmentation batch — burning iGPU budget
        for traces that don't need improvement yet.
        """
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        subscribed = set(CorpusQualityConsumer.SUBSCRIBED_TYPES)
        assert subscribed == {EventType.DATA_PRODUCT_QUALITY_ALERT}, (
            f"CorpusQualityConsumer subscribes to wrong set: {subscribed}. "
            "Should be exactly {DATA_PRODUCT_QUALITY_ALERT}."
        )

    def test_handle_calls_augment_batch(self):
        """O9d: DISCRIMINATING — handle() must call augment_batch, not a stub.

        A wrong implementation might log and return without calling the augmentor,
        meaning the corpus never actually improves.
        """
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        src = inspect.getsource(CorpusQualityConsumer._handle_quality_alert)
        assert "augment_batch" in src, (
            "_handle_quality_alert() does not call augment_batch() — "
            "corpus quality loop is silently broken"
        )

    def test_consumer_skill_filter_from_payload(self):
        """O9e: handle() must pass skill_filter from event payload when present."""
        from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer

        src = inspect.getsource(CorpusQualityConsumer._handle_quality_alert)
        assert "skill_filter" in src, (
            "skill_filter not passed from event payload — "
            "augmentation would process all skills even when alert is skill-specific"
        )
