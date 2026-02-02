"""Meta-Programming Generator for Cohezion.

Enables creating 50 agents from 50 lines of YAML using Jinja2 templates.
Compound Engineering: Generator uses universe tracking and rewards.

Usage:
    python -m cohezion.meta.generator --spec=specs/research_agent.yaml --output=src/cohezion/agents/
    python -m cohezion.meta.generator --dir=specs/ --output=src/cohezion/agents/
    python -m cohezion.meta.generator --list
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import jinja2
import yaml

logger = logging.getLogger("meta_generator")


def _snake_case(value: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _to_json(value: Any) -> str:
    """Convert value to JSON string."""
    if value is None:
        return "None"
    if isinstance(value, str):
        return f'"{value}"'
    return json.dumps(value)


class MetaGenerator:
    """Meta-programming generator for Cohezion agents and workflows."""

    def __init__(self, template_dir: str | None = None):
        self.template_dir = (
            Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        )

        from cohezion.rewards.system import RewardSystem
        from cohezion.universe.engine import UniverseSimulationEngine

        self.engine = UniverseSimulationEngine()
        self.rewards = RewardSystem()

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        self.env.filters["tojson"] = _to_json
        self.env.filters["snake_case"] = _snake_case

    async def generate_agent(
        self,
        spec_path: str | Path,
        output_dir: str | Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate an agent from a YAML specification."""
        spec_path = Path(spec_path)
        output_dir = Path(output_dir)

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
            with open(spec_path) as f:
                spec = yaml.safe_load(f)

            report["agent_name"] = spec.get("class_name", spec_path.stem)
            logger.info(f"📄 Loading spec: {spec_path}")
            logger.info(f"   Agent: {report['agent_name']}")

            template = self.env.get_template("agent.py.j2")
            code = template.render(agent=spec)

            filename = spec.get("filename", spec_path.stem)
            output_path = output_dir / f"{filename}.py"

            if dry_run:
                logger.info(f"   [DRY RUN] Would generate: {output_path}")
                report["files_generated"].append(str(output_path))
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(code)
                logger.info(f"   ✅ Generated: {output_path}")
                report["files_generated"].append(str(output_path))

            await self.engine.precipitate_reality(
                journey=journey,
                outputs={"generated_file": str(output_path), "spec": spec},
                phi_score=0.95,
            )

            self.rewards.award_xp(
                agent_id="MetaGenerator",
                amount=50,
                reason=f"Generated agent: {report['agent_name']}",
            )

            report["success"] = True

        except Exception as e:
            logger.error(f"   ❌ Generation failed: {e}")
            report["errors"].append(str(e))

        return report

    async def generate_batch(
        self,
        spec_dir: str | Path,
        output_dir: str | Path,
        pattern: str = "*.yaml",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate multiple agents from YAML specs."""
        spec_dir = Path(spec_dir)
        specs = list(spec_dir.glob(pattern))

        if not specs:
            logger.warning("No specs found!")
            return {"success": False, "error": "No specs found"}

        reports = []
        for spec_path in sorted(specs):
            report = await self.generate_agent(spec_path, output_dir, dry_run)
            reports.append(report)

        success_count = sum(1 for r in reports if r["success"])

        logger.info(f"\n📋 BATCH GENERATION SUMMARY")
        logger.info(f"   Total: {len(reports)}, Success: {success_count}")

        return {
            "success": success_count == len(reports),
            "total": len(reports),
            "success_count": success_count,
            "reports": reports,
        }

    def list_specs(self, spec_dir: str | Path) -> list[dict[str, Any]]:
        """List available specifications."""
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
                    }
                )
            except Exception as e:
                logger.warning(f"Could not parse {spec_path}: {e}")

        return specs


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cohezion Meta-Programming Generator",
    )
    parser.add_argument("--spec", "-s", help="Generate from a single YAML spec")
    parser.add_argument("--dir", "-d", help="Directory containing YAML specs")
    parser.add_argument("--output", "-o", default="src/cohezion/agents/")
    parser.add_argument("--pattern", default="*.yaml")
    parser.add_argument("--list", "-l", action="store_true", help="List specs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    generator = MetaGenerator()

    if args.list:
        specs_dir = Path(__file__).parent / "specs"
        specs = generator.list_specs(specs_dir)
        logger.info("📋 AVAILABLE SPECIFICATIONS")
        for spec in specs:
            logger.info(f"  {spec['name']}: {spec['description'][:50]}...")
        return

    if args.spec:
        report = await generator.generate_agent(args.spec, args.output, args.dry_run)
        logger.info(
            f"\n✅ Generation complete!" if report["success"] else "\n❌ Failed!"
        )
    elif args.dir:
        report = await generator.generate_batch(
            args.dir, args.output, args.pattern, args.dry_run
        )
        logger.info(f"\n✅ Batch complete: {report['success_count']}/{report['total']}")


if __name__ == "__main__":
    asyncio.run(main())
