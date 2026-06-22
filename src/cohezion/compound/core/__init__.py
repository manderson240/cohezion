"""Core executor and batch processing for compound engineering."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.core.batch_processor import (
        BatchProcessor as BatchProcessor,
        BatchResult as BatchResult,
        SimpleBatch as SimpleBatch,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.core.executor import (
        CompoundExecutor as CompoundExecutor,
        ExecutionConfig as ExecutionConfig,
        execute_simple as execute_simple,
    )
