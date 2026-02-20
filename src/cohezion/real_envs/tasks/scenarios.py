"""Realistic long-horizon task scenarios for agent training.

Multi-step tasks that require coordination across environments:
- Shell + API for deployment tasks
- Browser + Shell for web development
- Multi-stage data processing pipelines
"""

from __future__ import annotations

from cohezion.real_envs.evaluator import (
    EvaluatedTask,
    FileExistsCriterion,
    FileContentCriterion,
    CommandSucceededCriterion,
    APIResponseCriterion,
)


# =============================================================================
# SOFTWARE DEVELOPMENT TASKS
# =============================================================================


def create_flask_api_task() -> EvaluatedTask:
    """Create a Flask REST API with database connection.

    Steps: ~15-20
    Environments: shell, api (for testing)
    """
    return EvaluatedTask(
        task_id="flask_api_with_db",
        description="Create a Flask REST API with SQLite database. The API should have endpoints for GET /users and POST /users.",
        environment_type="shell",
        expected_steps=15,
        max_steps=30,
        criteria=[
            FileExistsCriterion("app.py"),
            FileContentCriterion("app.py", expected_pattern=r"from flask import Flask"),
            FileContentCriterion(
                "app.py", expected_pattern=r"@app\.route\s*\(\s*['\"]/users['\"]"
            ),
            FileContentCriterion("app.py", expected_pattern=r"sqlite3|SQLAlchemy"),
            FileExistsCriterion("requirements.txt"),
            FileContentCriterion("requirements.txt", expected_pattern=r"Flask"),
            CommandSucceededCriterion(command_pattern="flask run"),
        ],
        metadata={
            "category": "web_development",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 30,
        },
    )


def create_python_package_task() -> EvaluatedTask:
    """Create a publishable Python package with tests and documentation.

    Steps: ~20-25
    Environments: shell
    """
    return EvaluatedTask(
        task_id="python_package_setup",
        description="Create a complete Python package 'mytool' with setup.py, tests, and README. Include a simple CLI entry point.",
        environment_type="shell",
        expected_steps=20,
        max_steps=40,
        criteria=[
            FileExistsCriterion("setup.py"),
            FileExistsCriterion("README.md"),
            FileExistsCriterion("mytool/__init__.py"),
            FileExistsCriterion("tests/test_mytool.py"),
            FileContentCriterion("setup.py", expected_pattern=r"entry_points"),
            FileContentCriterion("setup.py", expected_pattern=r"console_scripts"),
            FileContentCriterion("mytool/__init__.py", expected_pattern=r"__version__"),
            FileContentCriterion("tests/test_mytool.py", expected_pattern=r"def test_"),
            FileExistsCriterion("requirements.txt"),
        ],
        metadata={
            "category": "software_engineering",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 45,
        },
    )


def setup_docker_project_task() -> EvaluatedTask:
    """Set up a Docker containerized application.

    Steps: ~12-18
    Environments: shell
    """
    return EvaluatedTask(
        task_id="docker_containerization",
        description="Create a Dockerized Python web application with Dockerfile, docker-compose.yml, and nginx config.",
        environment_type="shell",
        expected_steps=15,
        max_steps=30,
        criteria=[
            FileExistsCriterion("Dockerfile"),
            FileExistsCriterion("docker-compose.yml"),
            FileExistsCriterion("nginx.conf"),
            FileContentCriterion("Dockerfile", expected_pattern=r"FROM python"),
            FileContentCriterion("Dockerfile", expected_pattern=r"CMD|ENTRYPOINT"),
            FileContentCriterion("docker-compose.yml", expected_pattern=r"services:"),
            FileContentCriterion("nginx.conf", expected_pattern=r"server"),
        ],
        metadata={
            "category": "devops",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 35,
        },
    )


# =============================================================================
# DATA PROCESSING TASKS
# =============================================================================


def data_pipeline_task() -> EvaluatedTask:
    """Build a data processing pipeline with validation.

    Steps: ~18-25
    Environments: shell
    """
    return EvaluatedTask(
        task_id="data_processing_pipeline",
        description="Create a Python data pipeline that reads CSV, validates data, transforms it, and outputs JSON. Include error handling and logging.",
        environment_type="shell",
        expected_steps=20,
        max_steps=40,
        criteria=[
            FileExistsCriterion("pipeline.py"),
            FileExistsCriterion("test_data.csv"),
            FileExistsCriterion("requirements.txt"),
            FileContentCriterion("pipeline.py", expected_pattern=r"import csv"),
            FileContentCriterion("pipeline.py", expected_pattern=r"import json"),
            FileContentCriterion(
                "pipeline.py", expected_pattern=r"def validate|def transform"
            ),
            FileContentCriterion("pipeline.py", expected_pattern=r"logging|logger"),
            FileContentCriterion("pipeline.py", expected_pattern=r"try:|except"),
            CommandSucceededCriterion(command_pattern="python pipeline.py"),
            FileExistsCriterion("output.json"),
        ],
        metadata={
            "category": "data_engineering",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 40,
        },
    )


