import asyncio
from pathlib import Path

from cohezion.agents.lab_agent import LabAgent


async def verify_integration():
    print("🚀 Verifying Simulation Infrastructure Integration...")

    # 1. Initialize LabAgent
    agent = LabAgent()

    # 2. Run a One-Shot Cycle
    # We mock most of the heavy lifting to verify the data flow
    seed = "Fractal Toroidal vortex stability in exotic vacuum objects (EVOs)."
    report = (
        "✅ VERIFIED: HYPOTHESIS: Vortex stability is proportional to phi. CODE: print('verifying') OUTCOME: Success."
    )

    print("🛠️ Manually processing discovery findings...")
    await agent._process_findings(seed, report)

    # 3. Verify SimulationLogger output
    storage_dir = Path("data/simulations")
    agent.sim_logger.flush()  # Force flush

    shards = list(storage_dir.glob("*.parquet"))
    print(f"📁 Found {len(shards)} shards in {storage_dir}")
    assert len(shards) > 0, "No shards found!"

    # 4. Load and inspect dataset
    dataset = agent.sim_logger.load_universe_data()
    print(f"📊 Dataset size: {len(dataset)}")
    assert len(dataset) > 0, "Dataset is empty!"

    entry = dataset[0]
    print(f"🔍 Inspecting first entry: Domain={entry['universe_domain']}, Phiscore={entry['phi_score']:.2f}")
    assert entry["universe_domain"] == "physics"
    assert "EVO" in entry["seed_thought"]

    # Cleanup (Optional)
    # shutil.rmtree("data/simulations")

    print("\n✅ Simulation Infrastructure Integration Verified!")


if __name__ == "__main__":
    asyncio.run(verify_integration())
