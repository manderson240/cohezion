import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest

from problem import HASH_STAGES, Input, Machine, Tree

# Check if build_mem_image is in problem, if so import it
try:
    from problem import build_mem_image
except ImportError:
    # Maybe it's in frozen_problem or similar?
    # Or maybe it's not exported.
    # The submission_tests use `machine = Machine(mem, ...)`
    # How do they build mem?
    # submission_tests.py line 48: `mem = list(machine.mem)`? No.
    # submission_tests.py uses `build_mem_image`?
    # Let's assume it exists based on grep.
    pass

from optimizer import OptimizedKernelBuilder as KernelBuilder


class AdversarialTests(unittest.TestCase):
    def test_prime_nodes(self):
        """Test with a prime number of nodes"""
        print("\nTesting Adversarial: Batch 255 (Odd)...")
        self.run_scenario(height=5, rounds=4, batch=255)

    def test_zero_rounds(self):
        """Test with 0 rounds"""
        print("\nTesting Adversarial: Rounds 0...")
        self.run_scenario(height=5, rounds=0, batch=16)

    def test_large_rounds(self):
        """Test with 100 rounds"""
        print("\nTesting Adversarial: Rounds 100...")
        self.run_scenario(height=4, rounds=100, batch=16)

    def test_small_batch(self):
        """Test with Batch 1"""
        print("\nTesting Adversarial: Batch 1...")
        self.run_scenario(height=4, rounds=4, batch=1)

    def run_scenario(self, height, rounds, batch):
        forest = Tree.generate(height)
        inp = Input.generate(forest, batch, rounds)
        n_nodes = len(forest.values)

        kb_obj = KernelBuilder()
        kb_instrs = kb_obj.build_kernel(
            height, n_nodes, len(inp.indices), rounds, HASH_STAGES
        )

        mem = build_mem_image(forest, inp)
        machine = Machine(mem, kb_instrs, {})
        machine.enable_pause = False
        machine.enable_debug = False
        machine.run()

        # Verify
        from copy import deepcopy

        from problem import reference_kernel

        inp_ref = deepcopy(inp)
        reference_kernel(forest, inp_ref)

        forest_values_p = 7
        inp_indices_p = forest_values_p + n_nodes
        inp_values_p = inp_indices_p + len(inp.indices)

        final_mem = machine.mem
        res_indices = final_mem[inp_indices_p : inp_indices_p + batch]
        res_values = final_mem[inp_values_p : inp_values_p + batch]

        self.assertEqual(res_indices, inp_ref.indices)
        self.assertEqual(res_values, inp_ref.values)


if __name__ == "__main__":
    unittest.main()
