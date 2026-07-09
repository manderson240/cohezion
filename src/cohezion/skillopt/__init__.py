"""Cohezion SkillOpt integration — text-space skill optimizer using local silicon."""

from cohezion.skillopt.lemonade_backend import LemonadeBackend as LemonadeBackend
from cohezion.skillopt.runner import run_skillopt as run_skillopt
from cohezion.skillopt.surreal_trajectory_loader import (
    dump_corpus as dump_corpus,
)
from cohezion.skillopt.surreal_trajectory_loader import (
    list_skills_with_traces as list_skills_with_traces,
)
from cohezion.skillopt.surreal_trajectory_loader import (
    load_trajectories as load_trajectories,
)
from cohezion.skillopt.trace_augmentor import (
    SurrealTraceAugmentor as SurrealTraceAugmentor,
)
from cohezion.skillopt.trace_augmentor import (
    make_augmentor as make_augmentor,
)
from cohezion.skillopt.trace_writer import SurrealTraceWriter as SurrealTraceWriter
from cohezion.skillopt.trace_writer import make_trace_writer as make_trace_writer
