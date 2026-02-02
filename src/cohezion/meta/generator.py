"""Meta-Programming Generator for Cohezion.

Enables creating 50 agents from 50 lines of YAML using Jinja2 templates.
Compound Engineering: Generator uses universe tracking and rewards.

Usage:
    # Generate an agent from a YAML spec
    uv run python -m cohezion.meta.generator --spec=specs/research_agent.yaml --output=src/cohezion/swarm/agents/

    # Generate multiple agents
    uv run python -m cohezion.meta.generator --dir=specs/ --output=src/cohezion/swarm/agents/

    # List available specs
    uv run python -m cohezion.meta.generator --list
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import jinja2
import yaml

from cohezion.rewards.system import RewardSystem
from cohezion.universe.engine import UniverseSimulationEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("meta_generator")


class MetaGenerator:
    """Meta-programming generator for Cohezion agents and workflows.

    Features:
    - Jinja2-based templating for flexibility
    - Universe tracking for generated code
    - XP rewards for successful generations
    - Batch processing for multiple specs
    """

    def __init__(self, template_dir: str | None = None):
        self.template_dir = (
            Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        )
        self.engine = UniverseSimulationEngine()
        self.rewards = RewardSystem()

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters
        self.env.filters["tojson"] = self._to_json_filter
        self.env.filters["snake_case"] = self._snake_case_filter

    def _to_json_filter(self, value: Any) -> str:
        """Convert value to JSON string."""
        if value is None:
            return "None"
        if isinstance(value, str):
            return f'"{value}"'
        return json.dumps(value)

    def _snake_case_filter(self, value: str) -> str:
        """Convert CamelCase to snake_case."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    async def generate_agent(
        self,
        spec_path: str | Path,
        output_dir: str | Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate an agent from a YAML specification.

        Args:
            spec_path: Path to YAML spec file
            output_dir: Directory to write generated code
            dry_run: If True, don't write files

        Returns:
            Generation report
        """
        spec_path = Path(spec_path)
        output_dir = Path(output_dir)

        # Start universe journey for this generation
        journey = await self.engine.start_journey(
            agent_name="MetaGenerator",
            intent=f"Generate agent from {spec_path.name}",
        )

        report = {
            "spec": str(spec_path),
            "output_dir": str(output_dir),
            "success": False,
            "errors": [],
            "files_generated": [],
        }

        try:
            # Load spec
            with open(spec_path) as f:
                spec = yaml.safe_load(f)

            report["agent_name"] = spec.get("class_name", spec_path.stem)

            logger.info(f"📄 Loading spec: {spec_path}")
            logger.info(f"   Agent: {report['agent_name']}")

            # Render template
            template = self.env.get_template("agent.py.j2")
            code = template.render(agent=spec)

            # Determine output path
            filename = spec.get("filename", spec_path.stem)
            output_path = output_dir / f"{filename}.py"

            if dry_run:
                logger.info(f"   [DRY RUN] Would generate: {output_path}")
                report["files_generated"].append(str(output_path))
            else:
                # Ensure output directory exists
                output_dir.mkdir(parents=True, exist_ok=True)

                # Write generated code
                with open(output_path, "w") as f:
                    f.write(code)

                logger.info(f"   ✅ Generated: {output_path}")
                report["files_generated"].append(str(output_path))

            # Complete journey
            await self.engine.precipitate_reality(
                journey=journey,
                outputs={"generated_file": str(output_path), "spec": spec},
                phi_score=0.95,
            )

            # Award XP for successful generation
            self.rewards.award_xp(
                agent_id="MetaGenerator",
                amount=50,
                reason=f"Generated agent: {report['agent_name']}",
                context={"spec": str(spec_path), "output": str(output_path)},
            )

            report["success"] = True

        except Exception as e:
            logger.error(f"   ❌ Generation failed: {e}")
            report["errors"].append(str(e))

            await self.engine.evolve_trajectory(
                journey=journey,
                action="generation_failed",
                result=str(e),
                phi_score=0.0,
            )

        return report

    async def generate_workflow(
        self,
        spec_path: str | Path,
        output_dir: str | Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate a workflow from a YAML specification.

        Args:
            spec_path: Path to YAML spec file
            output_dir: Directory to write generated workflow
            dry_run: If True, don't write files

        Returns:
            Generation report
        """
        spec_path = Path(spec_path)
        output_dir = Path(output_dir)

        report = {
            "spec": str(spec_path),
            "output_dir": str(output_dir),
            "success": False,
            "errors": [],
            "files_generated": [],
        }

        try:
            with open(spec_path) as f:
                spec = yaml.safe_load(f)

            report["workflow_name"] = spec.get("name", spec_path.stem)

            logger.info(f"📄 Loading workflow spec: {spec_path}")
            logger.info(f"   Workflow: {report['workflow_name']}")

            # Render template
            template = self.env.get_template("workflow.yaml.j2")
            yaml_output = template.render(workflow=spec)

            # Determine output path
            output_path = output_dir / f"{spec.get('name', spec_path.stem)}.yaml"

            if dry_run:
                logger.info(f"   [DRY RUN] Would generate: {output_path}")
                report["files_generated"].append(str(output_path))
            else:
                output_dir.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    f.write(yaml_output)

                logger.info(f"   ✅ Generated: {output_path}")
                report["files_generated"].append(str(output_path))

            report["success"] = True

        except Exception as e:
            logger.error(f"   ❌ Workflow generation failed: {e}")
            report["errors"].append(str(e))

        return report

    async def generate_batch(
        self,
        spec_dir: str | Path,
        output_dir: str | Path,
        pattern: str = "*.yaml",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate multiple agents from YAML specs in a directory.

        Args:
            spec_dir: Directory containing YAML specs
            output_dir: Directory to write generated code
            pattern: File pattern to match
            dry_run: If True, don't write files

        Returns:
            Batch generation report
        """
        spec_dir = Path(spec_dir)

        logger.info("=" * 60)
        logger.info("🚀 BATCH META-GENERATION")
        logger.info("=" * 60)
        logger.info(f"   Spec directory: {spec_dir}")
        logger.info(f"   Output directory: {output_dir}")
        logger.info(f"   Pattern: {pattern}")

        # Find all specs
        specs = list(spec_dir.glob(pattern))
        logger.info(f"   Found {len(specs)} specs")

        if not specs:
            logger.warning("No specs found!")
            return {"success": False, "error": "No specs found"}

        # Generate each spec
        reports = []
        for spec_path in sorted(specs):
            report = await self.generate_agent(spec_path, output_dir, dry_run)
            reports.append(report)

        # Summary
        success_count = sum(1 for r in reports if r["success"])
        error_count = len(reports) - success_count

        logger.info("\n" + "=" * 60)
        logger.info("📋 BATCH GENERATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Total specs: {len(reports)}")
        logger.info(f"   Success: {success_count}")
        logger.info(f"   Errors: {error_count}")

        if error_count > 0:
            for r in reports:
                if not r["success"]:
                    logger.error(f"   ❌ {r['spec']}: {r['errors']}")

        return {
            "success": error_count == 0,
            "total": len(reports),
            "success_count": success_count,
            "error_count": error_count,
            "reports": reports,
        }

    def list_specs(self, spec_dir: str | Path) -> list[dict[str, Any]]:
        """List available specifications in a directory.

        Args:
            spec_dir: Directory containing YAML specs

        Returns:
            List of spec metadata
        """
        spec_dir = Path(spec_dir)
        specs = []

        for spec_path in sorted(spec_dir.glob("*.yaml")):
            try:
                with open(spec_path) as f:
                    spec = yaml.safe_load(f)

                specs.append(
                    {
                        "path": str(spec_path),
                        "name": spec.get("class_name", spec_path.stem),
                        "description": spec.get("description", ""),
                        "filename": spec.get("filename", spec_path.stem),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not parse {spec_path}: {e}")

        return specs


async def main():
    """Main entry point for the meta-generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cohezion Meta-Programming Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--spec",
        "-s",
        help="Generate from a single YAML spec file",
    )
    parser.add_argument(
        "--dir",
        "-d",
        help="Directory containing YAML specs to generate from",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory for generated code",
        default="src/cohezion/swarm/agents/",
    )
    parser.add_argument(
        "--pattern",
        help="File pattern for specs (default: *.yaml)",
        default="*.yaml",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available specs in the specs directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    parser.add_argument(
        "--template-dir",
        help="Directory containing Jinja2 templates",
    )

    args = parser.parse_args()

    generator = MetaGenerator(template_dir=args.template_dir)

    # List specs
    if args.list:
        specs_dir = Path(__file__).parent / "specs"
        if not specs_dir.exists():
            logger.error(f"Specs directory not found: {specs_dir}")
            sys.exit(1)

        specs = generator.list_specs(specs_dir)

        logger.info("=" * 60)
        logger.info("📋 AVAILABLE SPECIFICATIONS")
        logger.info("=" * 60)

        for spec in specs:
            logger.info(f"\n  {spec['name']}")
            logger.info(f"     Path: {spec['path']}")
            logger.info(f"     Description: {spec['description'][:60]}...")

        return

    # Generate from single spec
    if args.spec:
        spec_path = Path(args.spec)
        if not spec_path.exists():
            logger.error(f"Spec file not found: {spec_path}")
            sys.exit(1)

        report = await generator.generate_agent(
            spec_path=spec_path,
            output_dir=args.output,
            dry_run=args.dry_run,
        )

        if report["success"]:
            logger.info("\n✅ Generation complete!")
            logger.info(f"   Files generated: {len(report['files_generated'])}")
        else:
            logger.error("\n❌ Generation failed!")
            for error in report["errors"]:
                logger.error(f"   {error}")
            sys.exit(1)

    # Generate from directory
    elif args.dir:
        spec_dir = Path(args.dir)
        if not spec_dir.exists():
            logger.error(f"Spec directory not found: {spec_dir}")
            sys.exit(1)

        report = await generator.generate_batch(
            spec_dir=spec_dir,
            output_dir=args.output,
            pattern=args.pattern,
            dry_run=args.dry_run,
        )

        if report["success"]:
            logger.info("\n✅ Batch generation complete!")
            logger.info(f"   Success: {report['success_count']}/{report['total']}")
        else:
            logger.error("\n❌ Some generations failed!")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
