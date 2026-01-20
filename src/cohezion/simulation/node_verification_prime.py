"""
Node Verification Prime (Gateway 10).

Simulates a Consensus Client logic:
1. Listens for "blocks" (mocked or real headers).
2. Verifies their validity (CPU intensive hashing checks).
3. "Minting" only occurs if verification passes AND ResourceMonitor says OK.
"""

import asyncio
import hashlib
import logging
import random
import time
from typing import Dict, Optional

from cohezion.core.resource_monitor import get_resource_monitor
from cohezion.core.time_keeper import get_time_keeper
from cohezion.core.credit_manager import get_credit_manager

logger = logging.getLogger(__name__)

# Credits earned per block verified
CREDITS_PER_BLOCK = 1

class NodeVerificationPrime:
    def __init__(self):
        self.monitor = get_resource_monitor()
        self.tk = get_time_keeper()
        self._running = False
        self._metrics = {
            "blocks_verified": 0,
            "rent_paused_count": 0,
            "yield_generated": 0.0
        }

    async def run_verification_loop(self, duration_seconds: int = 10):
        """
        Run the verification loop for a set duration.
        """
        self._running = True
        end_time = time.time() + duration_seconds
        
        logger.info("Starting Node Verification Loop...")
        
        while time.time() < end_time and self._running:
            # 1. Check Resources
            if not self.monitor.should_rent():
                self._metrics["rent_paused_count"] += 1
                await asyncio.sleep(1) # Backoff
                continue
            
            # 2. "Fetch" Block (Simulated)
            block = self._fetch_mock_block()
            
            # 3. Verify Block (CPU Work)
            valid = await self._verify_block(block)
            
            if valid:
                self._metrics["blocks_verified"] += 1
                self._metrics["yield_generated"] += 0.001 # Mock yield
                
                # Credit the SwarmPool for verified work
                cm = get_credit_manager()
                cm.credit("SwarmPool", CREDITS_PER_BLOCK)
                
                await self.tk.log_event(
                    "NodeVerifier", 
                    "BLOCK_VERIFIED", 
                    {"block_hash": block["hash"], "yield": 0.001, "credits_earned": CREDITS_PER_BLOCK}
                )
            
            # Sleep to prevent 100% CPU hogging even when allowed
            await asyncio.sleep(0.1)
            
        logger.info(f"Verification Loop Complete. Metrics: {self._metrics}")
        return self._metrics

    def _fetch_mock_block(self) -> Dict[str, str]:
        """Generate a random block data."""
        data = f"block_data_{random.randint(0, 1000000)}_{time.time()}"
        return {
            "data": data,
            "hash": hashlib.sha256(data.encode()).hexdigest(),
            "prev_hash": "0000..."
        }

    async def _verify_block(self, block: Dict[str, str]) -> bool:
        """
        Simulate verification logic.
        Double SHA256 hashing to burn some CPU cycles.
        """
        # Burn cycles
        data = block["data"]
        for _ in range(1000):
            data = hashlib.sha256(data.encode()).hexdigest()
            
        # Check against block hash (trivial check here, but mimics content validation)
        recalc_hash = hashlib.sha256(block["data"].encode()).hexdigest()
        return recalc_hash == block["hash"]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    verifier = NodeVerificationPrime()
    asyncio.run(verifier.run_verification_loop(5))
