"""
Template Evolver for Cohezion.
Automates the refinement of structural blueprints (templates) based on task retrospectives.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateEvolver:
    """
    Refines templates in /templates/ by injecting missing patterns or best practices.
    """

    def __init__(self, templates_dir: str = "/home/mike-anderson/dev/cohezion/templates/"):
        self.templates_dir = Path(templates_dir)
        self.evolution_log_path = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/TEMPLATE_EVOLUTION.md"
        )

    def __init__(
        self, templates_dir: str = "/home/mike-anderson/dev/cohezion/templates/"
    ):
        self.templates_dir = Path(templates_dir)
        self.evolution_log_path = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/TEMPLATE_EVOLUTION.md"
        )

    def analyze_retrospective(
        self, retro_content: str, template_name: str = "skill.md"
    ) -> bool:
        """
        Scans a retrospective for "Missing Template Section" or "New Best Practice" and patches the template.
        """
        # Simple heuristic: Look for sections prefixed with [TEMPLATE IMPROVEMENT]
        improvements = re.findall(r"\[TEMPLATE IMPROVEMENT\]\s*(.*?)(?=\n\n|\n\[|$)", retro_content, re.DOTALL)

        if not improvements:
            logger.info("No template improvements found in retrospective.")
            return False

        template_file = self.templates_dir / template_name
        if not template_file.exists():
            logger.error(f"Template {template_name} not found.")
            return False

        success = False
        for improvement in improvements:
            if self._patch_template(template_file, improvement):
                success = True

        return success

    def _patch_template(self, template_path: Path, improvement: str) -> bool:
        """
        Non-destructively patches the template with the provided improvement.
        """
        content = template_path.read_text()

        # Avoid duplicate patching
        if improvement[:50] in content:
            logger.info(
                f"Improvement already present in {template_path.name}. Skipping."
            )
            return False

        # Strategy: Append to the end of the ## INSTRUCTION section or before ## VERSION
        if "## VERSION" in content:
            new_content = content.replace("## VERSION", f"{improvement}\n\n## VERSION")
        else:
            new_content = content + f"\n\n{improvement}"

        # Bump version in metadata
        current_version_match = re.search(r"v(\d+\.\d+)", new_content)
        if current_version_match:
            current_version = float(current_version_match.group(1))
            new_version = round(current_version + 0.1, 1)
            new_content = new_content.replace(f"v{current_version}", f"v{new_version}")

        template_path.write_text(new_content)
        self._log_evolution(template_path.name, improvement)
        logger.info(
            f"Patched template {template_path.name} to version v{new_version if 'new_version' in locals() else 'latest'}"
        )
        return True

    def _log_evolution(self, template_name: str, improvement: str):
        """Logs the evolution event to the knowledge graph."""
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"### {timestamp} - {template_name}\n- **Improvement**: {improvement}\n\n"

        if not self.evolution_log_path.exists():
            self.evolution_log_path.write_text("# Template Evolution Log\n\n" + entry)
        else:
            with open(self.evolution_log_path, "a") as f:
                f.write(entry)


if __name__ == "__main__":
    # Example usage / test
    evolver = TemplateEvolver()
    sample_retro = """
    ## Retrospective
    [TEMPLATE IMPROVEMENT]
    ### Automated Guardrails
    Ensure that all new skills include a section on `SANDBOX_ISOLATION_PRIME` compatibility.
    """
    evolver.analyze_retrospective(sample_retro)