def etl_api_to_db_task() -> EvaluatedTask:
    """Create ETL pipeline from API to database.

    Steps: ~15-22
    Environments: shell, api
    """
    return EvaluatedTask(
        task_id="etl_api_to_sqlite",
        description="Build an ETL pipeline that fetches data from a REST API and stores it in SQLite. Include retry logic and batch processing.",
        environment_type="shell",
        expected_steps=18,
        max_steps=35,
        criteria=[
            FileExistsCriterion("etl.py"),
            FileContentCriterion("etl.py", expected_pattern=r"import requests"),
            FileContentCriterion("etl.py", expected_pattern=r"sqlite3"),
            FileContentCriterion(
                "etl.py", expected_pattern=r"def extract|def transform|def load"
            ),
            FileContentCriterion("etl.py", expected_pattern=r"retry|backoff"),
            FileContentCriterion("etl.py", expected_pattern=r"try:|except"),
            FileExistsCriterion("database.db"),
            CommandSucceededCriterion(command_pattern="python etl.py"),
        ],
        metadata={
            "category": "data_engineering",
            "difficulty": "advanced",
            "estimated_duration_minutes": 50,
        },
    )


# =============================================================================
# API INTEGRATION TASKS
# =============================================================================


def github_api_task() -> EvaluatedTask:
    """Interact with GitHub API to manage repositories.

    Steps: ~10-15
    Environments: api
    """
    return EvaluatedTask(
        task_id="github_repo_management",
        description="Use the GitHub API to create a repository, add a file, and create an issue. Handle authentication and pagination.",
        environment_type="api",
        expected_steps=12,
        max_steps=25,
        criteria=[
            APIResponseCriterion(expected_status_code=201),  # Created repo
            APIResponseCriterion(expected_json_path="name"),
        ],
        metadata={
            "category": "api_integration",
            "difficulty": "intermediate",
            "requires_auth": True,
            "estimated_duration_minutes": 25,
        },
    )


def weather_api_dashboard_task() -> EvaluatedTask:
    """Build a weather dashboard using a public API.

    Steps: ~20-30
    Environments: shell, api, browser
    """
    return EvaluatedTask(
        task_id="weather_dashboard",
        description="Create a web dashboard that fetches weather data from OpenWeatherMap API and displays it. Include HTML, CSS, and JavaScript.",
        environment_type="multi",
        expected_steps=25,
        max_steps=50,
        criteria=[
            FileExistsCriterion("index.html"),
            FileExistsCriterion("style.css"),
            FileExistsCriterion("app.js"),
            FileContentCriterion("index.html", expected_pattern=r"weather|temperature"),
            FileContentCriterion("app.js", expected_pattern=r"fetch|XMLHttpRequest"),
            FileContentCriterion(
                "app.js", expected_pattern=r"api.openweathermap.org|weather"
            ),
            FileContentCriterion(
                "style.css", expected_pattern=r"\.container|\.weather"
            ),
        ],
        metadata={
            "category": "full_stack",
            "difficulty": "intermediate",
            "requires_api_key": True,
            "estimated_duration_minutes": 60,
        },
    )


# =============================================================================
# WEB SCRAPING TASKS
# =============================================================================


def scrape_and_analyze_task() -> EvaluatedTask:
    """Scrape website and analyze data.

    Steps: ~15-20
    Environments: shell, browser (for Scrapy or BeautifulSoup)
    """
    return EvaluatedTask(
        task_id="web_scraping_analysis",
        description="Scrape a website using requests and BeautifulSoup, extract data, and generate a summary report. Save results to CSV.",
        environment_type="shell",
        expected_steps=15,
        max_steps=30,
        criteria=[
            FileExistsCriterion("scraper.py"),
            FileExistsCriterion("requirements.txt"),
            FileContentCriterion("scraper.py", expected_pattern=r"import requests"),
            FileContentCriterion(
                "scraper.py", expected_pattern=r"from bs4 import BeautifulSoup"
            ),
            FileContentCriterion("scraper.py", expected_pattern=r"csv.writer|to_csv"),
            FileContentCriterion(
                "scraper.py", expected_pattern=r"def scrape|def parse"
            ),
            FileExistsCriterion("results.csv"),
            CommandSucceededCriterion(command_pattern="python scraper.py"),
        ],
        metadata={
            "category": "web_scraping",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 35,
        },
    )


