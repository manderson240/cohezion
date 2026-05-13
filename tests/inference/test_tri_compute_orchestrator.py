"""Minimal tests for tri_compute_orchestrator — ComputeTask and ExperimentPhase data classes."""

from __future__ import annotations

import time

from cohezion.inference.tri_compute_orchestrator import ComputeTask, NPUInferenceEngine


class TestComputeTask:
    def test_task_defaults(self):
        t = ComputeTask(task_id="t1", task_type="npu", payload="test prompt")
        assert t.priority == 0
        assert t.started_at is None
        assert t.completed_at is None
        assert t.result is None
        assert t.error is None

    def test_task_created_at_is_recent(self):
        before = time.time()
        t = ComputeTask(task_id="t2", task_type="igpu", payload={})
        after = time.time()
        assert before <= t.created_at <= after + 0.1

    def test_npu_task_type(self):
        t = ComputeTask(task_id="npu-1", task_type="npu", payload="classify this text")
        assert t.task_type == "npu"

    def test_igpu_task_type(self):
        t = ComputeTask(task_id="gpu-1", task_type="igpu", payload={"model": "flume"})
        assert t.task_type == "igpu"

    def test_cpu_task_type(self):
        t = ComputeTask(task_id="cpu-1", task_type="cpu", payload="aggregate results")
        assert t.task_type == "cpu"


class TestNPUInferenceEngine:
    def test_default_port_and_model(self):
        """NPU engine uses expected defaults."""
        e = NPUInferenceEngine()
        assert e.port == 8004
        assert "llama" in e.model.lower()

    def test_custom_port(self):
        """Can configure NPU engine to use our llama3.2-1b-FLM port."""
        e = NPUInferenceEngine(port=13306, model="llama3.2-1b-FLM")
        assert e.port == 13306
        assert e.model == "llama3.2-1b-FLM"
        assert "13306" in e.endpoint

    def test_latency_ms_reasonable_for_xdna2(self):
        """XDNA2 NPU should have low latency default (we measured 393ms TTFT)."""
        e = NPUInferenceEngine()
        assert e.latency_ms > 0
        assert e.latency_ms < 1000  # Should be well under 1s

    def test_throughput_tps_positive(self):
        """TPS must be positive (we measured 42 TPS for llama3.2-1b-FLM)."""
        e = NPUInferenceEngine()
        assert e.throughput_tps > 0
