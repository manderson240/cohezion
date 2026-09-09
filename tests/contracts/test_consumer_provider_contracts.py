"""Vector 5: Contract Testing with Mutation Verification.
=========================================================
Validates request/response compatibility across service boundaries (SurrealDB, Vault, Storage, AutoHarness).
Synthetically mutates contracts (fields, status codes, payload schemas) and verifies that consumer
verification tests strictly detect and reject contract drift.
"""

import copy
import pytest
from pydantic import ValidationError

from cohezion.data_mesh.durable_precipitation_bridge import DurableWitnessMark
from cohezion.storage.gdrive_offloader import StorageHealth, OffloadJob
from cohezion.agi.autoharness_policy import ActionPolicyResult


class TestConsumerProviderContracts:

    def test_durable_witness_mark_contract_baseline(self):
        """Baseline valid contract for DurableWitnessMark."""
        mark = DurableWitnessMark(
            mark_id="mark_contract_001",
            title="Contract Test Title",
            category="architecture",
            content="# Content",
            hiho_coherence=0.500,
        )
        assert mark.mark_id == "mark_contract_001"
        assert mark.hiho_coherence == 0.500

    @pytest.mark.parametrize("mutated_payload,expected_error", [
        # Mutant 1: Missing required primary key mark_id
        ({"title": "T", "category": "c", "content": "c", "hiho_coherence": 0.5}, "mark_id"),
        # Mutant 2: Missing required content
        ({"mark_id": "m1", "title": "T", "category": "c", "hiho_coherence": 0.5}, "content"),
        # Mutant 3: Incompatible type for hiho_coherence (string instead of float)
        ({"mark_id": "m1", "title": "T", "category": "c", "content": "c", "hiho_coherence": "invalid_coherence"}, "hiho_coherence"),
        # Mutant 4: Out-of-bounds hiho_coherence (> 1.0)
        ({"mark_id": "m1", "title": "T", "category": "c", "content": "c", "hiho_coherence": 1.5}, "hiho_coherence"),
    ])
    def test_durable_witness_mark_contract_mutation_resilience(self, mutated_payload, expected_error):
        """Mutation Verification: Proves consumer contract breaks when provider payload is mutated."""
        with pytest.raises(ValidationError) as exc_info:
            DurableWitnessMark(**mutated_payload)
        assert expected_error in str(exc_info.value)

    def test_storage_health_contract_baseline(self):
        """Baseline valid contract for StorageHealth."""
        health = StorageHealth(
            path="/home",
            total_gb=1000.0,
            used_gb=600.0,
            available_gb=400.0,
            use_percent=60.0,
            status="healthy",
        )
        assert health.status == "healthy"
        assert health.available_gb == 400.0

    @pytest.mark.parametrize("mutated_health,expected_error", [
        # Mutant 1: Invalid status code enum value
        ({
            "path": "/home", "total_gb": 1000.0, "used_gb": 600.0, "available_gb": 400.0,
            "use_percent": 60.0, "status": "UNKNOWN_CORRUPTED_STATUS"
        }, "status"),
        # Mutant 2: Missing path
        ({
            "total_gb": 1000.0, "used_gb": 600.0, "available_gb": 400.0,
            "use_percent": 60.0, "status": "healthy"
        }, "path"),
        # Mutant 3: Float expected, string provided for available_gb
        ({
            "path": "/home", "total_gb": 1000.0, "used_gb": 600.0, "available_gb": "not_a_number",
            "use_percent": 60.0, "status": "healthy"
        }, "available_gb"),
    ])
    def test_storage_health_contract_mutation_resilience(self, mutated_health, expected_error):
        """Mutation Verification: Proves StorageHealth rejects corrupted contract fields."""
        with pytest.raises(ValidationError) as exc_info:
            StorageHealth(**mutated_health)
        assert expected_error in str(exc_info.value)

    def test_action_policy_result_contract_immutability(self):
        """Proves ActionPolicyResult contract cannot be mutated post-creation."""
        res = ActionPolicyResult(
            allowed=True,
            bypassed_llm=True,
            action_type="credential_safe",
            verification_score=1.0,
            execution_time_ms=0.05,
        )
        with pytest.raises(Exception):
            # Attempting to mutate frozen slots dataclass must fail
            res.allowed = False  # type: ignore
