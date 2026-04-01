import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cohezion.knowledge_graph.bidirectional_linker import (
    LinkType,
    get_knowledge_graph,
)


async def register_breakthroughs():
    kg = get_knowledge_graph()
    
    # Mock connection if client not available (just for vault persistence)
    await kg.connect()
    
    breakthrough_doc = "/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault/cerebellum/luma-amd-breakthroughs-20260323.md"
    
    links = [
        {
            "target": "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mixed-mla/submission_triton_flash.py",
            "type": LinkType.DECISION_TO_CODE,
            "meta": {"rationale": "Transition to persistent Triton FlashMLA to bypass dispatch floor"}
        },
        {
            "target": "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/staging/submission_gate2_expert_mask.py",
            "type": LinkType.DECISION_TO_CODE,
            "meta": {"rationale": "Active-expert masking to skip compute for empty experts"}
        },
        {
            "target": "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/submission_triton_v4.py",
            "type": LinkType.DECISION_TO_CODE,
            "meta": {"rationale": "Triton dot_scaled optimization for CDNA 4"}
        },
        {
            "target": "stream_integrity_fix",
            "type": LinkType.PATTERN_TO_CODE,
            "meta": {"rationale": "Explicitly pass torch.cuda.current_stream().cuda_stream to all HIP/ctypes calls to avoid 500 error"}
        }
    ]
    
    for link in links:
        await kg.add_link(
            source=breakthrough_doc,
            target=link["target"],
            link_type=link["type"],
            metadata=link["meta"]
        )
        print(f"Registered link: {breakthrough_doc} -> {link['target']}")

if __name__ == "__main__":
    asyncio.run(register_breakthroughs())
