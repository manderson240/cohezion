"""Integration tests for SurrealDB persistence layer.

Requires a running SurrealDB instance (v3.0+).

Run with: pytest tests/integration/test_surreal_persistence.py -m integration --asyncio-mode=auto

To start SurrealDB for testing:
    docker run -d --name surrealdb-test -p 8000:8000 surrealdb/surrealdb:v3.0.0 start --allow-all

Environment variables:
    SURREAL_URL: WebSocket URL (default: ws://localhost:8000/rpc)
    SURREAL_USER: Username (default: root)
    SURREAL_PASS: Password (default: root)
    SKIP_INTEGRATION: Set to "1" to skip these tests
"""

import contextlib
import os
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION") == "1",
    reason="Integration tests skipped (set SKIP_INTEGRATION=0 to run)",
)


@pytest.fixture(scope="module")
async def surreal_client():
    """Create and connect SurrealClient for integration tests."""
    from cohezion.core.persistence.surreal_client import SurrealClient

    client = SurrealClient(
        url=os.environ.get("SURREAL_URL", "ws://localhost:8000/rpc"),
        namespace="test_cohezion",
        database="test_persistence",
    )

    connected = await client.connect()
    if not connected:
        pytest.skip("Could not connect to SurrealDB")

    if client._using_fallback:
        pytest.skip("Using in-memory fallback, not real SurrealDB")

    await client.query("DEFINE NAMESPACE test_cohezion;")
    await client.query("DEFINE DATABASE test_persistence;")

    yield client

    with contextlib.suppress(Exception):
        await client.query("REMOVE DATABASE test_persistence;")
    await client.close()


@pytest.fixture
def unique_id() -> str:
    """Generate a unique ID for test data."""
    return uuid.uuid4().hex[:8]


