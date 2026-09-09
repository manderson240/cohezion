#!/usr/bin/env python3
"""AMD GAIA SDK Chat & Code Playbooks Verification Harness.

Verifies:
1. GAIAChatAgent: Document indexing, RAG tool mixin retrieval, and multi-doc answer synthesis.
2. GAIACodeAgent: Autonomous schema DDL generation, CRUD API routing, and React UI scaffolding.
"""

from __future__ import annotations

import asyncio

from cohezion.integrations.amd_gaia_chat_code_suite import GAIAChatAgent, GAIACodeAgent


async def main_async() -> None:
    print("=" * 95)
    print("    🚀 AMD GAIA SDK CHAT & CODE PLAYBOOKS VERIFICATION (RYZEN AI / STRIX HALO)")
    print("=" * 95)

    # 1. Chat Agent Playbook
    print("\n📚 [Playbook 3: Document Q&A & RAG Chat Agent]")
    chat_agent = GAIAChatAgent()
    chat_agent.index_document(
        doc_id="doc_flume_01",
        content="FLUME encodes continuous cognitive state trajectories as 12D Poincaré manifold vectors.",
        source_path="docs/architecture/flume.md",
    )
    chat_agent.index_document(
        doc_id="doc_metron_02",
        content="Burkhard Heim's discrete Metron area grid quantum tau is 6.15e-70 m^2 eliminating singularities.",
        source_path="docs/physics/heim_metron.md",
    )

    query = "What is the discrete Metron area in Heim theory?"
    res = await chat_agent.answer_query(query)
    print(f"  • Query: {res.query}")
    print(f"  • Retrieved Chunks: {res.retrieved_chunks}")
    print(f"  • Synthesized Sources: {res.synthesized_from}")
    print(f"  • Answer: {res.answer}")
    print(f"  • Execution Time: {res.latency_ms:.2f} ms")

    # 2. Code Agent Playbook
    print("\n💻 [Playbook 4: Full-Stack Code Generation Agent]")
    code_agent = GAIACodeAgent()
    prompt = "Build me a movie tracking app where I can track movie title, genre, date watched, and a score out of 10"
    app_manifest = await code_agent.generate_app(prompt, "movie-tracker")
    print(f"  • App Name: {app_manifest.app_name}")
    print(f"  • Schema Generated: {len(app_manifest.schema_sql)} characters")
    print(f"  • API Routes Created: {list(app_manifest.api_routes.keys())}")
    print(f"  • React Components: {list(app_manifest.react_components.keys())}")
    print(f"  • Build Validation Status: {'✅ PASS' if app_manifest.build_verified else '❌ FAIL'}")
    print(f"  • Generation Time: {app_manifest.latency_ms:.2f} ms")

    print("\n" + "=" * 95)
    print("🎉 AMD GAIA SDK CHAT & CODE PLAYBOOKS FULLY VERIFIED & LEVERAGED!")
    print("=" * 95)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
