"""Secure sandboxed execution for agentic tasks.

Containerized/isolated execution environments for untrusted code.
"""

from cohezion.sandboxing.executor import (
    DockerSandbox,
    FirecrackerSandbox,
    ResourceLimits,
    SandboxManager,
    SandboxResult,
)


__all__ = [
    "DockerSandbox",
    "FirecrackerSandbox",
    "ResourceLimits",
    "SandboxManager",
    "SandboxResult",
]
