"""Persistence sub-package for compound engineering."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.compound.persistence.vault import (
        PersistenceConfig as PersistenceConfig,
    )
    from cohezion.compound.persistence.vault import (
        SessionPersister as SessionPersister,
    )
    from cohezion.compound.persistence.vault import (
        SimplePersistence as SimplePersistence,
    )
    from cohezion.compound.persistence.vault import (
        VaultPersister as VaultPersister,
    )
