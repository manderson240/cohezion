"""
Residency Awareness for Cohezion.
Codifies the physical hardware roots of the system (Truth Anchors).
"""

from typing import Any


class ResidencyAnchorBase:
    """Base class for residency identification."""

    # SYSTEM IDENTITY - THE TRUTH ANCHORS
    SYSTEM_OS = "Linux"
    SYSTEM_HOSTNAME = "framework-16"
    SYSTEM_CPU = "AMD RYZEN AI MAX+ 395 (Strix Halo)"
    SYSTEM_GPU = "AMD Radeon 8060S"
    SYSTEM_RAM_GB = 128
    SYSTEM_ARCHITECTURE = "AMD64 / Strix Halo UMA"

    # PROJECT ROOT
    PROJECT_ROOT = "/home/mike-anderson/dev/cohezion"

    @classmethod
    def get_anchors(cls) -> dict[str, Any]:
        """Return the codified truth anchors."""
        return {
            "os": cls.SYSTEM_OS,
            "hostname": cls.SYSTEM_HOSTNAME,
            "cpu": cls.SYSTEM_CPU,
            "gpu": cls.SYSTEM_GPU,
            "ram_gb": cls.SYSTEM_RAM_GB,
            "architecture": cls.SYSTEM_ARCHITECTURE,
            "project_root": cls.PROJECT_ROOT,
        }

    @classmethod
    def get_context_block(cls) -> str:
        """Return a formatted block for LLM context injection."""
        anchors = cls.get_anchors()
        return f"""
[SYSTEM RESIDENCY ANCHORS]
- **Hardware**: {anchors["cpu"]}
- **Graphics**: {anchors["gpu"]}
- **Memory**: {anchors["ram_gb"]}GB DDR5 (128GB Physical)
- **Architecture**: {anchors["architecture"]}
- **Hostname**: {anchors["hostname"]}
- **Root**: {anchors["project_root"]}
- **Note**: This is a high-performance Strix Halo substrate.
- **Guidance**: Prioritize local inference (Ollama) and high-density 12D state vectors.
""".strip()


def get_residency_anchors() -> dict[str, Any]:
    """Helper to get truth anchors."""
    return ResidencyAnchorBase.get_anchors()


if __name__ == "__main__":
    print(ResidencyAnchorBase.get_context_block())
