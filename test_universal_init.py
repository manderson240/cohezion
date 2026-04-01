#!/usr/bin/env python3
"""Test the universal initialization system in isolation."""

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
            if 'cohezion' in frame.f_code.co_filename:
                return True
            frame = frame.f_back
    except Exception:
        pass  # Continue with other detection methods
    
    # Signal 2: Check working directory for Cohezion markers
    try:
        cwd = Path.cwd()
        cohezion_markers = [
            'src/cohezion/__init__.py',
            'pyproject.toml', 
            '_bmad/',
            'docs/',
            '.opencode/',
            'cohezion_kb.jsonl'
        ]
        
        marker_count = sum(1 for marker in cohezion_markers 
                          if (cwd / marker).exists())
        if marker_count >= 3:  # Require multiple markers to reduce false positives
            return True
    except Exception:
        pass  # Continue with other detection methods
        
    # Signal 3: Check for Cohezion-specific environment variables
    cohezion_env_vars = [
        'COHEZION_SESSION_ACTIVE',
        'OPENCODE_SESSION_ID', 
        'COHEZION_WORKSPACE_MODE',
        'COHEZION_PROJECT_ROOT',
        'COHEZION_SESSION_ID'
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
                'code',           # VS Code (used by Claude Code, etc.)
                'gemini',         # Gemini CLI
                'zed',            # Zed IDE
                'antigravity',    # Antigravity IDE
                'opencode',       # Opencode
                'openclaw',       # OpenClaw
                'hermes',         # Hermes Agent
                'claude',         # Claude Code
                'python',         # Generic Python
                'node',           # Node.js processes
                'bash',           # Terminal shells
                'zsh',            # Zsh shells
                'fish',           # Fish shells
                'sh',             # Bourne shell
                'cmd',            # Windows Command Prompt
                'powershell',     # Windows PowerShell
                'wt',             # Windows Terminal
                'conhost',        # Windows Console Host
                'tmux',           # Terminal multiplexer
                'screen',         # Terminal multiplexer
                'iterm2',         # iTerm2
                'warp',           # Warp terminal
                'hyper',          # Hyper terminal
                'alacritty',      # Alacritty terminal
                'wezterm',        # WezTerm terminal
                'kitty'           # Kitty terminal
            ]
            if any(consumer in parent_name for consumer in cohezion_consumers):
                # Additional check: are we in Cohezion directory?
                try:
                    if any((cwd / marker).exists() for marker in ['src/cohezion', 'pyproject.toml']):
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
            if any((parent / marker).exists() for marker in ['src/cohezion/__init__.py', 'pyproject.toml']):
                # Additional validation: look for more markers
                marker_count = sum(1 for marker in [
                    '_bmad/', 'docs/', '.opencode/', 'cohezion_kb.jsonl'
                ] if (parent / marker).exists())
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
        if getattr(initialize_cohezion_environment, '_initialized', False):
            return True  # Already initialized
            
        if not is_cohezion_environment():
            return False  # Not a Cohezion environment, do nothing
            
        # For this test, we'll just return True to indicate we would initialize
        # In the real implementation, this would initialize the actual systems
        initialize_cohezion_environment._initialized = True
        return True
        
    except Exception as e:
        # Never let initialization failures break Cohezion
        # Fail silently to ensure Cohezion always works
        return False  # Indicate initialization was attempted but failed

# Auto-initialization when this module is imported
# This makes the initialization happen whenever the module is imported
if __name__ != "__main__":
    initialize_cohezion_environment()

if __name__ == "__main__":
    print("Testing universal initialization system...")
    print(f"Is Cohezion environment: {is_cohezion_environment()}")
    result = initialize_cohezion_environment()
    print(f"Initialization result: {result}")
    print("Universal initialization system test completed.")