# =============================================================================
# AUTOMATION TASKS
# =============================================================================


def git_workflow_automation_task() -> EvaluatedTask:
    """Automate git workflow with hooks and scripts.

    Steps: ~12-18
    Environments: shell
    """
    return EvaluatedTask(
        task_id="git_workflow_automation",
        description="Set up a Git repository with pre-commit hooks for linting, a GitHub Actions workflow for CI, and a release script.",
        environment_type="shell",
        expected_steps=15,
        max_steps=30,
        criteria=[
            FileExistsCriterion(".git/hooks/pre-commit"),
            FileExistsCriterion(".github/workflows/ci.yml"),
            FileExistsCriterion("scripts/release.sh"),
            FileContentCriterion(
                ".git/hooks/pre-commit", expected_pattern=r"ruff|black|flake8"
            ),
            FileContentCriterion(
                ".github/workflows/ci.yml",
                expected_pattern=r"on:.*push|on:.*pull_request",
            ),
            FileContentCriterion(
                ".github/workflows/ci.yml", expected_pattern=r"runs-on|steps:"
            ),
            FileContentCriterion(
                "scripts/release.sh", expected_pattern=r"#!/bin/bash|#!/bin/sh"
            ),
            CommandSucceededCriterion(command_pattern="git init"),
        ],
        metadata={
            "category": "automation",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 30,
        },
    )


def backup_automation_task() -> EvaluatedTask:
    """Create automated backup script with scheduling.

    Steps: ~10-15
    Environments: shell
    """
    return EvaluatedTask(
        task_id="backup_automation",
        description="Create a Python backup script that compresses directories, uploads to cloud storage, and sends notifications. Include a cron schedule.",
        environment_type="shell",
        expected_steps=12,
        max_steps=25,
        criteria=[
            FileExistsCriterion("backup.py"),
            FileExistsCriterion("crontab.txt"),
            FileContentCriterion(
                "backup.py", expected_pattern=r"import zipfile|import tarfile"
            ),
            FileContentCriterion("backup.py", expected_pattern=r"boto3|aws|gcp|azure"),
            FileContentCriterion(
                "backup.py", expected_pattern=r"smtplib|sendmail|notify"
            ),
            FileContentCriterion("backup.py", expected_pattern=r"logging|logger"),
            FileContentCriterion("crontab.txt", expected_pattern=r"\d+ \d+ \* \* \*"),
        ],
        metadata={
            "category": "automation",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 25,
        },
    )


# =============================================================================
# TASK REGISTRY
# =============================================================================

TASK_REGISTRY: dict[str, Callable[[], EvaluatedTask]] = {
    # Software development
    "flask_api_with_db": create_flask_api_task,
    "python_package_setup": create_python_package_task,
    "docker_containerization": setup_docker_project_task,
    # Data processing
    "data_processing_pipeline": data_pipeline_task,
    "etl_api_to_sqlite": etl_api_to_db_task,
    # API integration
    "github_repo_management": github_api_task,
    "weather_dashboard": weather_api_dashboard_task,
    # Web scraping
    "web_scraping_analysis": scrape_and_analyze_task,
    # Automation
    "git_workflow_automation": git_workflow_automation_task,
    "backup_automation": backup_automation_task,
}


def get_task(task_id: str) -> EvaluatedTask | None:
    """Get a task by ID."""
    factory = TASK_REGISTRY.get(task_id)
    if factory:
        return factory()
    return None


def list_tasks() -> list[dict[str, str]]:
    """List all available tasks with metadata."""
    tasks = []
    for task_id, factory in TASK_REGISTRY.items():
        task = factory()
        tasks.append(
            {
                "task_id": task_id,
                "description": task.description[:100] + "..."
                if len(task.description) > 100
                else task.description,
                "category": task.metadata.get("category", "unknown"),
                "difficulty": task.metadata.get("difficulty", "unknown"),
                "environment_type": task.environment_type,
                "expected_steps": str(task.expected_steps),
            }
        )
    return tasks


def get_tasks_by_category(category: str) -> list[EvaluatedTask]:
    """Get all tasks in a category."""
    tasks = []
    for task_id, factory in TASK_REGISTRY.items():
        task = factory()
        if task.metadata.get("category") == category:
            tasks.append(task)
    return tasks


def get_tasks_by_difficulty(difficulty: str) -> list[EvaluatedTask]:
    """Get all tasks with a specific difficulty level."""
    tasks = []
    for task_id, factory in TASK_REGISTRY.items():
        task = factory()
        if task.metadata.get("difficulty") == difficulty:
            tasks.append(task)
    return tasks
