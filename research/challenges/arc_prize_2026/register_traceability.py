import asyncio
from pathlib import Path
from cohezion.knowledge_graph.bidirectional_linker import (
    get_knowledge_graph,
    link_doc_to_code,
    link_doc_to_doc,
)


async def register_arc_traceability():
    print("Registering ARC Prize 2026 Traceability...")

    kg = get_knowledge_graph()
    try:
        await kg.connect()
    except Exception as e:
        print(
            f"  Note: Could not connect to SurrealDB ({e}). Proceeding with vault-only persistence."
        )

    project_root = Path.cwd()
    plan_file = str(project_root / "conductor/tracks/arc_prize_2026_20260327/plan.md")
    deep_plan_file = str(project_root / "conductor/arc_deep_synthesis_plan.md")

    # 1. Link Plans to each other
    await link_doc_to_doc(
        source_doc=plan_file,
        target_doc=deep_plan_file,
        reason="arc_deep_synthesis_plan.md provides advanced implementation details for the main competition plan.",
    )

    # 2. Link Plan to Core Implementations
    implementations = [
        ("research/challenges/arc_prize_2026/arc_gym_wrapper.py", "ARC-AGI-3 Environment Wrapper"),
        ("research/challenges/arc_prize_2026/arc_jepa.py", "JEPA World Model & Encoder"),
        (
            "research/challenges/arc_prize_2026/arc_topology_navigation.py",
            "Topological Navigation & Search",
        ),
        ("research/challenges/arc_prize_2026/arc_bioelectric.py", "Bioelectric Pattern Discovery"),
        (
            "research/challenges/arc_prize_2026/arc_cosmogony_synthesizer.py",
            "Cosmogonic Program Synthesis",
        ),
    ]

    for code_rel_path, section in implementations:
        code_file = str(project_root / code_rel_path)
        await link_doc_to_code(doc=deep_plan_file, code_file=code_file, section=section)
        print(f"  Linked: {section} -> {code_rel_path}")

    # 3. Link to Physics Foundation
    cosmogony_core = str(project_root / "src/cohezion/physics/cosmogony.py")
    await link_doc_to_code(
        doc=deep_plan_file, code_file=cosmogony_core, section="Cosmogony Foundation"
    )

    print("\nTraceability registration complete.")


if __name__ == "__main__":
    asyncio.run(register_arc_traceability())
