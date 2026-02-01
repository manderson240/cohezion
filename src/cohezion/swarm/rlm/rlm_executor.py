import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RLMExecutor:
    """
    Recursive Language Model Executor.
    Provides a sandboxed-style Python REPL for LLMs to programmatically manage large contexts.
    """

    def __init__(self, workspace_dir: str | None = None):
        self.workspace_dir = Path(workspace_dir or "/tmp/cohezion_rlm")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.workspace_dir / "execution_history.jsonl"

    def execute_recursive_step(
        self, code: str, context_vars: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Executes a Python snippet in a sub-process and returns the modified context.
        """
        execution_id = str(uuid.uuid4())
        script_path = self.workspace_dir / f"step_{execution_id}.py"
        output_path = self.workspace_dir / f"output_{execution_id}.json"

        # Inject context variables as a JSON file read by the script
        context_path = self.workspace_dir / f"context_{execution_id}.json"
        with open(context_path, "w") as f:
            json.dump(context_vars, f)

        # Wrap the code with input/output handling
        wrapped_code = f"""
import json
import os

def run():
    with open('{context_path}', 'r') as f:
        ctx = json.load(f)

    # User Code Start
{self._indent_code(code)}
    # User Code End

    with open('{output_path}', 'w') as f:
        json.dump(ctx, f)

if __name__ == "__main__":
    run()
"""
        with open(script_path, "w") as f:
            f.write(wrapped_code)

        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            error = result.stderr if result.returncode != 0 else None

            updated_context = {}
            if os.path.exists(output_path):
                with open(output_path) as f:
                    updated_context = json.load(f)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": error,
                "updated_context": updated_context,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "Execution timed out (30s)"}
        except Exception as e:
            return {"success": False, "stderr": str(e)}
        finally:
            # Cleanup
            for p in [script_path, output_path, context_path]:
                if p.exists():
                    p.unlink()

    def _indent_code(self, code: str) -> str:
        return "\n".join([f"    {line}" for line in code.split("\n")])


def get_rlm_executor() -> RLMExecutor:
    return RLMExecutor()
