"""
Populate the skill registry with all existing skill definitions.

Running this module will sync the registry from the filesystem, ensuring
that skill_registry.json stays in sync with the markdown files in the
repository.  Delegates to :func:`auto_sync` which is the single source
of truth for filesystem-driven registration.
"""

from cohezion.registry.skill_registry import auto_sync


def _register_all() -> int:
    """Sync all skills from src/cohezion/skills/*.md into skill_registry.json.

    Returns
    -------
    int
        Number of skills synced.
    """
    return auto_sync()


if __name__ == "__main__":
    count = _register_all()
    print(f"Synced {count} skills into skill_registry.json")
