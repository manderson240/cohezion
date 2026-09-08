"""Vector 2: Coverage-Guided Generative Fuzzing.
================================================
Fuzzes critical security boundaries, command safety verifiers, and AST policy parsers
with randomized adversarial bitstreams, pathological token trees, and malformed inputs.
"""

import string
import time
import pytest
from hypothesis import given, settings, strategies as st

from cohezion.security.secret_scrubber import (
    scrub_text,
    contains_unredacted_credentials,
    verify_command_safety,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


@pytest.mark.fuzz
class TestGenerativeFuzzing:

    @settings(max_examples=200, deadline=None)
    @given(
        st.binary(min_size=0, max_size=5000),
    )
    def test_fuzz_secret_scrubber_binary_resilience(self, raw_bytes):
        """Fuzz: Ensure secret scrubber gracefully handles raw binary, null bytes, and non-UTF8 strings."""
        decoded = raw_bytes.decode("utf-8", errors="replace")
        t0 = time.perf_counter()
        scrubbed = scrub_text(decoded)
        dt = time.perf_counter() - t0

        # No ReDoS (catastrophic backtracking): must process 5KB in < 50 ms
        assert dt < 0.05
        assert isinstance(scrubbed, str)

    @settings(max_examples=150, deadline=None)
    @given(
        st.text(alphabet=string.printable, min_size=1, max_size=200),
        st.sampled_from(["cat", "head", "tail", "grep", "less", "more", "awk", "sed"]),
        st.sampled_from([
            "rclone.conf",
            ".env",
            ".env.prod",
            "id_rsa",
            "id_ed25519",
            "credentials.json",
            ".aws/credentials",
        ]),
    )
    def test_fuzz_command_safety_adversarial_framing(self, filler, tool, secret_target):
        """Fuzz: Ensure command safety guard cannot be bypassed by path prefixes or shell chaining."""
        adversarial_cmd = f"{filler}; {tool} /path/to/{secret_target} && echo done"
        res = verify_command_safety(adversarial_cmd)
        assert res.allowed is False, f"Command safety guard failed to block: {adversarial_cmd}"
        assert len(res.violation_reason) > 0

    @settings(max_examples=100, deadline=None)
    @given(
        st.text(min_size=1, max_size=300),
    )
    def test_fuzz_autoharness_policy_resilience(self, arbitrary_code):
        """Fuzz: AutoHarness evaluate_policy must never raise unhandled exceptions on arbitrary text."""
        policy = AutoHarnessPolicy()
        res = policy.evaluate_policy("bounded_grid", {"grid": arbitrary_code})
        assert isinstance(res.allowed, bool)
        assert res.bypassed_llm is True
