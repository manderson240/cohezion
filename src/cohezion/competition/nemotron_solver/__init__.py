"""Nemotron solver — symbolic reasoning pipeline for Kaggle Nemotron competition."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.competition.nemotron_solver.solve import solve as solve
    from cohezion.competition.nemotron_solver.solve import classify_problem as classify_problem
    from cohezion.competition.nemotron_solver.solve import parse_examples as parse_examples

with contextlib.suppress(Exception):
    from cohezion.competition.nemotron_solver.train_lora_kaggle import (
        compare_answers as compare_answers,
    )
