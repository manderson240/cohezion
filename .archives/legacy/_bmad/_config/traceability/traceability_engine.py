#!/usr/bin/env python3
"""
BMAD Traceability Engine - Agent→Workflow→Task Mapping

Generates living traceability matrices for continuous compound engineering.
Supports:
- Agent → Workflow mapping
- Workflow → Task invocations
- Workflow → Workflow chains
- Party configurations per module
- Cycle detection
- Orphan detection

Refactored to use BaseEngine for DRY compliance and dependency injection.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET


try:
    from .base_engine import BaseEngine, EngineConfig
except ImportError:
    from base_engine import BaseEngine, EngineConfig


@dataclass
class Agent:
    """Agent definition from agent-manifest.csv."""

    name: str
    display_name: str
    title: str
    icon: str
    capabilities: str
    role: str
    identity: str
    module: str
    path: str


@dataclass
class Workflow:
    """Workflow definition from workflow-manifest.csv."""

    name: str
    description: str
    module: str
    path: str


@dataclass
class Task:
    """Task definition from task-manifest.csv."""

    name: str
    display_name: str
    description: str
    module: str
    path: str
    standalone: bool


@dataclass
class Invocation:
    """Workflow invocation (invoke-task, invoke-workflow, invoke-protocol)."""

    workflow_name: str
    target_name: str
    invocation_type: str  # invoke-task, invoke-workflow, invoke-protocol
    source_file: str
    line_ref: str


@dataclass
class WorkflowChain:
    """Workflow → Workflow dependency."""

    parent_workflow: str
    child_workflow: str
    trigger_condition: str
    source_file: str


@dataclass
class PartyConfig:
    """Party configuration per module."""

    module: str
    party_csv: str
    agent_count: int
    agents_included: List[str]


@dataclass
class TraceabilityMatrix:
    """Complete traceability matrix."""

    agent_workflow: List[Dict] = field(default_factory=list)
    workflow_task: List[Dict] = field(default_factory=list)
    workflow_chain: List[Dict] = field(default_factory=list)
    party_module: List[Dict] = field(default_factory=list)


class TraceabilityEngine(BaseEngine):
    """Main traceability extraction engine."""

    def __init__(self, project_root: Optional[Path] = None, config: Optional[EngineConfig] = None):
        # Support both old API and new DI pattern
        if config:
            super().__init__(config)
        else:
            project_root = project_root or Path("/home/mike-anderson/dev/cohezion")
            config = EngineConfig(
                project_root=project_root,
                output_dir=project_root / "_bmad" / "_config" / "traceability",
            )
            super().__init__(config)

        self.bmad_root = self.project_root / "_bmad"
        self.config_dir = self.bmad_root / "_config"

        # Storage
        self.agents: List[Agent] = []
        self.workflows: List[Workflow] = []
        self.tasks: List[Task] = []
        self.invocations: List[Invocation] = []
        self.chains: List[WorkflowChain] = []
        self.party_configs: List[PartyConfig] = []

        self.logger.info("TraceabilityEngine initialized")

        # Storage
        self.agents: List[Agent] = []
        self.workflows: List[Workflow] = []
        self.tasks: List[Task] = []
        self.invocations: List[Invocation] = []
        self.chains: List[WorkflowChain] = []
        self.party_configs: List[PartyConfig] = []

    def load_agent_manifest(self) -> List[Agent]:
        """Parse agent-manifest.csv."""
        manifest_path = self.config_dir / "agent-manifest.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Agent manifest not found: {manifest_path}")

        agents = []
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                agent = Agent(
                    name=row["name"].strip('"'),
                    display_name=row["displayName"].strip('"'),
                    title=row["title"].strip('"'),
                    icon=row["icon"].strip('"'),
                    capabilities=row["capabilities"].strip('"'),
                    role=row["role"].strip('"'),
                    identity=row["identity"].strip('"'),
                    module=row["module"].strip('"'),
                    path=row["path"].strip('"'),
                )
                agents.append(agent)

        self.agents = agents
        return agents

    def load_workflow_manifest(self) -> List[Workflow]:
        """Parse workflow-manifest.csv."""
        manifest_path = self.config_dir / "workflow-manifest.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Workflow manifest not found: {manifest_path}")

        workflows = []
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                workflow = Workflow(
                    name=row["name"].strip('"'),
                    description=row["description"].strip('"'),
                    module=row["module"].strip('"'),
                    path=row["path"].strip('"'),
                )
                workflows.append(workflow)

        self.workflows = workflows
        return workflows

    def load_task_manifest(self) -> List[Task]:
        """Parse task-manifest.csv."""
        manifest_path = self.config_dir / "task-manifest.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Task manifest not found: {manifest_path}")

        tasks = []
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task = Task(
                    name=row["name"].strip('"'),
                    display_name=row["displayName"].strip('"'),
                    description=row["description"].strip('"'),
                    module=row["module"].strip('"'),
                    path=row["path"].strip('"'),
                    standalone=row.get("standalone", "false").strip('"').lower() == "true",
                )
                tasks.append(task)

        self.tasks = tasks
        return tasks

    def find_workflow_xml_files(self) -> List[Path]:
        """Find all workflow XML files (instructions.xml, workflow.xml, workflow.yaml)."""
        xml_files = []
        for pattern in ["**/instructions.xml", "**/workflow.xml", "**/workflow.yaml"]:
            xml_files.extend(self.discover_python_files(self.bmad_root, pattern))
        return xml_files

    def extract_invocations_from_xml(self, xml_path: Path) -> List[Invocation]:
        """Extract invoke-* tags from workflow XML."""
        invocations = []

        content = self.read_file_safe(xml_path)
        if not content:
            self.logger.warning(f"Could not read {xml_path}")
            return invocations

        try:
            # Extract invoke-task tags with regex for better text handling
            task_pattern = r"<invoke-task>([^<]+)</invoke-task>"
            workflow_pattern = r"<invoke-workflow>([^<]+)</invoke-workflow>"
            protocol_pattern = r"<invoke-protocol\s+name=\"([^\"]+)\""

            workflow_name = self._path_to_workflow_name(xml_path)
            source_file = self.get_relative_path(xml_path, self.bmad_root)

            # Extract invoke-task
            for match in re.finditer(task_pattern, content):
                task_name = match.group(1).strip()
                # Extract just the task name from verbose text
                if "validate-workflow.xml" in task_name:
                    task_name = "validate-workflow"
                elif ".xml" in task_name:
                    task_name = task_name.split("/")[-1].replace(".xml", "")
                elif " " in task_name:
                    task_name = task_name.split()[-1]

                line_num = content[: match.start()].count("\n") + 1
                invocation = Invocation(
                    workflow_name=workflow_name,
                    target_name=task_name,
                    invocation_type="invoke-task",
                    source_file=source_file,
                    line_ref=f"Line {line_num}",
                )
                invocations.append(invocation)

            # Extract invoke-workflow
            for match in re.finditer(workflow_pattern, content):
                wf_name = match.group(1).strip()
                line_num = content[: match.start()].count("\n") + 1
                invocation = Invocation(
                    workflow_name=workflow_name,
                    target_name=wf_name,
                    invocation_type="invoke-workflow",
                    source_file=source_file,
                    line_ref=f"Line {line_num}",
                )
                invocations.append(invocation)

            # Extract invoke-protocol
            for match in re.finditer(protocol_pattern, content):
                protocol_name = match.group(1).strip()
                line_num = content[: match.start()].count("\n") + 1
                invocation = Invocation(
                    workflow_name=workflow_name,
                    target_name=protocol_name,
                    invocation_type="invoke-protocol",
                    source_file=source_file,
                    line_ref=f"Line {line_num}",
                )
                invocations.append(invocation)

        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {xml_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {xml_path}: {e}")
            self.logger.debug(__import__("traceback").format_exc())

        return invocations

    def extract_workflow_references_from_yaml(self, yaml_path: Path) -> List[Invocation]:
        """Extract workflow references from workflow.yaml files."""
        invocations = []

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for workflow references in description or other fields
            # Pattern: workflow names mentioned in the YAML
            workflow_name = self._path_to_workflow_name(yaml_path)
            source_file = str(yaml_path.relative_to(self.bmad_root))

            # Check for references to other workflows in the description
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                # Look for workflow mentions (e.g., "Run sprint-planning workflow first")
                if "workflow" in line.lower() and "`" in line:
                    # Extract workflow names in backticks
                    matches = re.findall(r"`([^`]+)`", line)
                    for match in matches:
                        if "-" in match and len(match.split("-")) >= 2:
                            # Likely a workflow name
                            invocation = Invocation(
                                workflow_name=workflow_name,
                                target_name=match,
                                invocation_type="invoke-workflow",
                                source_file=source_file,
                                line_ref=f"Line {line_num}",
                            )
                            invocations.append(invocation)

        except Exception as e:
            print(f"Error parsing YAML {yaml_path}: {e}")

        return invocations

    def _path_to_workflow_name(self, xml_path: Path) -> str:
        """Convert file path to workflow name."""
        # Extract workflow name from path
        # e.g., _bmad/bmm/workflows/4-implementation/code-review/instructions.xml → code-review
        parts = xml_path.relative_to(self.bmad_root).parts
        if "workflows" in parts:
            workflow_idx = parts.index("workflows")
            if workflow_idx + 1 < len(parts):
                return parts[workflow_idx + 1]
        return xml_path.stem

    def find_party_csv_files(self) -> List[Path]:
        """Find all default-party.csv files."""
        return list(self.bmad_root.glob("**/default-party.csv"))

    def extract_party_configs(self) -> List[PartyConfig]:
        """Parse all default-party.csv files."""
        party_files = self.find_party_csv_files()
        configs = []

        for party_path in party_files:
            # Extract module from path
            parts = party_path.relative_to(self.bmad_root).parts
            module = parts[0] if parts else "unknown"

            agents = []
            with open(party_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    agents.append(row["name"].strip('"'))

            config = PartyConfig(
                module=module,
                party_csv=str(party_path.relative_to(self.bmad_root)),
                agent_count=len(agents),
                agents_included=agents,
            )
            configs.append(config)

        self.party_configs = configs
        return configs

    def build_agent_workflow_matrix(self) -> List[Dict]:
        """Build Agent → Workflow mapping matrix."""
        matrix = []

        # Strategy: Match agents to workflows by module
        # Future enhancement: Analyze workflow instructions.xml for explicit agent references

        agent_module_map = {agent.name: agent.module for agent in self.agents}

        for workflow in self.workflows:
            # Find agents in same module
            module_agents = [agent for agent in self.agents if agent.module == workflow.module]

            for agent in module_agents:
                row = {
                    "agent_name": agent.name,
                    "workflow_name": workflow.name,
                    "invocation_pattern": "module_match",
                    "confidence": "medium",
                    "source_file": "workflow-manifest.csv",
                }
                matrix.append(row)

        self.matrix_agent_workflow = matrix
        return matrix

    def build_workflow_task_matrix(self) -> List[Dict]:
        """Build Workflow → Task mapping matrix."""
        matrix = []

        for invocation in self.invocations:
            if invocation.invocation_type == "invoke-task":
                row = {
                    "workflow_name": invocation.workflow_name,
                    "task_invoked": invocation.target_name,
                    "invocation_type": invocation.invocation_type,
                    "source_file": invocation.source_file,
                    "line_ref": invocation.line_ref,
                }
                matrix.append(row)

        self.matrix_workflow_task = matrix
        return matrix

    def build_workflow_chain_matrix(self) -> List[Dict]:
        """Build Workflow → Workflow chain matrix."""
        matrix = []

        for invocation in self.invocations:
            if invocation.invocation_type == "invoke-workflow":
                row = {
                    "parent_workflow": invocation.workflow_name,
                    "child_workflow": invocation.target_name,
                    "trigger_condition": "explicit_invoke",
                    "source_file": invocation.source_file,
                    "line_ref": invocation.line_ref,
                }
                matrix.append(row)

        self.matrix_workflow_chain = matrix
        return matrix

    def build_party_module_matrix(self) -> List[Dict]:
        """Build Party → Module mapping matrix."""
        matrix = []

        for config in self.party_configs:
            row = {
                "module": config.module,
                "party_csv": config.party_csv,
                "agent_count": config.agent_count,
                "agents_included": ";".join(config.agents_included),
            }
            matrix.append(row)

        self.matrix_party_module = matrix
        return matrix

    def detect_cycles(self) -> List[Tuple[str, str]]:
        """Detect circular workflow dependencies."""
        cycles = []

        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for chain in self.chains:
            if chain.parent_workflow not in graph:
                graph[chain.parent_workflow] = []
            graph[chain.parent_workflow].append(chain.child_workflow)

        # DFS cycle detection
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> Optional[Tuple[str, str]]:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Cycle detected
                    return (node, neighbor)

            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = dfs(node, [node])
                if cycle:
                    cycles.append(cycle)

        return cycles

    def detect_orphan_agents(self) -> List[str]:
        """Find agents with no workflow assignments."""
        assigned_agents = {row["agent_name"] for row in self.matrix_agent_workflow}
        all_agents = {agent.name for agent in self.agents}
        orphans = all_agents - assigned_agents
        return list(orphans)

    def detect_orphan_workflows(self) -> List[str]:
        """Find workflows with no agent assignments."""
        assigned_workflows = {row["workflow_name"] for row in self.matrix_agent_workflow}
        all_workflows = {workflow.name for workflow in self.workflows}
        orphans = all_workflows - assigned_workflows
        return list(orphans)

    def run_full_extraction(self, self_trace: bool = False) -> TraceabilityMatrix:
        """Execute full extraction pipeline."""
        print("Loading manifests...")
        self.load_agent_manifest()
        self.load_workflow_manifest()
        self.load_task_manifest()

        print(f"Loaded {len(self.agents)} agents")
        print(f"Loaded {len(self.workflows)} workflows")
        print(f"Loaded {len(self.tasks)} tasks")

        print("Extracting invocations from XML...")
        xml_files = self.find_workflow_xml_files()
        print(f"Found {len(xml_files)} workflow XML files")

        for xml_path in xml_files:
            # Skip self-trace directory unless self_trace mode enabled
            if not self_trace and "traceability" in str(xml_path):
                continue

            invocations = self.extract_invocations_from_xml(xml_path)
            self.invocations.extend(invocations)

            # Also extract from YAML files
            if xml_path.suffix == ".yaml":
                yaml_invocations = self.extract_workflow_references_from_yaml(xml_path)
                self.invocations.extend(yaml_invocations)

        print(f"Extracted {len(self.invocations)} invocations")

        print("Extracting party configurations...")
        self.extract_party_configs()
        print(f"Found {len(self.party_configs)} party configs")

        print("Building matrices...")
        matrix = TraceabilityMatrix(
            agent_workflow=self.build_agent_workflow_matrix(),
            workflow_task=self.build_workflow_task_matrix(),
            workflow_chain=self.build_workflow_chain_matrix(),
            party_module=self.build_party_module_matrix(),
        )

        print("Cycle detection...")
        cycles = self.detect_cycles()
        if cycles:
            print(f"⚠️  Detected {len(cycles)} workflow cycles: {cycles}")
        else:
            print("✓ No workflow cycles detected")

        print("Orphan detection...")
        orphan_agents = self.detect_orphan_agents()
        orphan_workflows = self.detect_orphan_workflows()
        if orphan_agents:
            print(f"⚠️  {len(orphan_agents)} orphan agents: {orphan_agents}")
        if orphan_workflows:
            print(f"⚠️  {len(orphan_workflows)} orphan workflows: {orphan_workflows}")

        return matrix

    def write_matrices(self, matrix: TraceabilityMatrix) -> Dict[str, Path]:
        """Write all matrices to CSV files."""
        output_files = {}

        # Agent → Workflow
        agent_workflow_path = self.output_dir / "agent-workflow-matrix.csv"
        if matrix.agent_workflow:
            with open(agent_workflow_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matrix.agent_workflow[0].keys())
                writer.writeheader()
                writer.writerows(matrix.agent_workflow)
            output_files["agent_workflow"] = agent_workflow_path

        # Workflow → Task
        workflow_task_path = self.output_dir / "workflow-task-matrix.csv"
        if matrix.workflow_task:
            with open(workflow_task_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matrix.workflow_task[0].keys())
                writer.writeheader()
                writer.writerows(matrix.workflow_task)
            output_files["workflow_task"] = workflow_task_path

        # Workflow → Workflow
        workflow_chain_path = self.output_dir / "workflow-chain-matrix.csv"
        if matrix.workflow_chain:
            with open(workflow_chain_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matrix.workflow_chain[0].keys())
                writer.writeheader()
                writer.writerows(matrix.workflow_chain)
            output_files["workflow_chain"] = workflow_chain_path

        # Party → Module
        party_module_path = self.output_dir / "party-module-matrix.csv"
        if matrix.party_module:
            with open(party_module_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matrix.party_module[0].keys())
                writer.writeheader()
                writer.writerows(matrix.party_module)
            output_files["party_module"] = party_module_path

        return output_files

    def generate_mermaid_graph(self) -> str:
        """Generate Mermaid dependency graph."""
        graph_lines = ["graph TD"]

        # Workflow → Task relationships
        for row in self.matrix_workflow_task[:20]:  # Limit for readability
            workflow = row["workflow_name"].replace("-", "_")
            task = row["task_invoked"].replace("-", "_")
            graph_lines.append(f"    {workflow} -->|invokes| {task}")

        # Workflow → Workflow chains
        for row in self.matrix_workflow_chain[:20]:
            parent = row["parent_workflow"].replace("-", "_")
            child = row["child_workflow"].replace("-", "_")
            graph_lines.append(f"    {parent} -->|chains to| {child}")

        return "\n".join(graph_lines)

    def generate_report(self) -> str:
        """Generate summary report."""
        report = []
        report.append("# BMAD Traceability Report")
        report.append("")
        report.append("## Summary Statistics")
        report.append("")
        report.append(f"- **Agents**: {len(self.agents)}")
        report.append(f"- **Workflows**: {len(self.workflows)}")
        report.append(f"- **Tasks**: {len(self.tasks)}")
        report.append(f"- **Invocations**: {len(self.invocations)}")
        report.append(f"- **Party Configs**: {len(self.party_configs)}")
        report.append("")
        report.append("## Matrix Files Generated")
        report.append("")
        for name, path in self.write_matrices.__annotations__.items():
            report.append(f"- `{name}`: {path}")
        report.append("")
        report.append("## Cycle Detection")
        report.append("")
        cycles = self.detect_cycles()
        if cycles:
            report.append(f"⚠️ **{len(cycles)} cycles detected**:")
            for parent, child in cycles:
                report.append(f"- {parent} → {child}")
        else:
            report.append("✓ No workflow cycles detected")
        report.append("")
        report.append("## Orphan Detection")
        report.append("")
        orphan_agents = self.detect_orphan_agents()
        orphan_workflows = self.detect_orphan_workflows()
        if orphan_agents:
            report.append(f"### Orphan Agents ({len(orphan_agents)})")
            for agent in orphan_agents:
                report.append(f"- `{agent}`")
        if orphan_workflows:
            report.append(f"### Orphan Workflows ({len(orphan_workflows)})")
            for workflow in orphan_workflows:
                report.append(f"- `{workflow}`")
        report.append("")
        report.append("## Dependency Graph")
        report.append("")
        report.append("```mermaid")
        report.append(self.generate_mermaid_graph())
        report.append("```")

        return "\n".join(report)


def main():
    """Main entry point."""
    import os
    import sys

    # Support hardcoded path from env var or use default
    project_root = Path(os.environ.get("PROJECT_ROOT", "/home/mike-anderson/dev/cohezion"))
    config = EngineConfig(
        project_root=project_root,
        output_dir=project_root / "_bmad" / "_config" / "traceability",
        verbose=True,
    )
    engine = TraceabilityEngine(config=config)

    print("🔍 BMAD Traceability Engine")
    print("=" * 50)

    # Check for self-trace mode
    self_trace = "--self-trace" in sys.argv

    if self_trace:
        print("🔄 Self-trace mode: ENABLED (tracing traceability/ directory)")
    else:
        print("🔄 Self-trace mode: DISABLED (excluding traceability/)")

    matrix = engine.run_full_extraction(self_trace=self_trace)
    output_files = engine.write_matrices(matrix)

    print("\n📊 Generated matrices:")
    for name, path in output_files.items():
        print(f"  {name}: {path}")

    report = engine.generate_report()
    report_path = engine.output_dir / "traceability-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 Report written to: {report_path}")

    # Generate Mermaid graph
    mermaid_path = engine.output_dir / "traceability-graph.md"
    with open(mermaid_path, "w", encoding="utf-8") as f:
        f.write("# BMAD Traceability Graph\n\n")
        f.write("```mermaid\n")
        f.write(engine.generate_mermaid_graph())
        f.write("\n```\n")

    print(f"📈 Graph written to: {mermaid_path}")

    # Version snapshot
    from datetime import datetime

    snapshot_dir = engine.output_dir / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = snapshot_dir / f"traceability_{timestamp}.csv"

    with open(snapshot_file, "w", encoding="utf-8") as f:
        f.write(f"timestamp,{timestamp}\n")
        f.write(f"agents,{len(engine.agents)}\n")
        f.write(f"workflows,{len(engine.workflows)}\n")
        f.write(f"tasks,{len(engine.tasks)}\n")
        f.write(f"invocations,{len(engine.invocations)}\n")
        f.write(f"self_trace,{self_trace}\n")

    print(f"💾 Snapshot saved to: {snapshot_file}")
    print("\n✅ Traceability extraction complete!")


if __name__ == "__main__":
    main()
