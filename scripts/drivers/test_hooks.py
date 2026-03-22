"""
Verify Registry Hooks.

Registers a test hook and triggers server actions to ensure events are dispatched.
"""

import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from cohezion.mcp.knowledge_server import get_server as get_knowledge_server
from cohezion.registry.hooks import RegistryHook, get_hook_manager


class TestHook(RegistryHook):
    def __init__(self):
        self.triggered = False

    def on_knowledge_stored(self, entity_id: str, data: dict):
        print(f"HOOK TRIGGERED: {entity_id}")
        self.triggered = True


def verify_hooks():
    # 1. Register Hook
    hook = TestHook()
    get_hook_manager().register_hook(hook)

    # 2. Trigger Action via Server
    server = get_knowledge_server()
    test_entity = {"id": "test_hook_entity", "content": "This is a test for hooks"}

    print("Storing entity...")
    server.store_entity(test_entity)

    # 3. Verify
    if hook.triggered:
        print("✅ Hook verified successfully")

        # Cleanup
        (Path("src/cohezion/knowledge_graph/entities/test_hook_entity.json")).unlink(
            missing_ok=True
        )
        return True
    else:
        print("❌ Hook FAILED to trigger")
        return False


if __name__ == "__main__":
    success = verify_hooks()
    sys.exit(0 if success else 1)
