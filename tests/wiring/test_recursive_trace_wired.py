"""Discriminating identity test: recursive_trace exports reachable via package surface."""

from cohezion.recursive_trace import RecursiveTraceLoop as pkg_loop
from cohezion.recursive_trace import TraceTask as pkg_task
from cohezion.recursive_trace import TraceMemory as pkg_memory
from cohezion.recursive_trace import RecursiveTraceResult as pkg_result
from cohezion.recursive_trace.core import RecursiveTraceLoop as src_loop
from cohezion.recursive_trace.core import TraceTask as src_task
from cohezion.recursive_trace.core import TraceMemory as src_memory
from cohezion.recursive_trace.core import RecursiveTraceResult as src_result


def test_recursive_trace_loop_is_same():
    assert pkg_loop is src_loop


def test_trace_task_is_same():
    assert pkg_task is src_task


def test_trace_memory_is_same():
    assert pkg_memory is src_memory


def test_recursive_trace_result_is_same():
    assert pkg_result is src_result
