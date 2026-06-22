"""Persistence sub-package for compound engineering."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.persistence.vault import (
        PersistenceConfig as PersistenceConfig,
        SessionPersister as SessionPersister,
        SimplePersistence as SimplePersistence,
        VaultPersister as VaultPersister,
    )
