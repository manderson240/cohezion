# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Task scenario registry for real environment evaluations."""

from __future__ import annotations

from cohezion.real_envs.evaluator import (
    CommandSucceededCriterion,
    EvaluatedTask,
    FileContentCriterion,
    FileExistsCriterion,
)


# Task registry for all real environment scenarios
# Maps task_id -> factory function that creates EvaluatedTask
TASK_REGISTRY: dict = {}


def create_flask_api_task() -> EvaluatedTask:
    """Create Flask API with database integration."""
    return EvaluatedTask(
        task_id="flask_api_with_db",
        task_name="Flask API with Database",
        description="Create a Flask REST API with SQLAlchemy database models, authentication, and CRUD endpoints.",
        environment_type="shell",
        expected_steps=20,
        max_steps=40,
        criteria=[
            FileExistsCriterion("app.py"),
            FileExistsCriterion("models.py"),
            FileExistsCriterion("requirements.txt"),
            FileContentCriterion("app.py", expected_pattern=r"from flask import Flask"),
            FileContentCriterion("models.py", expected_pattern=r"from sqlalchemy"),
            FileContentCriterion("requirements.txt", expected_pattern=r"Flask"),
            FileContentCriterion("requirements.txt", expected_pattern=r"SQLAlchemy"),
            CommandSucceededCriterion(command_pattern="python -c 'from app import app; print(app)'"),
        ],
        metadata={
            "category": "web_development",
            "difficulty": "intermediate",
            "technologies": ["Flask", "SQLAlchemy", "Python"],
        },
    )


def data_pipeline_task() -> EvaluatedTask:
    """Create data processing pipeline."""
    return EvaluatedTask(
        task_id="data_processing_pipeline",
        task_name="Data Processing Pipeline",
        description="Create a Python data processing pipeline with pandas for ETL operations.",
        environment_type="shell",
        expected_steps=15,
        max_steps=30,
        criteria=[
            FileExistsCriterion("pipeline.py"),
            FileExistsCriterion("data/input.csv"),
            FileContentCriterion("pipeline.py", expected_pattern=r"import pandas as pd"),
            FileContentCriterion("pipeline.py", expected_pattern=r"def extract|def transform|def load"),
            FileExistsCriterion("output"),
        ],
        metadata={
            "category": "data_engineering",
            "difficulty": "easy",
            "technologies": ["Pandas", "Python", "ETL"],
        },
    )


def etl_api_to_db_task() -> EvaluatedTask:
    """Create ETL from API to SQLite."""
    return EvaluatedTask(
        task_id="etl_api_to_sqlite",
        task_name="ETL API to SQLite",
        description="Create an ETL pipeline that fetches data from an API and stores it in SQLite database.",
        environment_type="shell",
        expected_steps=18,
        max_steps=35,
        criteria=[
            FileExistsCriterion("etl.py"),
            FileExistsCriterion("database.db"),
            FileContentCriterion("etl.py", expected_pattern=r"import requests"),
            FileContentCriterion("etl.py", expected_pattern=r"import sqlite3"),
            FileContentCriterion("etl.py", expected_pattern=r"def fetch_data|def insert_data"),
        ],
        metadata={
            "category": "data_engineering",
            "difficulty": "intermediate",
            "technologies": ["Requests", "SQLite", "Python"],
        },
    )


def git_workflow_automation_task() -> EvaluatedTask:
    """Set up Git workflow automation."""
    return EvaluatedTask(
        task_id="git_workflow_automation",
        task_name="Git Workflow Automation",
        description="Create Git hooks and scripts for automated testing, linting, and commit validation.",
        environment_type="shell",
        expected_steps=12,
        max_steps=25,
        criteria=[
            FileExistsCriterion(".git/hooks/pre-commit"),
            FileExistsCriterion(".git/hooks/pre-push"),
            FileContentCriterion(".git/hooks/pre-commit", expected_pattern=r"#!/bin/bash|#!/bin/sh"),
            FileContentCriterion(".git/hooks/pre-commit", expected_pattern=r"pytest|black|flake8"),
        ],
        metadata={
            "category": "testing",
            "difficulty": "intermediate",
            "technologies": ["Git", "Bash", "Automation"],
        },
    )


# Register base tasks
TASK_REGISTRY.update(
    {
        "flask_api_with_db": create_flask_api_task,
        "data_processing_pipeline": data_pipeline_task,
        "etl_api_to_sqlite": etl_api_to_db_task,
        "git_workflow_automation": git_workflow_automation_task,
    }
)


__all__ = [
    "TASK_REGISTRY",
    "create_flask_api_task",
    "data_pipeline_task",
    "etl_api_to_db_task",
    "git_workflow_automation_task",
]
