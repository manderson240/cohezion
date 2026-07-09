import contextlib


with contextlib.suppress(Exception):
    from cohezion.pipelines.traceability import TraceabilityLink as TraceabilityLink

with contextlib.suppress(Exception):
    from cohezion.pipelines.traceability import TraceabilityPipeline as TraceabilityPipeline
