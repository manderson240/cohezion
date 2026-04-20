# changes to this file require a backend change


JOB_NO_RESULT_TERMINAL_STATES = {
    "FAILED_VALIDATION",
    "CANCELED",
    "TERMINATED",
    "NOT_ENOUGH_FUNDS",
    "JOBS_LIMIT_EXCEEDED",
}
JOB_RESULTS_READY_STATES = {"COMPLETED"}
JOB_TERMINAL_STATES = JOB_RESULTS_READY_STATES.union(JOB_NO_RESULT_TERMINAL_STATES)
JOB_NON_TERMINAL_STATES = {"PENDING", "QUEUED", "RUNNING"}
JOB_STATES = JOB_NON_TERMINAL_STATES.union(JOB_TERMINAL_STATES)

DEVICE_TYPES = {
    "cpu",
    "gpu",
    "quantum",
    "tensor-network",
    "pennylane.cpu",
    "pennylane.gpu",
    "pennylane.cpu.adjoint",
    "pennylane.gpu.adjoint",
    "mps.cpu",  # Dec 2024
    "mps.gpu",
    "pauli-path",  # Dec 2024
    "pauli-path.gpu",  # Oct 2025
}

# Map GPU devices to their CPU counterparts for fallback in local execution mode
DEVICE_FALLBACK_MAPPING = {
    "gpu": "cpu",
    "mps.gpu": "mps.cpu",
    "pauli-path.gpu": "pauli-path",
    "pennylane.gpu": "pennylane.cpu",
    "pennylane.gpu.adjoint": "pennylane.cpu.adjoint",
}

MAXIMUM_NUMBER_OF_BATCH_JOBS = 500

QUEUED_CPU_JOBS_LIMIT = 5

MAXIMUM_NUMBER_OF_JOBS_FOR_RUN = 50

MAX_QUBITS_WITH_STATEVEC = 16

MAXIMUM_NUMBER_OF_SHOTS = dict.fromkeys(DEVICE_TYPES, 100_000)
MAXIMUM_NUMBER_OF_SHOTS["mps.cpu"] = 1_000_000
MAXIMUM_NUMBER_OF_SHOTS["mps.gpu"] = 1_000_000

MAX_MPS_CPU_BOND_DIMENSION = 2048
MAX_MPS_GPU_BOND_DIMENSION = 4000
MAX_TWO_QUBIT_GATE_COUNT = {"mps.cpu": 10_000, "pauli-path": 3000}

MPS_DEFAULT_BOND_DIMENSION = 256
MPS_DEFAULT_TRUNCATION_THRESHOLD = 1e-10

# smallest truncation threshold that is currently supported for pauli-path jobs
MIN_PAULI_PATH_TRUNCATION_THRESHOLD = 1e-5
PAULI_PATH_CIRCUIT_TRANSPILATION_LEVELS = {0, 1, 2, 3}
PAULI_PATH_DEFAULT_TRANSPILATION_LEVEL = 2

# Maximum size in bytes for serialized circuit data
MAXIMUM_SERIALIZED_CIRCUIT_SIZE = 10_000_000  # 10 MB
MAX_JOB_TAGS_SIZE = 1_000_000  # 1 MB

MAX_JOB_NAME_LENGTH = 200
