"""
Universal Cohezion Environment Initialization

Activates in ANY environment that uses Cohezion
(Claude Code, Gemini CLI, Zed IDE, Antigravity, Opencode, OpenClaw, Hermes Agent, terminals, APIs, etc.)
"""

import os
import sys
from pathlib import Path


def is_cohezion_environment() -> bool:
    """
    Detect if we're in a Cohezion environment using multiple signals.
    Works in ANY environment that uses Cohezion.
    """

    # Signal 1: Check if we're importing Cohezion modules (most reliable)
    # This handles the case where __init__.py is being processed
    try:
        frame = sys._getframe(1)
        while frame:
            if "cohezion" in frame.f_code.co_filename:
                return True
            frame = frame.f_back
    except Exception:
        pass  # Continue with other detection methods

    # Signal 2: Check working directory for Cohezion markers
    try:
        cwd = Path.cwd()
        cohezion_markers = [
            "src/cohezion/__init__.py",
            "pyproject.toml",
            "_bmad/",
            "docs/",
            ".opencode/",
            "cohezion_kb.jsonl",
        ]

        marker_count = sum(1 for marker in cohezion_markers if (cwd / marker).exists())
        if marker_count >= 3:  # Require multiple markers to reduce false positives
            return True
    except Exception:
        pass  # Continue with other detection methods

    # Signal 3: Check for Cohezion-specific environment variables
    cohezion_env_vars = [
        "COHEZION_SESSION_ACTIVE",
        "OPENCODE_SESSION_ID",
        "COHEZION_WORKSPACE_MODE",
        "COHEZION_PROJECT_ROOT",
        "COHEZION_SESSION_ID",
    ]

    if any(var in os.environ for var in cohezion_env_vars):
        return True

    # Signal 4: Check if we're in a known Cohezion consumer process
    # This helps with IDE integrations, agents, terminals, etc.
    try:
        import psutil

        current_process = psutil.Process()
        # Check parent process for known Cohezion consumers
        parent = current_process.parent()
        if parent:
            parent_name = parent.name().lower()
            cohezion_consumers = [
                "code",  # VS Code (used by Claude Code, etc.)
                "gemini",  # Gemini CLI
                "zed",  # Zed IDE
                "antigravity",  # Antigravity IDE
                "opencode",  # Opencode
                "openclaw",  # OpenClaw
                "hermes",  # Hermes Agent
                "claude",  # Claude Code
                "python",  # Generic Python
                "node",  # Node.js processes
                "bash",  # Terminal shells
                "zsh",  # Zsh shells
                "fish",  # Fish shells
                "sh",  # Bourne shell
                "cmd",  # Windows Command Prompt
                "powershell",  # Windows PowerShell
                "wt",  # Windows Terminal
                "conhost",  # Windows Console Host
                "tmux",  # Terminal multiplexer
                "screen",  # Terminal multiplexer
                "iterm2",  # iTerm2
                "warp",  # Warp terminal
                "hyper",  # Hyper terminal
                "alacritty",  # Alacritty terminal
                "wezterm",  # WezTerm terminal
                "kitty",  # Kitty terminal
            ]
            if any(consumer in parent_name for consumer in cohezion_consumers):
                # Additional check: are we in Cohezion directory?
                try:
                    if any((cwd / marker).exists() for marker in ["src/cohezion", "pyproject.toml"]):
                        return True
                except Exception:
                    pass  # Continue with other signals
    except ImportError:
        pass  # psutil not available, continue with other signals
    except Exception:
        pass  # Other errors, continue with other signals

    # Signal 5: Check for Cohezion-specific files in parent directories
    # Helps when launched from subdirectories
    try:
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if any((parent / marker).exists() for marker in ["src/cohezion/__init__.py", "pyproject.toml"]):
                # Additional validation: look for more markers
                marker_count = sum(
                    1 for marker in ["_bmad/", "docs/", ".opencode/", "cohezion_kb.jsonl"] if (parent / marker).exists()
                )
                if marker_count >= 2:
                    return True
    except Exception:
        pass  # Continue with other detection methods

    return False


