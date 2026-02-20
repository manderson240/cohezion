"""Verification test for hierarchical swarm topology."""

import asyncio

from cohezion.swarm.executive import SovereignExecutive


async def test_topology_hierarchy():
    print("Initializing SovereignExecutive...")
    exec_agent = SovereignExecutive(mission_name="Omega_Discovery")

    print("Creating regional swarms...")
    swarm1 = exec_agent.create_regional_swarm(
        domain="physics_sim", capabilities=["manifold_encoding", "hamiltonian_dynamics"]
    )
    swarm2 = exec_agent.create_regional_swarm(
        domain="core_codebase", capabilities=["rust_binding", "simd_optimization"]
    )

    print(f"Swarm 1 ID: {swarm1}")
    print(f"Swarm 2 ID: {swarm2}")

    report = exec_agent.get_topology_report()
    print("\nTopology Report:")
    print(f"Executive Node: {report['executive_id']}")
    for sid, r in report["regions"].items():
        print(f"  - Region {sid} [{r['domain']}]: Lead with {r['lead_capabilities']}")

    print("\nSimulating mission execution...")
    result = await exec_agent.execute_mission("Optimize FlumePhysics kernel for AVX2")
    print(f"Mission Status: {result['status']}")
    print(f"Topology Link: {result['topology_id']}")


if __name__ == "__main__":
    asyncio.run(test_topology_hierarchy())
