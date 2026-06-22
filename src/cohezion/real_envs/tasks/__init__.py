"""Real-world evaluation task scenarios."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.real_envs.tasks.scenarios import create_flask_api_task as create_flask_api_task

with contextlib.suppress(Exception):
    from cohezion.real_envs.tasks.scenarios import data_pipeline_task as data_pipeline_task

with contextlib.suppress(Exception):
    from cohezion.real_envs.tasks.scenarios import etl_api_to_db_task as etl_api_to_db_task

with contextlib.suppress(Exception):
    from cohezion.real_envs.tasks.scenarios import (
        git_workflow_automation_task as git_workflow_automation_task,
    )
