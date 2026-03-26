import asyncio
import os

import torch

from cohezion.flume.bridge import HFEmbeddingBridge
from cohezion.universe.triune_manifold import TriuneState


KERNEL_SRC_DIR = "hip-kernels-kimi-k2-5/src"

async def ingest_kernels():
    print(f"🚀 Starting ingestion of kernels from {KERNEL_SRC_DIR}...")

    # Initialize the bridge with target_dim=2048 for the Knower layer
    bridge = HFEmbeddingBridge(target_dim=2048)

    kernel_files = [f for f in os.listdir(KERNEL_SRC_DIR) if f.endswith(".hip")]

    for filename in kernel_files:
        path = os.path.join(KERNEL_SRC_DIR, filename)
        with open(path) as f:
            code = f.read()

        print(f"  - Encoding {filename}...")

        # Get 2048D embedding for the code
        # HFEmbeddingBridge uses sentence-transformers which works well for code snippets too
        knower_vector = await bridge.get_flume_input(code)

        # knower_vector might be (1, 2048), we need (2048,)
        if knower_vector.dim() == 2:
            knower_vector = knower_vector.squeeze(0)

        # Initialize a blank TriuneState with the encoded Knower layer
        state = TriuneState(
            doer=torch.zeros(12),
            thinker=torch.zeros(512),
            knower=knower_vector
        )

        print(f"    ✅ Encoded into Knower layer (norm: {state.knower.norm():.4f})")

        # In a real run, we would persist this to SurrealDB and Obsidian here.
        # For this task, we are demonstrating the ingestion and encoding logic.

    print(f"\n📊 Ingestion complete for {len(kernel_files)} kernels.")

if __name__ == "__main__":
    asyncio.run(ingest_kernels())
