"""Integration tests verifying Cohezion Roadmap Components.
=========================================================
1. Priority 1: Semantic Cache integration in PreflightValidator.
2. Priority 2: Two-Party IV&V Gatekeeper enforcement.
3. Priority 3: Retrospective Skill Extractor automation.
4. Priority 4: Zero-Copy Shared Memory Mesh NumPy buffer exchange.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np

from cohezion.cache.semantic_cache_system import SemanticCacheSystem
from cohezion.compound.ivv_engine import (
    IndependentVerifier,
    IVVGatekeeper,
    IVVSeverity,
)
from cohezion.compound.retrospective_skill_extractor import RetrospectiveSkillExtractor
from cohezion.data_mesh.shm_mesh import SharedMemoryDataProductBuffer
from cohezion.kaggle.preflight_validator import PreflightValidator


def test_priority_1_semantic_cache_in_preflight_validator() -> None:
    cache = SemanticCacheSystem(l1_capacity=100)
    validator = PreflightValidator(cache=cache)

    cfg = {
        "slots": {
            1: {
                "name": "cache_roadmap_slot",
                "patch_script": None,
            }
        }
    }

    # First call: computes and stores in L1 cache
    res1 = validator.validate_slot("rsna-knee-abnormality-detection", 1, cfg)
    assert res1.passed is True

    # Second call: instantaneous L1 cache hit
    res2 = validator.validate_slot("rsna-knee-abnormality-detection", 1, cfg)
    assert res2.passed is True
    assert res1 == res2
    assert len(cache.l1_cache) >= 1


def test_priority_2_two_party_ivv_gatekeeper() -> None:
    verifier = IndependentVerifier(verifier_id="AdversarialVerifier")
    gatekeeper = IVVGatekeeper()

    # Case A: Self-certification must fail (Party A == Party B)
    self_cert = verifier.audit_code_artifact(
        artifact_id="test_comp:slot_1",
        creator_id="AdversarialVerifier",  # Same as verifier!
        code_str="x = 1",
        requirements_spec={},
    )
    assert self_cert.passed is False
    assert any(f.gate == "IdentityGate" for f in self_cert.findings)

    # Case B: Valid Independent Verification
    valid_code = "import numpy as np\ndf['Abnormal'] = np.maximum(df['Abnormal'], df[['ACL']].max(axis=1))"
    valid_cert = verifier.audit_code_artifact(
        artifact_id="test_comp:slot_2",
        creator_id="AllotmentEngineCreator",
        code_str=valid_code,
        requirements_spec={"competition_type": "rsna-knee-abnormality-detection"},
    )
    assert valid_cert.passed is True
    assert valid_cert.is_valid is True

    gatekeeper.register_certificate(valid_cert)
    ready, reason = gatekeeper.verify_deployment_readiness("test_comp:slot_2", "AllotmentEngineCreator")
    assert ready is True
    assert "DEPLOYMENT BLOCKED" not in reason


def test_priority_3_retrospective_skill_extractor() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        extractor = RetrospectiveSkillExtractor(workspace_root=tmp_root)

        code_sample = '''
def ledoit_wolf_shrinkage(cov: np.ndarray, prior: np.ndarray, alpha: float = 0.2) -> np.ndarray:
    """Computes convex linear shrinkage towards the prior."""
    return (1.0 - alpha) * cov + alpha * prior
'''
        spec = extractor.extract_from_python_code(
            code_content=code_sample,
            name="TEST_LEDOIT_WOLF_SHRINKAGE",
            domain_expertise="Ledoit-Wolf shrinkage covariance projection for anatomical feature coupling.",
            source_artifact="test_cov.py",
            tags=["medical", "rsna", "covariance"],
        )
        assert spec.name == "TEST_LEDOIT_WOLF_SHRINKAGE"
        assert len(spec.key_concepts) >= 1

        skill_path = extractor.save_skill(spec)
        assert skill_path.exists()
        assert "TEST_LEDOIT_WOLF_SHRINKAGE_PRIME.md" in skill_path.name
        content = skill_path.read_text(encoding="utf-8")
        assert "SKILL: TEST_LEDOIT_WOLF_SHRINKAGE_PRIME" in content
        assert "DOMAIN EXPERTISE" in content


def test_priority_4_zero_copy_shm_mesh_numpy() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        shm_buffer = SharedMemoryDataProductBuffer(base_dir=tmpdir)

        # Generate sample validation matrices (e.g. predictions, ground truth, fold splits)
        rng = np.random.default_rng(1337)
        original_arr = rng.normal(loc=0.5, scale=0.2, size=(100, 12)).astype(np.float32)

        # Publish NumPy array zero-copy
        desc = shm_buffer.publish_numpy(
            product_id="rsna_validation_predictions_v1",
            arr=original_arr,
            metadata={"competition": "rsna-knee", "fold": 0},
        )
        assert desc.payload_size == original_arr.nbytes
        assert Path(desc.shm_path).exists()

        # Read back array directly
        meta, recovered_arr = shm_buffer.read_numpy("rsna_validation_predictions_v1")
        assert meta["competition"] == "rsna-knee"
        assert meta["dtype"] == "float32"
        assert meta["shape"] == [100, 12]
        np.testing.assert_array_equal(original_arr, recovered_arr)

        # Cleanup
        assert shm_buffer.delete("rsna_validation_predictions_v1") is True
        assert not Path(desc.shm_path).exists()
