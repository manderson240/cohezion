"""Cohezion Quantum Computing & Simulation Bridge."""


class QuantumBackendUnavailableError(RuntimeError):
    """No real quantum backend can run the job (SDK missing, client init failed, no token).

    Raised instead of returning placeholder results: a caller that uses measurement
    counts as an oracle must never be handed values that were not measured.
    """
