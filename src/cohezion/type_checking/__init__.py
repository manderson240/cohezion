"""Cohezion Type Checking Subsystem with Pyrefly Integration."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.type_checking.pyrefly_adapter import (
        PyreflyAdapter as PyreflyAdapter,
    )
    from cohezion.type_checking.pyrefly_adapter import (
        PyreflyDiagnostic as PyreflyDiagnostic,
    )
    from cohezion.type_checking.pyrefly_adapter import (
        PyreflyResult as PyreflyResult,
    )