class TestSurrealClientConnection:
    """Integration tests for SurrealClient basic operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_and_version(self, surreal_client):
        """Test basic connection and version check."""
        version = await surreal_client.version()
        assert version is not None
        assert len(version) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_is_alive(self, surreal_client):
        """Test health check."""
        alive = await surreal_client.is_alive()
        assert alive is True


class TestUniverseRepositoryIntegration:
    """Integration tests for SurrealUniverseRepository."""

    @pytest.fixture
    async def repo(self, surreal_client):
        from cohezion.core.persistence.repositories.surreal_universe_repository import (
            SurrealUniverseRepository,
        )

        await surreal_client.query("""
            DEFINE TABLE universe_nodes SCHEMALESS;
            DEFINE FIELD id ON TABLE universe_nodes TYPE string;
            DEFINE FIELD content ON TABLE universe_nodes TYPE string;
            DEFINE FIELD node_type ON TABLE universe_nodes TYPE string DEFAULT 'document';
        """)

        yield SurrealUniverseRepository(surreal_client)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_get_universe_node(self, repo, surreal_client, unique_id):
        """Test creating and retrieving a universe node."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        node = UniverseNode(
            id=f"test_{unique_id}",
            content="Test node for integration testing",
            embedding=[0.1] * 768,
            physics_state=PhysicsState(x=0.5, y=0.3, logic=0.9),
            node_type="test",
            metadata={"test": True},
        )

        created = await repo.create(node)
        assert created is True

        retrieved = await repo.get(f"test_{unique_id}")
        assert retrieved is not None
        assert retrieved.content == node.content
        assert retrieved.node_type == "test"
        assert abs(retrieved.physics_state.x - 0.5) < 0.01

        await surreal_client.query(f"DELETE universe_nodes WHERE id = universe_nodes:test_{unique_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_universe_node(self, repo, surreal_client, unique_id):
        """Test updating a universe node."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        node = UniverseNode(
            id=f"test_update_{unique_id}",
            content="Original content",
            physics_state=PhysicsState(),
            node_type="test",
            metadata={"version": 1},
        )

        await repo.create(node)

        updated = await repo.update(
            f"test_update_{unique_id}", {"content": "Updated content", "metadata": {"version": 2}}
        )
        assert updated is True

        retrieved = await repo.get(f"test_update_{unique_id}")
        assert retrieved is not None
        assert retrieved.content == "Updated content"

        await surreal_client.query(f"DELETE universe_nodes WHERE id = universe_nodes:test_update_{unique_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_universe_node(self, repo, surreal_client, unique_id):
        """Test deleting a universe node."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        node = UniverseNode(
            id=f"test_delete_{unique_id}",
            content="Node to be deleted",
            physics_state=PhysicsState(),
            node_type="test",
        )

        await repo.create(node)

        deleted = await repo.delete(f"test_delete_{unique_id}")
        assert deleted is True

        retrieved = await repo.get(f"test_delete_{unique_id}")
        assert retrieved is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_by_physics_range(self, repo, surreal_client, unique_id):
        """Test querying nodes by physics dimension range."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        nodes = [
            UniverseNode(
                id=f"physics_test_{unique_id}_{i}",
                content=f"Physics test node {i}",
                physics_state=PhysicsState(x=float(i) * 0.1, y=float(i) * 0.2),
                node_type="physics_test",
            )
            for i in range(5)
        ]

        for node in nodes:
            await repo.create(node)

        results = await repo.query_by_physics("x", min_val=0.15, max_val=0.35, limit=10)

        assert len(results) >= 2

        await surreal_client.query("DELETE universe_nodes WHERE node_type = 'physics_test'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_by_type(self, repo, surreal_client, unique_id):
        """Test querying nodes by type."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        for i in range(3):
            node = UniverseNode(
                id=f"type_test_{unique_id}_{i}",
                content=f"Type test node {i}",
                physics_state=PhysicsState(),
                node_type="type_test_unique",
            )
            await repo.create(node)

        results = await repo.query_by_type("type_test_unique", limit=10)

        assert len(results) >= 3

        await surreal_client.query("DELETE universe_nodes WHERE node_type = 'type_test_unique'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, repo, surreal_client, unique_id):
        """Test vector similarity search."""
        from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode

        node1 = UniverseNode(
            id=f"vec_sim_1_{unique_id}",
            content="Document about machine learning",
            embedding=[0.1] * 100 + [0.9] * 100 + [0.1] * 568,
            physics_state=PhysicsState(logic=0.9),
            node_type="vec_test",
        )
        node2 = UniverseNode(
            id=f"vec_sim_2_{unique_id}",
            content="Document about cooking recipes",
            embedding=[0.9] * 100 + [0.1] * 100 + [0.5] * 568,
            physics_state=PhysicsState(biology=0.8),
            node_type="vec_test",
        )

        await repo.create(node1)
        await repo.create(node2)

        query_embedding = [0.1] * 100 + [0.9] * 100 + [0.1] * 568
        results = await repo.search_similar(query_embedding, limit=5)

        assert len(results) >= 1

        await surreal_client.query("DELETE universe_nodes WHERE node_type = 'vec_test'")


class TestSkillRepositoryIntegration:
    """Integration tests for SurrealSkillRepository."""

    @pytest.fixture
    async def repo(self, surreal_client):
        from cohezion.core.persistence.repositories.surreal_skill_repository import (
            SurrealSkillRepository,
        )

        await surreal_client.query("""
            DEFINE TABLE skill SCHEMALESS;
            DEFINE FIELD name ON skill TYPE string;
            DEFINE FIELD keywords ON skill TYPE array;
            DEFINE FIELD category ON skill TYPE string DEFAULT 'general';
            DEFINE FIELD active ON skill TYPE bool DEFAULT true;
        """)

        yield SurrealSkillRepository(surreal_client)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_get_skill(self, repo, surreal_client, unique_id):
        """Test creating and retrieving a skill."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"test_skill_{unique_id}",
            description="Test skill for integration testing",
            path="/test/skill",
            keywords=["test", "integration"],
            metadata={"category": "testing"},
        )

        skill_id = await repo.create(skill)
        assert skill_id != ""

        retrieved = await repo.get(skill_id)
        assert retrieved is not None
        assert retrieved.name == skill.name
        assert "test" in retrieved.keywords

        await surreal_client.query(f"DELETE skill WHERE id = skill:{skill_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_by_name(self, repo, surreal_client, unique_id):
        """Test retrieving a skill by name."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"named_skill_{unique_id}",
            description="Skill with unique name",
            path="/named/skill",
            keywords=["named"],
            metadata={},
        )

        await repo.create(skill)

        retrieved = await repo.get_by_name(f"named_skill_{unique_id}")
        assert retrieved is not None
        assert retrieved.name == f"named_skill_{unique_id}"

        await surreal_client.query(f"DELETE skill WHERE name = 'named_skill_{unique_id}'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_skill(self, repo, surreal_client, unique_id):
        """Test updating a skill."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"skill_to_update_{unique_id}",
            description="Original description",
            path="/update/skill",
            keywords=["update"],
            metadata={},
        )

        skill_id = await repo.create(skill)

        updated = await repo.update(skill_id, {"description": "Updated description"})
        assert updated is True

        retrieved = await repo.get(skill_id)
        assert retrieved is not None
        assert retrieved.description == "Updated description"

        await surreal_client.query(f"DELETE skill WHERE id = skill:{skill_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_skill(self, repo, surreal_client, unique_id):
        """Test deleting a skill."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"skill_to_delete_{unique_id}",
            description="Skill to be deleted",
            path="/delete/skill",
            keywords=["delete"],
            metadata={},
        )

        skill_id = await repo.create(skill)

        deleted = await repo.delete(skill_id)
        assert deleted is True

        retrieved = await repo.get(skill_id)
        assert retrieved is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_by_keywords(self, repo, surreal_client, unique_id):
        """Test keyword search."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill1 = Skill(
            name=f"keyword_skill_1_{unique_id}",
            description="First keyword skill",
            path="/kw/1",
            keywords=["python", "testing", "pytest"],
            metadata={},
        )
        skill2 = Skill(
            name=f"keyword_skill_2_{unique_id}",
            description="Second keyword skill",
            path="/kw/2",
            keywords=["javascript", "testing", "jest"],
            metadata={},
        )

        await repo.create(skill1)
        await repo.create(skill2)

        results = await repo.search_by_keywords(["testing"], limit=10)

        assert len(results) >= 2

        await surreal_client.query("DELETE skill WHERE path LIKE '/kw/%'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_by_category(self, repo, surreal_client, unique_id):
        """Test category search."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"category_skill_{unique_id}",
            description="Categorized skill",
            path="/cat/skill",
            keywords=["category"],
            metadata={"category": "integration_test_category"},
        )

        await repo.create(skill)

        results = await repo.search_by_category("integration_test_category", limit=10)

        assert len(results) >= 1
        assert results[0].metadata.get("category") == "integration_test_category"

        await surreal_client.query("DELETE skill WHERE category = 'integration_test_category'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_record_invocation(self, repo, surreal_client, unique_id):
        """Test invocation tracking."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill = Skill(
            name=f"invocation_skill_{unique_id}",
            description="Skill for invocation tracking",
            path="/invoke/skill",
            keywords=["invoke"],
            metadata={},
        )

        skill_id = await repo.create(skill)

        success = await repo.record_invocation(skill_id, success=True)
        assert success is True

        success = await repo.record_invocation(skill_id, success=False)
        assert success is True

        retrieved = await repo.get(skill_id)
        assert retrieved is not None
        assert retrieved.metadata.get("invocation_count", 0) >= 2

        await surreal_client.query(f"DELETE skill WHERE id = skill:{skill_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_active_skills(self, repo, surreal_client, unique_id):
        """Test retrieving active skills."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        skill_active = Skill(
            name=f"active_skill_{unique_id}",
            description="Active skill",
            path="/active/skill",
            keywords=["active"],
            metadata={"active": True},
        )
        skill_inactive = Skill(
            name=f"inactive_skill_{unique_id}",
            description="Inactive skill",
            path="/inactive/skill",
            keywords=["inactive"],
            metadata={"active": False},
        )

        await repo.create(skill_active)
        await repo.create(skill_inactive)

        active_skills = await repo.get_active_skills(limit=100)

        active_names = [s.name for s in active_skills]
        assert f"active_skill_{unique_id}" in active_names

        await surreal_client.query("DELETE skill WHERE path LIKE '/active/%'")
        await surreal_client.query("DELETE skill WHERE path LIKE '/inactive/%'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_top_skills(self, repo, surreal_client, unique_id):
        """Test retrieving top skills by metric."""
        from cohezion.core.persistence.repositories.skill_repository import Skill

        for i in range(3):
            skill = Skill(
                name=f"top_skill_{unique_id}_{i}",
                description=f"Top skill {i}",
                path=f"/top/skill/{i}",
                keywords=["top"],
                metadata={},
            )
            await repo.create(skill)

        top_by_invocation = await repo.get_top_skills(by="invocation_count", limit=5)
        assert len(top_by_invocation) >= 1

        top_by_success = await repo.get_top_skills(by="success_rate", limit=5)
        assert len(top_by_success) >= 1

        await surreal_client.query("DELETE skill WHERE path LIKE '/top/skill/%'")


class TestJourneyKnowledgeRepositoryIntegration:
    """Integration tests for JourneyKnowledgeRepository."""

    @pytest.fixture
    async def repo(self, surreal_client):
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            SurrealJourneyKnowledgeRepository,
        )

        await surreal_client.query("""
            DEFINE TABLE journey_knowledge SCHEMALESS;
            DEFINE FIELD knowledge_type ON journey_knowledge TYPE string;
            DEFINE FIELD content ON journey_knowledge TYPE string;
            DEFINE FIELD confidence ON journey_knowledge TYPE float DEFAULT 0.0;
            DEFINE FIELD validated ON journey_knowledge TYPE bool DEFAULT false;
        """)

        yield SurrealJourneyKnowledgeRepository(surreal_client)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_get_knowledge(self, repo, surreal_client, unique_id):
        """Test creating and retrieving knowledge."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge = JourneyKnowledge(
            id=f"know_{unique_id}",
            source_journey_id=f"journey_{unique_id}",
            knowledge_type="pattern",
            content="Test pattern extracted from journey",
            confidence=0.85,
            metadata={"test": True},
        )

        knowledge_id = await repo.create(knowledge)
        assert knowledge_id != ""

        retrieved = await repo.get(knowledge_id)
        assert retrieved is not None
        assert retrieved.knowledge_type == "pattern"
        assert retrieved.content == knowledge.content
        assert abs(retrieved.confidence - 0.85) < 0.01

        await surreal_client.query(f"DELETE journey_knowledge WHERE id = journey_knowledge:{knowledge_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_by_type(self, repo, surreal_client, unique_id):
        """Test retrieving knowledge by type."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        for kt in ["pattern", "anti_pattern", "insight"]:
            knowledge = JourneyKnowledge(
                id=f"know_{kt}_{unique_id}",
                knowledge_type=kt,
                content=f"Test {kt} content",
                confidence=0.75,
            )
            await repo.create(knowledge)

        patterns = await repo.get_by_type("pattern", limit=10)
        assert len(patterns) >= 1
        assert all(k.knowledge_type == "pattern" for k in patterns)

        insights = await repo.get_by_type("insight", limit=10)
        assert len(insights) >= 1

        await surreal_client.query(f"DELETE journey_knowledge WHERE id LIKE 'journey_knowledge:know_%{unique_id}%'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_knowledge(self, repo, surreal_client, unique_id):
        """Test validating knowledge."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge = JourneyKnowledge(
            id=f"know_validate_{unique_id}",
            knowledge_type="pattern",
            content="Pattern to validate",
            confidence=0.80,
            validated=False,
        )

        knowledge_id = await repo.create(knowledge)

        validated = await repo.validate(knowledge_id, validated=True)
        assert validated is True

        retrieved = await repo.get(knowledge_id)
        assert retrieved is not None
        assert retrieved.validated is True

        await surreal_client.query(f"DELETE journey_knowledge WHERE id = journey_knowledge:{knowledge_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_by_confidence(self, repo, surreal_client, unique_id):
        """Test retrieving knowledge by confidence threshold."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge_high = JourneyKnowledge(
            id=f"know_high_{unique_id}",
            knowledge_type="pattern",
            content="High confidence pattern",
            confidence=0.95,
        )
        knowledge_low = JourneyKnowledge(
            id=f"know_low_{unique_id}",
            knowledge_type="pattern",
            content="Low confidence pattern",
            confidence=0.45,
        )

        await repo.create(knowledge_high)
        await repo.create(knowledge_low)

        high_conf = await repo.get_by_confidence(min_confidence=0.9, limit=10)

        assert len(high_conf) >= 1
        assert all(k.confidence >= 0.9 for k in high_conf)

        await surreal_client.query(f"DELETE journey_knowledge WHERE id LIKE 'journey_knowledge:know_%{unique_id}%'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_confidence(self, repo, surreal_client, unique_id):
        """Test updating confidence score."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge = JourneyKnowledge(
            id=f"know_conf_update_{unique_id}",
            knowledge_type="insight",
            content="Insight for confidence update",
            confidence=0.50,
        )

        knowledge_id = await repo.create(knowledge)

        updated = await repo.update_confidence(knowledge_id, 0.95)
        assert updated is True

        retrieved = await repo.get(knowledge_id)
        assert retrieved is not None
        assert abs(retrieved.confidence - 0.95) < 0.01

        await surreal_client.query(f"DELETE journey_knowledge WHERE id = journey_knowledge:{knowledge_id}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_knowledge(self, repo, surreal_client, unique_id):
        """Test deleting knowledge."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge = JourneyKnowledge(
            id=f"know_delete_{unique_id}",
            knowledge_type="pattern",
            content="Pattern to delete",
            confidence=0.70,
        )

        knowledge_id = await repo.create(knowledge)

        deleted = await repo.delete(knowledge_id)
        assert deleted is True

        retrieved = await repo.get(knowledge_id)
        assert retrieved is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_similar_knowledge(self, repo, surreal_client, unique_id):
        """Test vector similarity search on knowledge."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge1 = JourneyKnowledge(
            id=f"know_sim_1_{unique_id}",
            knowledge_type="pattern",
            content="This is about machine learning patterns",
            confidence=0.85,
            embedding=[0.1] * 100 + [0.9] * 100 + [0.1] * 568,
        )
        knowledge2 = JourneyKnowledge(
            id=f"know_sim_2_{unique_id}",
            knowledge_type="insight",
            content="This is about cooking techniques",
            confidence=0.75,
            embedding=[0.9] * 100 + [0.1] * 100 + [0.5] * 568,
        )

        await repo.create(knowledge1)
        await repo.create(knowledge2)

        query_embedding = [0.1] * 100 + [0.9] * 100 + [0.1] * 568
        results = await repo.search_similar(query_embedding, limit=5)

        assert len(results) >= 1

        await surreal_client.query(f"DELETE journey_knowledge WHERE id LIKE 'journey_knowledge:know_sim_%{unique_id}%'")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_validated_knowledge(self, repo, surreal_client, unique_id):
        """Test retrieving validated knowledge."""
        from cohezion.core.persistence.repositories.journey_knowledge_repository import (
            JourneyKnowledge,
        )

        knowledge_v = JourneyKnowledge(
            id=f"know_validated_{unique_id}",
            knowledge_type="pattern",
            content="Validated pattern",
            confidence=0.90,
            validated=True,
        )
        knowledge_u = JourneyKnowledge(
            id=f"know_unvalidated_{unique_id}",
            knowledge_type="pattern",
            content="Unvalidated pattern",
            confidence=0.80,
            validated=False,
        )

        await repo.create(knowledge_v)
        await repo.create(knowledge_u)

        validated = await repo.get_validated(limit=10)

        assert all(k.validated for k in validated)

        await surreal_client.query(f"DELETE journey_knowledge WHERE id LIKE 'journey_knowledge:know_%{unique_id}%'")


class TestTransactions:
    """Test SurrealDB transaction support."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_begin_commit_transaction(self, surreal_client):
        """Test transaction commit."""
        txn_id = await surreal_client.begin_transaction()
        assert txn_id is not None
        assert txn_id in surreal_client._active_transactions

        try:
            await surreal_client.query("CREATE test_txn_commit SET value = 'committed'")

            committed = await surreal_client.commit_transaction(txn_id)
            assert committed is True
            assert txn_id not in surreal_client._active_transactions
        except Exception:
            with contextlib.suppress(Exception):
                await surreal_client.cancel_transaction(txn_id)
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, surreal_client):
        """Test transaction cancellation."""
        txn_id = await surreal_client.begin_transaction()
        assert txn_id is not None

        try:
            await surreal_client.query("CREATE test_txn_rollback SET value = 'will_rollback'")

            cancelled = await surreal_client.cancel_transaction(txn_id)
            assert cancelled is True
            assert txn_id not in surreal_client._active_transactions
        except Exception:
            if txn_id in surreal_client._active_transactions:
                with contextlib.suppress(Exception):
                    await surreal_client.cancel_transaction(txn_id)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_transactions_prevented(self, surreal_client):
        """Test that concurrent transactions raise appropriate errors."""
        txn_id1 = await surreal_client.begin_transaction()

        try:
            txn_id2 = await surreal_client.begin_transaction()

            with contextlib.suppress(Exception):
                await surreal_client.commit_transaction(txn_id1)

            with contextlib.suppress(Exception):
                await surreal_client.commit_transaction(txn_id2)
        except Exception:
            if txn_id1 in surreal_client._active_transactions:
                with contextlib.suppress(Exception):
                    await surreal_client.cancel_transaction(txn_id1)


