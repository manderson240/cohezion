import contextlib


with contextlib.suppress(Exception):
    from cohezion.compound.universal.init import is_cohezion_environment as is_cohezion_environment

with contextlib.suppress(Exception):
    from cohezion.compound.universal.init import (
        initialize_cohezion_environment as initialize_cohezion_environment,
    )
