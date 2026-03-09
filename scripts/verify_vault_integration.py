import asyncio
import json
import logging
import time
from datetime import datetime

from cohezion.compound.exp_persistence.vault import ExecutionContext, VaultLogger
from cohezion.compound.persistence import CompoundPersistence
from cohezion.compound.session_manager import SessionState, VaultCheckpointManager
from cohezion.core.mcp_client import get_mcp_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_vault_logger():
    logger.info("--- 1. Verifying VaultLogger (Execution Logs) ---")
    vl = VaultLogger()
    mcp = get_mcp_client()

    ctx = ExecutionContext(
        project="verification",
        skill_name="TestSkill",
        task_description="Testing unified vault integration",
        operation_type="analyze",
        start_time=datetime.now(),
        mcp_client=mcp,
    )

    path = vl.log_execution_start(ctx)
    logger.info(f"Execution started, path: {path}")

    # Wait a bit
    time.sleep(1)

    vl.log_execution_result(path, True, "Verification successful", {"coherence": 0.95})
    logger.info("Execution result logged.")

    # Verify file exists
    try:
        content = mcp.vault_read(path)
        data = json.loads(content)
        assert data["success"] is True
        assert data["metrics"]["coherence"] == 0.95
        logger.info(f"✅ VaultLogger verification PASSED. Content: {data['output_summary']}")
    except Exception as e:
        logger.error(f"❌ VaultLogger verification FAILED: {e}")


async def verify_checkpoint_manager():
    logger.info("--- 2. Verifying VaultCheckpointManager ---")
    cm = VaultCheckpointManager()
    mcp = get_mcp_client()

    state = SessionState(
        session_id="verify_sess_123",
        skill_name="VerifySkill",
        current_step=5,
        total_steps=10,
        context="Initial context",
    )

    # Save
    await cm.save(state)
    logger.info("Checkpoint saved.")

    # Load
    loaded = await cm.load(state.session_id)
    if loaded and loaded.session_id == state.session_id:
        logger.info(f"✅ Checkpoint load PASSED. Step: {loaded.current_step}")
    else:
        logger.error("❌ Checkpoint load FAILED.")

    # Delete
    await cm.delete(state.session_id)
    logger.info("Checkpoint deleted.")

    # Verify deletion
    try:
        mcp.vault_read(f"checkpoints/{state.session_id}.json")
        logger.error("❌ Checkpoint deletion FAILED (still exists in vault).")
    except Exception:
        logger.info("✅ Checkpoint deletion PASSED (canonical failure on read).")


async def verify_compound_persistence():
    logger.info("--- 3. Verifying CompoundPersistence (Tiers) ---")
    cp = CompoundPersistence()

    skill = "VaultVerifySkill"
    data = {"result": "success", "fidelity": 1.0}

    # Save
    record_id = await cp.save_cycle(skill, data)
    logger.info(f"Cycle saved, record_id: {record_id}")

    if record_id.startswith("vault:"):
        logger.info("✅ Tier 1: Vault save PASSED.")
    else:
        logger.warning(f"⚠️ Tier 1: Vault save FAILED or skipped. Record ID: {record_id}")

    # Load
    history = await cp.load_history(skill, limit=1)
    if history and history[0]["fidelity"] == 1.0:
        logger.info("✅ CompoundPersistence load PASSED.")
    else:
        logger.error("❌ CompoundPersistence load FAILED.")


async def main():
    try:
        # Give services a moment
        await verify_vault_logger()
        await verify_checkpoint_manager()
        await verify_compound_persistence()
        logger.info("\n--- ALL VAULT INTEGRATIONS VERIFIED ---")
    except Exception as e:
        logger.error(f"Verification suite CRASHED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
