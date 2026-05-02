from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from . import job_metadata_constants
from .api import circuits, jobs
from .backend_connection import BackendConnection
from .check_version import check_version
from .circuit_serialization import is_a_pennylane_circuit, is_a_qiskit_circuit
from .estimate_result import EstimateResult
from .exceptions import (
    BQBatchJobsLimitExceededError,
    BQCPUJobsLimitExceededError,
    BQJobCouldNotCancelError,
    BQJobInvalidDeviceTypeError,
    BQJobNotCompleteError,
    BQJobsLimitExceededError,
    BQJobsMalformedShotsError,
    BQSDKUsageError,
)
from .job_result import JobResult
from .local_execution import run_circuits_local
from .version import __version__


if TYPE_CHECKING:
    import datetime

# TODO this requires imports of actual quantum libraries for proper type
# checking.
CircuitT = Any

PauliSumT = list[tuple[str, float]] | str

logger = logging.getLogger("bluequbit-python-sdk")


class BQClient:
    """Client for managing jobs on BlueQubit platform.

    :param api_token: API token of the user. If ``None``, the token will be looked
                      in the environment variable BLUEQUBIT_API_TOKEN.
    :param execution_mode: Execution mode. Can be ``"cloud"``, ``"local"`` or ``None``.
                           If ``None``, the environment variable
                           BLUEQUBIT_EXECUTION_MODE will be used if set, otherwise
                           ``"cloud"`` will be used.
    """

    _job_name_prefix_cls: str | None = None

    def __init__(self, api_token: str | None = None, execution_mode: str | None = None):
        super().__init__()
        if os.environ.get("BLUEQUBIT_TESTING") is None:
            with contextlib.suppress(Exception):
                check_version(__version__)

        if execution_mode is None:
            if "BLUEQUBIT_EXECUTION_MODE" in os.environ:
                execution_mode = os.environ["BLUEQUBIT_EXECUTION_MODE"]
                logger.info(
                    "Using execution mode from environment variable BLUEQUBIT_EXECUTION_MODE: %s",
                    execution_mode,
                )
            else:
                execution_mode = "cloud"
        self.execution_mode = execution_mode
        if self.execution_mode not in ["cloud", "local"]:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

        self._backend_connection = BackendConnection(api_token)

        self.job_name_prefix: str | None = BQClient._job_name_prefix_cls

    def name(self):
        return "BlueQubit"

    def validate_device(self, device):
        if not isinstance(device, str):
            raise BQJobInvalidDeviceTypeError(device)
        converted_device = device.lower()
        if converted_device not in job_metadata_constants.DEVICE_TYPES:
            raise BQJobInvalidDeviceTypeError(device)
        return converted_device

    @staticmethod
    def validate_batch(batch):
        if not isinstance(batch, list):
            return False
        if len(batch) > job_metadata_constants.MAXIMUM_NUMBER_OF_BATCH_JOBS:
            raise BQBatchJobsLimitExceededError(len(batch))
        return True

    @staticmethod
    def validate_batch_for_run(batch, device):
        if not BQClient.validate_batch(batch):
            return
        if len(batch) > job_metadata_constants.MAXIMUM_NUMBER_OF_JOBS_FOR_RUN:
            raise BQJobsLimitExceededError(len(batch))
        if "cpu" in device and len(batch) > job_metadata_constants.QUEUED_CPU_JOBS_LIMIT:
            raise BQCPUJobsLimitExceededError(len(batch))

    @staticmethod
    def validate_circuit_type(circuits, device):
        # Early return for devices that don't require validation
        if not (
            device.startswith("pennylane")
            or device in {"mps.cpu", "mps.gpu", "pauli-path", "pauli-path.gpu"}
        ):
            return

        circuits_list = circuits if isinstance(circuits, list) else [circuits]
        for circuit in circuits_list:
            if device.startswith("pennylane"):
                if not is_a_pennylane_circuit(circuit):
                    raise BQSDKUsageError(f"Only Pennylane circuit is supported for {device}")
            elif not is_a_qiskit_circuit(circuit):
                raise BQSDKUsageError(f"Only Qiskit circuit is supported for {device}")

    @staticmethod
    def _validate_tags(tags):
        if tags is None:
            return
        if not isinstance(tags, dict):
            raise BQSDKUsageError("'tags' must be a dictionary with keys as strings")
        for k in tags:
            if not isinstance(k, str):
                raise BQSDKUsageError(
                    f"Each key of 'tags' must be a string; received key {k} of type {type(k)}"
                )
        try:
            tags_str = json.dumps(tags)
        except (TypeError, ValueError) as e:
            raise BQSDKUsageError(
                f"'tags' must be JSON serializable; received non-serializable data: {e}"
            ) from e
        tags_size = len(tags_str.encode())
        if tags_size > job_metadata_constants.MAX_JOB_TAGS_SIZE:
            raise BQSDKUsageError(
                f"'tags' must be of size less than 1 MB; received 'tags' of size: {tags_size}"
            )

    @staticmethod
    def _validate_options(options, device):
        if options is None:
            return
        for k in options:
            if k not in [
                "mps_bond_dimension",
                "pauli_path_truncation_threshold",
                "pauli_path_circuit_transpilation_level",
                "pauli_path_weight_cutoff",
            ]:
                raise BQSDKUsageError(f"options not supported: {k}")

        chi = options.get("mps_bond_dimension")
        if chi is not None and (not isinstance(chi, int) or chi < 1):
            raise BQSDKUsageError(
                f"'mps_bond_dimension' must be a positive integer; received {chi}"
            )
        if (
            device == "mps.cpu"
            and chi is not None
            and chi > job_metadata_constants.MAX_MPS_CPU_BOND_DIMENSION
        ):
            raise BQSDKUsageError(
                f"'mps_bond_dimension' must be smaller than {job_metadata_constants.MAX_MPS_CPU_BOND_DIMENSION} for {device}; received {chi}."
            )
        if (
            device == "mps.gpu"
            and chi is not None
            and chi > job_metadata_constants.MAX_MPS_GPU_BOND_DIMENSION
        ):
            raise BQSDKUsageError(
                f"'mps_bond_dimension' must be smaller than {job_metadata_constants.MAX_MPS_GPU_BOND_DIMENSION} for {device}; received {chi}."
            )

        delta = options.get("pauli_path_truncation_threshold")
        if delta is not None and (not isinstance(delta, (float, int)) or delta < 0.0):
            raise BQSDKUsageError(
                f"'pauli_path_truncation_threshold' must be a non-negative float; received {delta}"
            )
        if delta is not None and delta < job_metadata_constants.MIN_PAULI_PATH_TRUNCATION_THRESHOLD:
            raise BQSDKUsageError(
                "Truncation threshold too small: 'pauli_path_truncation_threshold' smaller than "
                f"{job_metadata_constants.MIN_PAULI_PATH_TRUNCATION_THRESHOLD}"
                " is currently not supported."
            )
        pps_transpilation_level = options.get("pauli_path_circuit_transpilation_level")
        if (
            pps_transpilation_level is not None
            and pps_transpilation_level
            not in job_metadata_constants.PAULI_PATH_CIRCUIT_TRANSPILATION_LEVELS
        ):
            raise BQSDKUsageError(
                f"'pauli_path_circuit_transpilation_level' must be from {job_metadata_constants.PAULI_PATH_CIRCUIT_TRANSPILATION_LEVELS}; received {pps_transpilation_level}"
            )

    @staticmethod
    def _validate_pps_job(options, circuits, pauli_sum):
        circuits_list = circuits if isinstance(circuits, list) else [circuits]
        # check that if any of the circuits are > 13 qubits, then a truncation threshold is provided
        if options is None or options.get("pauli_path_truncation_threshold") is None:
            for circuit in circuits_list:
                if circuit.num_qubits > 13:
                    raise BQSDKUsageError(
                        "For 'pauli-path' device, circuits with more than 13 qubits require "
                        "'pauli_path_truncation_threshold' to be specified in options."
                        f" Please specify a 'pauli_path_truncation_threshold' larger than {job_metadata_constants.MIN_PAULI_PATH_TRUNCATION_THRESHOLD}."
                    )
        if pauli_sum is None:
            raise BQSDKUsageError(
                "'pauli_sum' must be provided when using the 'pauli-path' device."
            )
        if isinstance(pauli_sum[0], list) and len(pauli_sum) > 1:
            raise BQSDKUsageError(
                "Only a single observable is supported on 'pauli-path' device. "
                f"Received 'pauli_sum' with {len(pauli_sum)} observables."
            )

    def estimate(
        self, circuits: CircuitT | list[CircuitT], device: str = "cpu"
    ) -> EstimateResult | list[EstimateResult]:
        """Estimate job runtime. Not supported in local execution mode.

        :param circuits: quantum circuit or circuits
        :type circuits: Cirq, Qiskit, list
        :param device: device for which to estimate the circuit. Can be one of
                       ``"cpu"`` | ``"gpu"`` | ``"quantum"``
        :return: result or results estimate metadata
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("BQClient.estimate() is not supported in local execution mode.")
        device = self.validate_device(device)
        self.validate_batch(circuits)
        response = jobs.submit_jobs(self._backend_connection, circuits, device, estimate_only=True)
        if isinstance(circuits, list):
            return [EstimateResult(data) for data in response]
        return EstimateResult(response)

    def run(
        self,
        circuits: CircuitT | list[CircuitT],
        device: str = "cpu",
        *,
        asynchronous: bool = False,
        job_name: str | None = None,
        shots: int | None = None,
        pauli_sum: PauliSumT | list[PauliSumT] | None = None,
        options: dict | None = None,
        tags: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> JobResult | list[JobResult]:
        """Submit a job to run on BlueQubit platform.

        :param circuits: quantum circuit or list of circuits
        :type circuits: Cirq, Qiskit, list
        :param device: device on which to run the circuit. Can be one of
                       ``"cpu"``
                       | ``"gpu"``
                       | ``"quantum"``
                       | ``"mps.cpu"``
                       | ``"mps.gpu"``
                       | ``"pauli-path"``
        :param asynchronous: if set to ``False``, wait for job completion before
                             returning. If set to ``True``, return immediately
        :param job_name: customizable job name
        :param shots: number of shots to run. If device is quantum and shots is None then
                      it is set to 1000. For non quantum devices, if None, full
                      probability distribution will be returned. For mps.cpu and mps.gpu devices it is limited to 1000000, for all other devices it is limited to 100000
        :param pauli_sum: The Pauli sum or a list of Pauli sum which
                          expectation value is the computation result
        :param options: dictionary of options used to configure the run:

                       - ``mps_bond_dimension`` (int): Sets a limit on the number of Schmidt
                         coefficients retained at the end of the svd algorithm.
                         Coefficients beyond this limit will be discarded.
                         Default: None (no limit on the bond dimension).
                         Applicable only to ``"mps.cpu"`` and ``"mps.gpu"`` devices.
                       - ``pauli_path_truncation_threshold`` (float): Sets a lower bound on the absolute value of
                         coefficients of the Pauli operators retained after each step of the Pauli-path propagation algorithm.
                         Pauli operators with coefficients less than this threshold will be discarded.
                         Choosing a smaller threshold keeps more Pauli terms in the simulation and provides
                         a better estimate of the expectation value, but at the cost of increased runtime.
                         Smallest value currently supported is 1e-5.
                         For circuits with more than 13 qubits a ``pauli_path_truncation_threshold`` must be specified.
                         For exact simulation of circuits with <= 13 qubits, set ``pauli_path_truncation_threshold`` to ``None``.
                         Applicable only to ``"pauli-path"`` device.
                       - ``pauli_path_circuit_transpilation_level`` (int): Controls the extend of transpilation performed
                         while converting the given circuit into one consisting of only rotation gates.
                         Must be one of 0, 1, 2 or 3, with 0 corresponding to minimal tranpilation, whereas level 3 involves
                         extensive, potentially time consuming, transpilation passes with different bases to minimize gate counts.
                         In general, different transpilation levels may result in slightly different expectation values.
                         Default: 2
                         Applicable only to ``"pauli-path"`` device

        :param tags: an optional dictionary containing key-value pairs to help tag the job.

        :param timeout: maximum wait time in seconds when ``asynchronous`` is ``False``.
                        If the job does not complete within the specified time,
                        an exception will be raised. If None, the wait will continue indefinitely.

        :return: job or jobs metadata
        """
        device = self.validate_device(device)
        self.validate_batch_for_run(circuits, device)
        self.validate_circuit_type(circuits, device)
        self._validate_options(options, device)
        self._validate_tags(tags)
        if timeout is not None:
            if self.execution_mode == "local":
                raise BQSDKUsageError(
                    "BQClient.run(timeout=...) is not supported in local execution mode."
                )
            if asynchronous is True:
                raise BQSDKUsageError(
                    "BQClient.run(asynchronous=True) does not support timeout parameter."
                )
        if device == "pauli-path":
            self._validate_pps_job(options, circuits, pauli_sum)

        if shots is not None and (
            not isinstance(shots, int)
            or shots > job_metadata_constants.MAXIMUM_NUMBER_OF_SHOTS[device]
        ):
            raise BQJobsMalformedShotsError(
                shots, device, job_metadata_constants.MAXIMUM_NUMBER_OF_SHOTS[device]
            )
        job_name = (
            job_name if self.job_name_prefix is None else self.job_name_prefix + str(job_name)
        )
        if self.execution_mode == "local" and device != "quantum":
            if asynchronous is True:
                raise BQSDKUsageError(
                    "BQClient.run(asynchronous=True) is not supported in local execution mode."
                )
            return run_circuits_local(
                circuits,
                device,
                job_name=job_name,
                shots=shots,
                pauli_sum=pauli_sum,
                options=options,
                tags=tags,
            )
        if job_name is not None:
            if not isinstance(circuits, list):
                if len(job_name) > job_metadata_constants.MAX_JOB_NAME_LENGTH:
                    logger.warning(
                        "Job name is too long, it will be truncated to %s characters.",
                        job_metadata_constants.MAX_JOB_NAME_LENGTH,
                    )
            else:  # batch
                zero_fill_count = len(str(len(circuits) - 1))
                if len(job_name) > job_metadata_constants.MAX_JOB_NAME_LENGTH - zero_fill_count:
                    logger.warning(
                        "Batch job name is too long, it will be truncated to %s characters.",
                        job_metadata_constants.MAX_JOB_NAME_LENGTH,
                    )
        response = jobs.submit_jobs(
            self._backend_connection,
            circuits,
            device,
            job_name,
            shots=shots,
            asynchronous=asynchronous,
            pauli_sum=pauli_sum,
            options=options,
            tags=tags,
        )
        if isinstance(circuits, list):
            logger.info("Submitted %s jobs. Batch ID %s", len(response), response[0]["batch_id"])

            def add_circuit_to_all(job_results, circuits):
                for job_result, circuit in zip(job_results, circuits, strict=True):
                    job_result.circuit = circuit

            job_results = [JobResult(data, self._backend_connection) for data in response]
            if not asynchronous:
                if self._check_all_in_terminal_states(job_results):
                    add_circuit_to_all(job_results, circuits)
                    return job_results

                waited_job_results = self.wait(job_results, timeout=timeout)
                add_circuit_to_all(waited_job_results, circuits)
                return waited_job_results
                # if job_results[0].batch_id is not None:
                #     return self.wait(batch_id=job_results[0].batch_id)
                # else:
            add_circuit_to_all(job_results, circuits)
            return job_results
        submitted_job = JobResult(response, self._backend_connection)
        if submitted_job.run_status in job_metadata_constants.JOB_NO_RESULT_TERMINAL_STATES:
            raise BQJobNotCompleteError(
                submitted_job.job_id,
                submitted_job.run_status,
                submitted_job.error_message,
            )
        logger.info("Submitted: %s", submitted_job)
        if (
            not asynchronous
            and submitted_job.run_status not in job_metadata_constants.JOB_TERMINAL_STATES
        ):
            jr = self.wait(submitted_job.job_id, timeout=timeout)
            jr.circuit = circuits  # type: ignore[union-attr]
            return jr
        submitted_job.circuit = circuits
        return submitted_job

    @staticmethod
    def _check_all_in_terminal_states(job_results):
        if not isinstance(job_results, list):
            if job_results.run_status in job_metadata_constants.JOB_NO_RESULT_TERMINAL_STATES:
                raise BQJobNotCompleteError(
                    job_results.job_id,
                    job_results.run_status,
                    job_results.error_message,
                )
            return job_results.run_status in job_metadata_constants.JOB_TERMINAL_STATES
        for job_result in job_results:
            if job_result.run_status in job_metadata_constants.JOB_NO_RESULT_TERMINAL_STATES:
                raise BQJobNotCompleteError(
                    job_result.job_id,
                    job_result.run_status,
                    job_result.error_message,
                )
        return all(
            job_result.run_status in job_metadata_constants.JOB_TERMINAL_STATES
            for job_result in job_results
        )

    def wait(
        self,
        job_ids: str | list[str] | JobResult | list[JobResult],
        timeout: float | None = None,
    ) -> JobResult | list[JobResult]:
        """Wait for job completion. Not supported in local execution mode.

        :param job_ids: job IDs that can be found as property of :class:`JobResult` metadata
                        of :func:`~run` method, or `JobResult` instances from which job IDs
                        will be extracted
        :param timeout: maximum wait time in seconds
                             If the job does not complete within the specified time,
                             an exception will be raised. If None, the wait will continue indefinitely. The raised error will have an error.job_ids attribute that can be used to identify the jobs that didn't complete within the specified time and be canceled.
        :return: job metadata
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("BQClient.wait() is not supported in local execution mode.")
        self.validate_batch(job_ids)
        job_results_previous = None
        start_time = time.time()
        while True:
            job_results = self._get(job_ids, need_qc_unprocessed=False)
            if self._check_all_in_terminal_states(job_results):
                return job_results
            if not isinstance(job_results, list):
                job_results = [job_results]
            if job_results_previous is not None:
                for job_result, job_result_previous in zip(
                    job_results, job_results_previous, strict=True
                ):
                    assert job_result.job_id == job_result_previous.job_id
                    if job_result.run_status != job_result_previous.run_status:
                        logger.info(
                            "Status changed: Job ID: %s. From %s to %s.",
                            job_result.job_id,
                            job_result_previous.run_status,
                            job_result.run_status,
                        )
            job_results_previous = job_results
            time.sleep(1.0)
            if timeout is not None and time.time() - start_time > timeout:
                error_job_ids = (
                    [jr.job_id for jr in job_results]
                    if isinstance(job_ids, list)
                    else job_results[0].job_id
                )
                err = TimeoutError(
                    f"Jobs {error_job_ids} didn't complete within the specified time. Maximum wait time: {timeout} seconds.",
                    timeout,
                )
                err.job_ids = error_job_ids  # type: ignore[attr-defined]
                raise err

    def get(
        self,
        job_ids: str | list[str] | JobResult | list[JobResult],
    ) -> JobResult | list[JobResult]:
        """Get current metadata of jobs. Not supported in local execution mode.

        :param job_ids: job IDs that can be found as property of :class:`JobResult` metadata
                        of :func:`~run` method
        :return: jobs metadata
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("BQClient.get() is not supported in local execution mode.")
        return self._get(job_ids)

    def _get(
        self,
        job_ids: str | list[str] | JobResult | list[JobResult],
        need_qc_unprocessed=True,
    ) -> JobResult | list[JobResult]:
        self.validate_batch(job_ids)
        job_ids_list = job_ids if isinstance(job_ids, list) else [job_ids]
        if isinstance(job_ids_list[0], JobResult):
            job_ids_list = [jr.job_id for jr in job_ids_list]  # type: ignore[union-attr]
        job_results = jobs.search_jobs(
            self._backend_connection,
            job_ids=job_ids_list,
            need_qc_unprocessed=need_qc_unprocessed,
        )
        job_results = [JobResult(r, self._backend_connection) for r in job_results["data"]]
        if isinstance(job_ids, list):
            return job_results
        return job_results[0]

    def cancel(
        self, job_ids: str | list[str] | JobResult | list[JobResult]
    ) -> JobResult | list[JobResult]:
        """Submit jobs cancel request. Not supported in local execution mode.

        :param job_ids: job IDs that can be found as property of :class:`JobResult` metadata
                        of :func:`run` method
        :return: job or jobs metadata
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("BQClient.cancel() is not supported in local execution mode.")
        self.validate_batch(job_ids)
        if isinstance(job_ids, JobResult):
            job_ids = job_ids.job_id
        elif isinstance(job_ids, list) and isinstance(job_ids[0], JobResult):
            job_ids = [jr.job_id for jr in job_ids]  # type: ignore[union-attr]
        logger.info("Canceling jobs: %s", job_ids)
        responses = jobs.cancel_jobs(self._backend_connection, job_ids)
        if isinstance(job_ids, list):
            for response in responses:
                if response["ret"] == "FAILED":
                    logger.warning(response["error_message"])
        try:
            self.wait(job_ids, timeout=180.0)
        except BQJobNotCompleteError as e:
            if not e.run_status == "CANCELED":
                raise BQJobCouldNotCancelError(e.job_id, e.run_status, e.error_message) from None
        return self.get(job_ids)

    def search(
        self,
        run_status: str | None = None,
        created_later_than: str | datetime.datetime | None = None,
        batch_id: str | None = None,
    ) -> list[JobResult]:
        """Search jobs. Not supported in local execution mode.

        :param run_status: if not ``None``, run status of jobs to filter.
                           Can be one of ``"FAILED_VALIDATION"`` | ``"PENDING"`` |
                           ``"QUEUED"`` | ``"RUNNING"`` | ``"TERMINATED"`` | ``"CANCELED"`` |
                           ``"NOT_ENOUGH_FUNDS"`` | ``"COMPLETED"``

        :param created_later_than: if not ``None``, filter by latest job creation datetime.
                                   Please add timezone for clarity, otherwise UTC
                                   will be assumed

        :param batch_id: if not ``None``, filter by batch ID

        :return: metadata of jobs
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("BQClient.search() is not supported in local execution mode.")
        job_results = jobs.search_jobs(
            self._backend_connection, run_status, created_later_than, batch_id=batch_id
        )
        return [JobResult(r, self._backend_connection) for r in job_results["data"]]

    def get_peaked_circuit(self, difficulty: int, circuit_id: int | None = None):
        """Get a peaked circuit from the backend.

        :param difficulty: difficulty of the circuit to get
        :param circuit_id: ID of the circuit to get. If ``None``, a random
                           circuit of the given difficulty will be returned.
        :return: PeakedCircuit
        :raises BQSDKUsageError: if circuit_id is not a non-negative integer
        """
        from .peaked_circuit import PeakedCircuit

        if circuit_id is not None and (not isinstance(circuit_id, int) or circuit_id < 0):
            raise BQSDKUsageError("circuit_id must be a non-negative integer")
        if difficulty is None or not isinstance(difficulty, int) or difficulty <= 0:
            raise BQSDKUsageError("difficulty must be a positive integer")
        data = circuits.get_peaked_circuit(self._backend_connection, difficulty, circuit_id)
        return PeakedCircuit(data)

    def _set_api_min_request_interval(self, min_request_interval: float) -> None:
        """Set the minimum request interval for the API. If consecutive requests are made
        within this interval, the SDK will automatically wait until the interval has passed
        before making the next request.

        :param min_request_interval: minimum request interval in seconds
        :return: None
        """
        if min_request_interval < 0.0:
            raise ValueError("Minimum request interval must be non-negative")
        self._backend_connection.min_request_interval = min_request_interval

    def _get_api_min_request_interval(self) -> float:
        """Get the minimum request interval for the API. See :func:`set_api_min_request_interval` for more details.

        :return: minimum request interval in seconds
        """
        return self._backend_connection.min_request_interval

    async def run_native_async(
        self, *args, polling_interval: float = 1.0, **kwargs
    ) -> JobResult | list[JobResult]:
        """Experimental: Submit a job to run on BlueQubit platform with asyncio.
        Not supported in local execution mode.

        :param args: arguments for the :func:`run` method
        :param polling_interval: interval in seconds to poll for job completion
        :type polling_interval: float
        :param kwargs: keyword arguments for the :func:`run` method

        :return: job or jobs metadata
        :rtype: JobResult or list[JobResult]
        """
        if self.execution_mode == "local":
            raise BQSDKUsageError("asyncio is not supported in local execution mode.")
        if kwargs.get("asynchronous") is False:
            raise BQSDKUsageError("asyncio is not supported in not asynchronous mode.")
        job_results = self.run(*args, asynchronous=True, **kwargs)
        try:
            while True:
                job_results = self._get(job_results, need_qc_unprocessed=False)

                if self._check_all_in_terminal_states(job_results):
                    return job_results
                await asyncio.sleep(polling_interval)
        except asyncio.CancelledError:
            job_ids = (
                [jr.job_id for jr in job_results]
                if isinstance(job_results, list)
                else [job_results.job_id]
            )
            logger.info("Cancelling jobs: %s", job_ids)
            jobs.cancel_jobs(self._backend_connection, job_ids)
            raise
