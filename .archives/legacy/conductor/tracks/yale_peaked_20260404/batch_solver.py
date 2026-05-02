import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from solve_peaked_circuit import solve_peaked_circuit


class BatchSolver:
    """
    Handles parallel execution and SHA-256 caching of peaked circuit problems.
    """

    def __init__(self, max_workers=2, cache_dir="conductor/tracks/yale_peaked_20260404/cache"):
        self.max_workers = max_workers
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_hash(self, path, shots, device, bond_dim):
        """
        Creates a SHA-256 hash of the problem's parameters and circuit content.
        """
        with open(path) as f:
            content = f.read()

        # Salt the hash with the parameters
        params = f"{content}|{shots}|{device}|{bond_dim}"
        return hashlib.sha256(params.encode()).hexdigest()

    def _get_cache(self, h):
        """
        Returns cached results if they exist.
        """
        cache_path = os.path.join(self.cache_dir, f"{h}.json")
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return json.load(f)
        return None

    def _set_cache(self, h, result):
        """
        Saves results to the cache.
        """
        cache_path = os.path.join(self.cache_dir, f"{h}.json")
        with open(cache_path, "w") as f:
            json.dump(result, f, indent=2)

    def solve_all(self, problems, shots=100000, device="mps.cpu", bond_dim=None, allow_paid=False):
        """
        Solves a dictionary of problems {name: qasm_path}.
        Uses SHA-256 caching to avoid redundant API calls.
        """
        results = {}
        to_run = {}
        hashes = {}

        # First, check the cache
        for name, path in problems.items():
            h = self._get_hash(path, shots, device, bond_dim)
            hashes[name] = h
            cached = self._get_cache(h)

            if cached:
                print(f"📦 Cache Hit: {name} ({h[:8]})")
                results[name] = cached
            else:
                to_run[name] = path

        if not to_run:
            return results

        print(f"🚀 Batch Executing {len(to_run)} problems on {device}...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map futures to problem names
            future_to_name = {
                executor.submit(
                    solve_peaked_circuit,
                    path,
                    shots=shots,
                    bond_dim=bond_dim,
                    device=device,
                    allow_paid=allow_paid,
                ): name
                for name, path in to_run.items()
            }

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                h = hashes[name]
                try:
                    result = future.result()
                    if result:
                        results[name] = result
                        # Store in cache
                        self._set_cache(h, result)
                        print(
                            f"✅ Completed: {name} -> {result['bitstring']} (SNR: {result['snr']:.2f})"
                        )
                    else:
                        print(f"❌ Failed: {name} (No result)")
                except Exception as e:
                    print(f"❌ Error in {name}: {e}")

        return results
