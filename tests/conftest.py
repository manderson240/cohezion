"""Shared pytest fixtures and configuration for Phase 4A test framework."""

import pytest
import httpx
from typing import Generator, Any


class MockSurrealDBConnection:
    """Mock SurrealDB connection for testing without live database."""

    def __init__(self):
        self.data = {}
        self.connection_count = 0

    def connect(self) -> bool:
        """Simulate connection to SurrealDB."""
        self.connection_count += 1
        return True

    def query(self, sql: str, params: dict = None) -> list[dict]:
        """Simulate query execution."""
        return []

    def insert(self, table: str, data: dict) -> dict:
        """Simulate insert operation."""
        self.data.setdefault(table, [])
        self.data[table].append(data)
        return data


@pytest.fixture
def surrealdb_mock() -> Generator[MockSurrealDBConnection, None, None]:
    """Provide mock SurrealDB connection for all tests."""
    db = MockSurrealDBConnection()
    db.connect()
    yield db


@pytest.fixture
def http_client() -> Generator[httpx.Client, None, None]:
    """Provide HTTP client configured for testing."""
    client = httpx.Client(
        base_url="http://localhost:8000",
        auth=("root", "root"),
        timeout=10.0,
    )
    yield client
    client.close()


# Test data factories

@pytest.fixture
def sample_paper_data() -> dict[str, Any]:
    """Sample paper data for testing confidence scoring."""
    return {
        "id": "paper_001",
        "title": "Test Paper on Decision Making",
        "authors": ["Author A", "Author B"],
        "year": 2024,
        "abstract": "A comprehensive study on decision making",
        "citations": 15,
    }


@pytest.fixture
def sample_decision_data() -> dict[str, Any]:
    """Sample decision data for testing impact analysis."""
    return {
        "id": "decision_001",
        "title": "Choose database technology",
        "status": "proposed",
        "confidence": 0.75,
        "created_at": "2026-02-14",
        "affected_areas": ["infrastructure", "backend", "ops"],
    }


@pytest.fixture
def sample_reasoning_chain() -> dict[str, Any]:
    """Sample reasoning chain for testing GraphRAG."""
    return {
        "id": "reasoning_001",
        "decision_id": "decision_001",
        "reasoning_steps": [
            {"step": 1, "description": "Identify criteria", "evidence": []},
            {"step": 2, "description": "Evaluate options", "evidence": []},
            {"step": 3, "description": "Select best option", "evidence": []},
        ],
        "confidence_score": 0.82,
    }


@pytest.fixture
def sample_dependency_graph() -> dict[str, list[tuple]]:
    """Sample dependency graph for testing impact analysis."""
    return {
        "nodes": [
            ("decision_001", {"title": "Choose DB"}),
            ("decision_002", {"title": "Setup infrastructure"}),
            ("decision_003", {"title": "Deploy to production"}),
        ],
        "edges": [
            ("decision_001", "decision_002"),
            ("decision_002", "decision_003"),
        ],
    }


# Pytest configuration

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "graphrag: mark test as related to GraphRAG (Track A)"
    )
    config.addinivalue_line(
        "markers", "scoring: mark test as related to Confidence Scoring (Track B)"
    )
    config.addinivalue_line(
        "markers", "impact: mark test as related to Impact Analysis (Track C)"
    )
