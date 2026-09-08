# Specification: Producer and Consumer Wiring Audit

## Overview
This track focuses on auditing and remediating the wiring of the 5 core Datamesh connections within the Cohezion local fleet and inference stack. Specifically, it targets closing the gaps between event producers (such as execution monitoring, cache hits, and card alignment tracking) and their downstream consumers (including the Mycelium pattern aggregator and the daily researcher verification lane).

## Objectives
1. Audit the existing Datamesh connections to map out all active producers and consumers.
2. Remediate the Mycelium pattern verification gap by implementing a thread-safe shared singleton registry and querying mechanism in `MyceliumRegistry` (cross-agent pattern aggregator).
3. Connect the daily researcher's `verify_evolve.py` lane to the live `MyceliumRegistry` singleton for quantitative pattern verification.
4. Update `CardAlignmentMonitor` to track and emit model IDs within its `HEALING_EVENT` payloads.
5. Remediate the Ouroboros healing query gap by implementing a SurrealDB-backed query in `verify_evolve.py` to identify recent model-specific `HEALING_EVENT`s using sanitized inputs.

## Functional Requirements

### 1. Thread-Safe Mycelium Registry Singleton (`src/cohezion/mycelium/registry.py`)
- **Singleton Implementation**:
  - Implement a thread-safe singleton pattern using a `threading.Lock` inside `get_instance()` and `reset_instance()`.
- **Memory Bounding**:
  - Bound the size of the cluster list (max 500 clusters). If exceeded, evict the oldest inactive cluster (FIFO eviction based on centroid updates).
- **Cluster Tracking**:
  - Add `member_families: set[str]` and `member_tasks: set[str]` to `MyceliumCluster` to track unique families and tasks associated with members in the cluster.
- **Pattern Query Interface**:
  - Implement the query method:
    ```python
    def query_patterns(self, family: str, task: str) -> list[dict]:
        """Query matching pattern clusters.
        
        Returns:
            list[dict]: A list of matching clusters represented as dicts containing:
                - "family": str
                - "task": str
                - "size": int
                - "cluster_id": str
                - "mean_coherence": float
        """
    ```

### 2. Card Alignment Monitor (`src/cohezion/ouroboros/card_alignment_monitor.py`)
- **Model Tracking**:
  - Update `__init__` to accept an optional `model_id: str | None = None`.
- **Payload Schema**:
  - In `_emit_healing_event(self, rate: float)`, the `HEALING_EVENT` payload must adhere to the following schema:
    ```json
    {
      "source": "ouroboros.card_alignment_monitor",
      "model_id": "<model_id>",
      "rate": <float>,
      "threshold": <float>,
      "window_size": <int>,
      "timestamp": <float>
    }
    ```

### 3. Verification Lane Integration (`src/cohezion/researcher/lanes/verify_evolve.py`)
- **Mycelium Query Wiring**:
  - In `_query_mycelium_patterns(self, model_id: str, task: str) -> list[dict]`, resolve the model family using `cohezion.inference.default_profiles.get_profile(model_id).family`.
  - Fetch the thread-safe `MyceliumRegistry.get_instance()` and query it using `query_patterns(family, task)`.
- **Ouroboros Healing Event Wiring**:
  - Wire `_query_ouroboros_healing_events(self, model_id: str) -> list[dict]` to perform an HTTP query against SurrealDB's `precipitation_event` table.
- **Security & Resiliency (SurrealDB queries)**:
  - **Sourcing Credentials**: Read SurrealDB credentials strictly from env variables (`SURREALDB_URL`, `SURREALDB_USER`, `SURREALDB_PASS`).
  - **Input Sanitization**: Validate that `model_id` contains only alphanumeric characters, colons, and dashes before interpolating it into the SurrealQL query string to prevent SQL injection.
  - **Timeout & Retry**: Set a strict connection timeout of 2.0s. Implement a simple retry loop with exponential backoff (up to 3 retries, starting at 100ms backoff) using `asyncio.sleep`.

## Non-Functional Requirements
- **Code Quality**: Maintain Black formatting (88-char limit), strict type hints (mypy compatible), and NumPy-style docstrings for all new or modified methods.
- **Zero Regressions**: Ensure `make test-fast` returns a passing result (excluding pre-existing integration test failures).

## Acceptance Criteria
1. The `MyceliumRegistry` singleton successfully accumulates clusters from the `PrecipitationBus` concurrently.
2. `verify_evolve.py` fetches and filters Mycelium clusters in-memory during verification without crashing.
3. `verify_evolve.py` queries SurrealDB to verify recent healing events safely (SQL-injection safe).
4. New unit tests verify:
   - Singleton behavior with concurrent thread access.
   - Cluster list bounding and FIFO eviction when limits are reached.
   - Input sanitization and error handling (failed DB query) in the daily researcher.

## Out of Scope
- Auditing or editing external messaging/integration systems (Telegram hub, Robinhood MCP tools).
- Modifying the underlying 12D manifold simulation algorithms or the FLUME VAE model.