def initialize_cohezion_environment() -> bool:
    """
    Initialize Cohezion environment with TDD + Adversarial Review systems.
    Called automatically when any Cohezion module is imported.
    Works in ANY environment.
    Returns True if initialization was attempted, False if not a Cohezion environment.
    """
    try:
        # Prevent multiple initializations using function attribute
        if getattr(initialize_cohezion_environment, "_initialized", False):
            return True  # Already initialized

        if not is_cohezion_environment():
            return False  # Not a Cohezion environment, do nothing

        # Import initialization systems (lazy import to avoid circular deps)
        try:
            from .daemon.workflow_initializer import get_workflow_initializer
            from .tdd_adversarial import (
                get_adversarial_review_system,
                get_tdd_integration,
                get_tdt_adversarial_coordinator,
            )
        except ImportError:
            # If we can't import our new systems, fail gracefully
            # Don't break Cohezion - just skip initialization
            return True  # Consider it "initialized" by skipping

        # Get current working directory as project root
        try:
            project_root = Path.cwd()
            # Verify it looks like a Cohezion project
            if not (project_root / "src" / "cohezion").exists():
                # Try to find Cohezion root by looking up the directory tree
                for parent in [project_root] + list(project_root.parents):
                    if (parent / "src" / "cohezion").exists():
                        project_root = parent
                        break
                else:
                    # Couldn't find Cohezion root, use current directory as best effort
                    pass
        except Exception:
            project_root = Path.cwd()  # Fallback to current directory

        # Initialize systems
        try:
            initializer = get_workflow_initializer(project_root)
            tdd_system = get_tdd_integration(project_root)
            review_system = get_adversarial_review_system(project_root)
            coordinator = get_tdt_adversarial_coordinator(project_root)
        except Exception:
            # If we can't initialize systems, fail gracefully
            # Don't break Cohezion - just skip initialization
            return True  # Consider it "initialized" by skipping

        # Initialize session if we appear to be in an active session
        # This handles both manual work and automated agent work
        session_id = (
            os.environ.get("COHEZION_SESSION_ID")
            or os.environ.get("OPENCODE_SESSION_ID")
            or f"auto_session_{int(os.times().elapsed)}_{os.getpid()}"
        )

        worktree_created = False
        tdd_ready = False
        review_ready = False
        coordinator_ready = False
        initialization_details = {}

        # Try to create worktree if we're in a proper git repo and it makes sense
        try:
            init_result = initializer.initialize_session(
                session_id=session_id, create_worktree=True, prepare_tdd=True, prepare_review=True
            )
            worktree_created = init_result.get("success", False)
            initialization_details.update(init_result)
        except Exception:
            # Fallback: continue without worktree (current directory work)
            # This is fine for many environments (APIs, batch jobs, etc.)
            pass

        # Initialize core systems (always try these - they should work in current directory)
        try:
            # Quick test that TDD system is working
            _ = tdd_system.get_tdd_metrics(f"init_test_{session_id}")
            tdd_ready = True
        except Exception:
            # TDD system failed to initialize - continue anyway
            pass

        try:
            # Quick test that review system is working
            _ = review_system.get_adversarial_metrics(f"init_test_{session_id}")
            review_ready = True
        except Exception:
            # Review system failed to initialize - continue anyway
            pass

        try:
            # Quick test that coordinator is working
            _ = coordinator.get_integration_metrics(f"init_test_{session_id}")
            coordinator_ready = True
        except Exception:
            # Coordinator system failed to initialize - continue anyway
            pass

        # Mark as initialized to prevent double initialization
        initialize_cohezion_environment._initialized = True
        initialize_cohezion_environment._project_root = str(project_root)
        initialize_cohezion_environment._session_id = session_id
        initialize_cohezion_environment._worktree_created = worktree_created
        initialize_cohezion_environment._initialization_details = initialization_details

        # Log initialization (in a way that works in all environments)
        init_msg = (
            f"[COHEZION_INIT] Environment initialized | "
            f"Session: {session_id[:20]}... | "
            f"Worktree: {'Yes' if worktree_created else 'No'} | "
            f"TDD: {'Ready' if tdd_ready else 'Failed'} | "
            f"Review: {'Ready' if review_ready else 'Failed'} | "
            f"Coordinator: {'Ready' if coordinator_ready else 'Failed'}"
        )

        # Try to log to file, fall back to stdout if file fails
        try:
            log_dir = Path.cwd() / ".opencode" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "universal_init.log", "a") as f:
                f.write(f"{init_msg}\n")
        except Exception:
            # Final fallback to stdout (visible in most environments)
            # Only print if we're likely in an interactive environment
            try:
                if not os.environ.get("COHEZION_NON_INTERACTIVE"):
                    print(init_msg)
            except Exception:
                pass  # Even error reporting failed, continue silently

        return True

    except Exception as e:
        # Never let initialization failures break Cohezion
        # Fail silently to ensure Cohezion always works
        try:
            error_msg = f"[COHEZION_INIT_ERROR] {str(e)[:100]}..."
            # Only print error if we're likely in an interactive environment
            try:
                if not os.environ.get("COHEZION_NON_INTERACTIVE"):
                    print(error_msg)
            except Exception:
                pass  # Even error reporting failed, continue silently
        except Exception:
            pass  # Even error reporting failed, continue silently
        return False  # Indicate initialization was attempted but failed


# Auto-initialization when this module is imported
# This makes the initialization happen whenever Cohezion is imported
initialize_cohezion_environment()
