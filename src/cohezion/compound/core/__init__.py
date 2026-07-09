"""Core executor and batch processing for compound engineering."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.compound.core.batch_processor import (
        BatchProcessor as BatchProcessor,
    )
    from cohezion.compound.core.batch_processor import (
        BatchResult as BatchResult,
    )
    from cohezion.compound.core.batch_processor import (
        SimpleBatch as SimpleBatch,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.core.executor import (
        CompoundExecutor as CompoundExecutor,
    )
    from cohezion.compound.core.executor import (
        ExecutionConfig as ExecutionConfig,
    )
    from cohezion.compound.core.executor import (
        execute_simple as execute_simple,
    )
