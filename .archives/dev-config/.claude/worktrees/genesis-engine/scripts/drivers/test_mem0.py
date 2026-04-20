
from mem0 import Memory


def test_local_mem0():
    print("Initializing Mem0 Memory...")
    # Attempt local config
    config = {
        "vector_store": {"provider": "qdrant", "config": {"path": "test_mem0_db"}},
        "history_db_path": "test_mem0_history.db",
    }

    try:
        m = Memory.from_config(config)
        print("Memory initialized.")

        print("Adding memory...")
        m.add("The user prefers pragmatic solutions over hype.", user_id="test_user")

        print("Searching memory...")
        results = m.search("What does the user prefer?", user_id="test_user")
        print(f"Results: {results}")

    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    test_local_mem0()