class TestSchemaOperations:
    """Test schema operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_define_table_and_fields(self, surreal_client, unique_id):
        """Test defining tables and fields."""
        table_name = f"test_schema_{unique_id}"

        await surreal_client.query(f"""
            DEFINE TABLE {table_name} SCHEMAFULL;
            DEFINE FIELD name ON TABLE {table_name} TYPE string;
            DEFINE FIELD value ON TABLE {table_name} TYPE number DEFAULT 0;
        """)

        await surreal_client.query(f"""
            CREATE {table_name} SET name = 'test', value = 42;
        """)

        result = await surreal_client.query(f"SELECT * FROM {table_name}")
        assert result is not None
        assert len(result[0].get("result", [])) >= 1

        await surreal_client.query(f"REMOVE TABLE {table_name}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_index_creation(self, surreal_client, unique_id):
        """Test index creation for performance."""
        table_name = f"test_index_{unique_id}"

        await surreal_client.query(f"""
            DEFINE TABLE {table_name} SCHEMALESS;
            DEFINE INDEX idx_name ON TABLE {table_name} FIELDS name;
        """)

        for i in range(5):
            await surreal_client.query(f"CREATE {table_name} SET name = 'item_{i}'")

        result = await surreal_client.query(f"SELECT * FROM {table_name} WHERE name = 'item_3'")
        assert result is not None

        await surreal_client.query(f"REMOVE TABLE {table_name}")
