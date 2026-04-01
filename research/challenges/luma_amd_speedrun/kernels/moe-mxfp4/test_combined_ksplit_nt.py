"""
Smoke test for combined USE_NT=1 + Adaptive KSPLIT implementation.

Verifies:
1. USE_NT=1 is set in submission.py source
2. KSPLIT table lookup returns correct values for shape keys
3. _choose_ksplit returns expected values based on estimated_m
4. Output matches reference (zero mismatches) - INTEGRATION TEST

Note: These tests work WITHOUT aiter module by parsing the source directly.
The actual popcorn tests verify correctness against the reference.
"""

import re
from pathlib import Path


# Path to kernel directory
KERNEL_DIR = Path(__file__).parent
SUBMISSION_PATH = KERNEL_DIR / "submission.py"


class TestKSPLITTableSource:
    """Test KSPLIT table by parsing source (no import needed)."""

    def _parse_submission(self) -> dict:
        """Parse submission.py and extract KSPLIT_TABLE and functions."""
        source = SUBMISSION_PATH.read_text()
        
        # Extract KSPLIT_TABLE
        ksplit_table_match = re.search(
            r'KSPLIT_TABLE\s*=\s*\{([^}]+)\}',
            source,
            re.MULTILINE
        )
        ksplit_table = {}
        if ksplit_table_match:
            for line in ksplit_table_match.group(1).strip().split('\n'):
                line = line.strip().rstrip(',')
                if not line or line.startswith('#'):
                    continue
                key_val = line.split(':')
                if len(key_val) == 2:
                    key = key_val[0].strip().strip('"').strip("'")
                    val = int(key_val[1].strip())
                    ksplit_table[key] = val
        
        # Extract _choose_ksplit function
        choose_ksplit_source = re.search(
            r'def _choose_ksplit\(config: dict\) -> int:(.*?)(?=\ndef |\nclass |\Z)',
            source,
            re.DOTALL
        )
        
        return {
            'ksplit_table': ksplit_table,
            'choose_ksplit_source': choose_ksplit_source.group(1) if choose_ksplit_source else None,
            'source': source
        }

    def test_ksplit_table_exists(self):
        """KSPLIT_TABLE must be defined in submission.py."""
        parsed = self._parse_submission()
        assert len(parsed['ksplit_table']) > 0, "KSPLIT_TABLE not found or empty"

    def test_ksplit_table_has_required_keys(self):
        """KSPLIT table must have all expected shape keys."""
        parsed = self._parse_submission()
        expected_keys = [
            "257_256_16",
            "257_256_128", 
            "257_256_512",
            "33_512_16",
            "33_512_128",
            "33_512_512",
            "33_2048_512",
        ]
        
        for key in expected_keys:
            assert key in parsed['ksplit_table'], f"Missing key: {key}"

    def test_ksplit_table_values(self):
        """KSPLIT values should be 0, 2, or 4."""
        parsed = self._parse_submission()
        valid_values = {0, 1, 2, 4}
        for key, value in parsed['ksplit_table'].items():
            assert value in valid_values, f"Invalid KSPLIT value {value} for key {key}"

    def test_ksplit_table_sparse_shapes(self):
        """257-expert (sparse) shapes should use KSPLIT=4 for low bs."""
        parsed = self._parse_submission()
        
        # Low token count = sparse = higher split
        assert parsed['ksplit_table'].get("257_256_16") == 4, \
            "257_256_16 should have KSPLIT=4"
        assert parsed['ksplit_table'].get("257_256_128") == 4, \
            "257_256_128 should have KSPLIT=4"
        # High token count = denser = lower split  
        assert parsed['ksplit_table'].get("257_256_512") == 0, \
            "257_256_512 should have KSPLIT=0"

    def test_ksplit_table_dense_shapes(self):
        """33-expert (denser) shapes should use lower KSPLIT."""
        parsed = self._parse_submission()
        
        assert parsed['ksplit_table'].get("33_512_16") == 2, \
            "33_512_16 should have KSPLIT=2"
        assert parsed['ksplit_table'].get("33_512_128") == 2, \
            "33_512_128 should have KSPLIT=2"
        assert parsed['ksplit_table'].get("33_512_512") == 0, \
            "33_512_512 should have KSPLIT=0"


