import contextlib

with contextlib.suppress(Exception):
    from cohezion.physics.quantum.utils import compute_seti_metrics as compute_seti_metrics

with contextlib.suppress(Exception):
    from cohezion.physics.quantum.peaked_solver import PeakedCircuitSolver as PeakedCircuitSolver
