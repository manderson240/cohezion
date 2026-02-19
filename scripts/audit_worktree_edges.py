import os
import shutil
import subprocess
from pathlib import Path
from cohezion.compound.worktree import WorktreeOrchestrator

def audit_worktree_edge_cases():
    print("Starting Audit: Git Worktree Isolation Edge Cases")
    
    # Use a dedicated audit path
    audit_base = Path("/tmp/cohezion_audit_worktree")
    if audit_base.exists():
        shutil.rmtree(audit_base)
    
    orchestrator = WorktreeOrchestrator(base_path=str(audit_base))
    
    # 1. Test session creation
    session_id = "audit_session_1"
    print(f"Allocating worktree for {session_id}...")
    worktree_path = orchestrator.create_session_worktree(session_id)
    
    if os.path.exists(worktree_path) and worktree_path != str(orchestrator.repo_root):
        print(f"✅ SUCCESS: Worktree created at {worktree_path}")
    else:
        print(f"❌ FAILURE: Worktree path invalid or creation failed: {worktree_path}")
        return

    # 2. Test duplicate session ID (Should be idempotent or handle gracefully)
    print("Testing duplicate session allocation...")
    try:
        path2 = orchestrator.create_session_worktree(session_id)
        if path2 == worktree_path:
            print("✅ SUCCESS: Duplicate session handled gracefully (idempotent).")
        else:
            print(f"❌ FAILURE: Duplicate session created different path: {path2}")
    except Exception as e:
        print(f"❌ FAILURE: Duplicate session raised error: {e}")

    # 3. Test invalid session ID (e.g. nested paths) - Should be BLOCKED
    invalid_session = "bad/../../path"
    print(f"Testing invalid session ID: {invalid_session}...")
    try:
        path3 = orchestrator.create_session_worktree(invalid_session)
        print(f"❌ FAILURE: Invalid session produced a path: {path3}")
    except (ValueError, RuntimeError) as e:
        print(f"✅ SUCCESS: Invalid session correctly blocked: {e}")
    except Exception as e:
        print(f"❌ FAILURE: Unexpected error type: {type(e).__name__}: {e}")

    # 4. Cleanup
    print(f"Cleaning up {session_id}...")
    orchestrator.cleanup_session_worktree(session_id)
    if not os.path.exists(worktree_path):
        print("✅ SUCCESS: Worktree removed.")
    else:
        # Check if it's still registered in git
        res = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True)
        if str(worktree_path) in res.stdout:
            print("❌ FAILURE: Worktree still registered in git.")
        else:
            print("✅ SUCCESS: Worktree cleaned up.")

if __name__ == "__main__":
    audit_worktree_edge_cases()