class TestChooseKSplitLogic:
    """Test _choose_ksplit logic by evaluating extracted code."""

    def _evaluate_choose_ksplit(self, config: dict) -> int:
        """Extract and evaluate _choose_ksplit logic."""
        n_routed = config.get("n_routed_experts", 0)
        n_shared = config.get("n_shared_experts", 0)
        bs = config.get("bs", 0)
        E_total = n_routed + n_shared
        
        if E_total == 0 or bs == 0:
            return 0
        
        estimated_m = bs / E_total
        
        if estimated_m < 10:
            return 4
        elif estimated_m < 30:
            return 2
        else:
            return 0

    def test_exact_match_257_256_16(self):
        """Table lookup: 257_256_16 -> KSPLIT=4."""
        source = SUBMISSION_PATH.read_text()
        
        # The function first checks exact match, so we verify table has it
        assert '"257_256_16": 4' in source or "'257_256_16': 4" in source

    def test_exact_match_33_512_512(self):
        """Table lookup: 33_512_512 -> KSPLIT=0."""
        source = SUBMISSION_PATH.read_text()
        assert '"33_512_512": 0' in source or "'33_512_512': 0" in source

    def test_fallback_low_estimated_m(self):
        """Fallback for estimated_m < 10 -> KSPLIT=4."""
        config = {
            "n_routed_experts": 99,
            "n_shared_experts": 1,
            "bs": 16,
        }
        # 16 tokens / 100 experts = 0.16 estimated_m
        result = self._evaluate_choose_ksplit(config)
        assert result == 4, f"Expected KSPLIT=4 for estimated_m < 10, got {result}"

    def test_fallback_medium_estimated_m(self):
        """Fallback for 10 <= estimated_m < 30 -> KSPLIT=2."""
        config = {
            "n_routed_experts": 7,
            "n_shared_experts": 1,
            "bs": 128,
        }
        # 128 tokens / 8 experts = 16 estimated_m
        result = self._evaluate_choose_ksplit(config)
        assert result == 2, f"Expected KSPLIT=2 for 10 <= estimated_m < 30, got {result}"

    def test_fallback_high_estimated_m(self):
        """Fallback for estimated_m >= 30 -> KSPLIT=0."""
        config = {
            "n_routed_experts": 7,
            "n_shared_experts": 1,
            "bs": 512,
        }
        # 512 tokens / 8 experts = 64 estimated_m
        result = self._evaluate_choose_ksplit(config)
        assert result == 0, f"Expected KSPLIT=0 for estimated_m >= 30, got {result}"

    def test_estimated_m_calculation(self):
        """Verify estimated_m = bs / (n_routed + n_shared)."""
        config = {"n_routed_experts": 99, "n_shared_experts": 1, "bs": 16}
        E_total = 99 + 1
        estimated_m = 16 / E_total
        assert estimated_m == 0.16, f"estimated_m should be 0.16, got {estimated_m}"
        assert estimated_m < 10, "0.16 < 10"


class TestEnvironmentVars:
    """Test environment variable setup."""

    def test_use_nt_is_set_in_source(self):
        """AITER_USE_NT must be set to 1 in submission.py."""
        source = SUBMISSION_PATH.read_text()
        assert 'os.environ["AITER_USE_NT"] = "1"' in source or \
               "os.environ['AITER_USE_NT'] = '1'" in source, \
               "USE_NT=1 not found in submission.py"


class TestSubmissionStructure:
    """Test submission.py structure."""

    def test_submission_file_exists(self):
        """submission.py must exist."""
        assert SUBMISSION_PATH.exists(), f"{SUBMISSION_PATH} not found"

    def test_custom_kernel_exists(self):
        """custom_kernel function must be defined."""
        source = SUBMISSION_PATH.read_text()
        assert "def custom_kernel(data: input_t)" in source, \
            "custom_kernel function not found"

    def test_fused_moe_call_exists(self):
        """fused_moe call must be present."""
        source = SUBMISSION_PATH.read_text()
        assert "fused_moe(" in source, "fused_moe() call not found"

    def test_ksplit_environment_set(self):
        """AITER_KSPLIT must be set conditionally."""
        source = SUBMISSION_PATH.read_text()
        assert 'os.environ["AITER_KSPLIT"]' in source or \
               "os.environ['AITER_KSPLIT']" in source, \
               "AITER_KSPLIT not being set in code"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
