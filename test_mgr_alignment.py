import asyncio
import logging
import sys
from cohezion.compound.session_manager import CompoundSessionManager

logging.basicConfig(level=logging.INFO, stream=sys.stderr)

async def test_alignment():
    print("Initializing manager...")
    async with CompoundSessionManager() as mgr:
        print("Starting session...")
        mgr.start_session(max_cache_entries=10)
        
        prompt = "Test ARC-AGI prompt for alignment."
        print(f"Checking alignment for: {prompt}")
        
        # This is where it might be hanging
        result = mgr.check_alignment(prompt, threshold=0.5)
        
        print(f"Alignment result: {result.coherence}")
        print(f"Should proceed: {result.should_proceed}")
        
        mgr.end_session()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(test_alignment())
