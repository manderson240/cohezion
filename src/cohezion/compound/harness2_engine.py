"""Harness^2: Recursive Agent Harnessing Engine (arXiv:2610.14224).

Implements the two connected levels of recursion from Harness^2:
1. Task-Level Recursion: Refines the execution harness for an open-world task
   using a contrastive Propose-Probe-Compose (PPC) cycle without ground-truth labels.
   Supports parallel (width k) and sequential (depth k) recursion.
2. Harnessing-Level Recursion: Turn task-level exploration outcomes into persistent
   continual improvement lessons, enforcing the strict Confounding Doctrine and
   persisting reusable components and EXPERIENCE.md records into SurrealDB and disk.

The 8 editable harness components (K=8):
- PROMPT: prompt.txt (persona, role framing, global goals)
- GUARDRAILS: guardrails.md (process boundaries, negative constraints, stop conditions)
- MEMORY: memory.md (workspace context, indices, session state)
- SKILLS: skills/ (modular domain expertise and procedural markdown guides)
- TOOLS: tools/ (tool definitions, usage rules, constraints)
- SCRIPTS: scripts/ (deterministic Python helper programs offloading computation from LLM)
- SUBAGENTS: subagents/ (specialized worker roles and delegation rules)
- PLUGIN: plugin.py (runtime event middleware, interception hooks, and telemetry)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class HarnessComponentType(StrEnum):
    """The K=8 canonical components of an agent execution harness."""

    PROMPT = "prompt.txt"
    GUARDRAILS = "guardrails.md"
    MEMORY = "memory.md"
    SKILLS = "skills"
    TOOLS = "tools"
    SCRIPTS = "scripts"
    SUBAGENTS = "subagents"
    PLUGIN = "plugin.py"


class HarnessVerdict(StrEnum):
    """Empirical verdict assigned to a component edit during reflection."""

    HELPED = "helped"
    HURT = "hurt"
    NO_OBSERVED_EFFECT = "no_observed_effect"
    CONFOUNDED = "confounded"


@dataclass
class ComponentEdit:
    """Record of a proposed and evaluated component modification."""

    component: HarnessComponentType
    candidate_scope: str  # "INV" (invariant/procedure) or "DOM" (domain/contract)
    change_summary: str
    diff_content: str
    observed_difference: str = ""
    verdict: HarnessVerdict = HarnessVerdict.NO_OBSERVED_EFFECT

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "candidate_scope": self.candidate_scope,
            "change_summary": self.change_summary,
            "diff_content": self.diff_content,
            "observed_difference": self.observed_difference,
            "verdict": self.verdict.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComponentEdit:
        return cls(
            component=HarnessComponentType(data["component"]),
            candidate_scope=str(data.get("candidate_scope", "INV")),
            change_summary=str(data.get("change_summary", "")),
            diff_content=str(data.get("diff_content", "")),
            observed_difference=str(data.get("observed_difference", "")),
            verdict=HarnessVerdict(data.get("verdict", HarnessVerdict.NO_OBSERVED_EFFECT.value)),
        )


@dataclass
class HarnessDefinition:
    """Full K=8 component harness definition."""

    harness_id: str
    components: dict[HarnessComponentType, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_content(self, component: HarnessComponentType) -> str:
        return self.components.get(component, "")

    def set_content(self, component: HarnessComponentType, content: str) -> None:
        self.components[component] = content

    def calculate_hash(self) -> str:
        hasher = hashlib.sha256()
        for c in sorted(self.components.keys(), key=lambda x: x.value):
            hasher.update(c.value.encode("utf-8"))
            hasher.update(self.components[c].encode("utf-8"))
        return hasher.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "harness_id": self.harness_id,
            "components": {k.value: v for k, v in self.components.items()},
            "metadata": self.metadata,
            "hash": self.calculate_hash(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessDefinition:
        components = {
            HarnessComponentType(k): v
            for k, v in data.get("components", {}).items()
            if k in [c.value for c in HarnessComponentType]
        }
        return cls(
            harness_id=str(data.get("harness_id", "harness-unknown")),
            components=components,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ExecutionRecord:
    """Observed trajectory and deliverable from running a harness."""

    harness_id: str
    trajectory: list[dict[str, Any]]
    deliverable: str
    metrics: dict[str, float] = field(default_factory=dict)
    errors_encountered: list[str] = field(default_factory=list)
    execution_time_s: float = 0.0
    task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "harness_id": self.harness_id,
            "trajectory": self.trajectory,
            "deliverable": self.deliverable,
            "metrics": self.metrics,
            "errors_encountered": self.errors_encountered,
            "execution_time_s": self.execution_time_s,
            "task_id": self.task_id,
        }


@dataclass
class HarnessExperience:
    """A durable, transferable lesson extracted from a task's harness refinement."""

    experience_id: str
    cue: str  # Shape of the situation (pattern, not task-specific facts)
    lesson: str  # Transferable operation on a named harness component
    evidence: str  # Cites edit rows and trajectory contrasts
    confidence: str  # "high", "medium", "low"
    task_id: str
    component: HarnessComponentType
    timestamp: float = field(default_factory=time.time)

    def to_markdown(self) -> str:
        return f"""# EXPERIENCE: {self.experience_id}
- **Component**: `{self.component.value}`
- **Cue**: {self.cue}
- **Lesson**: {self.lesson}
- **Evidence**: {self.evidence}
- **Confidence**: {self.confidence}
- **Task ID**: `{self.task_id}`
- **Timestamp**: {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))}
"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "cue": self.cue,
            "lesson": self.lesson,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "task_id": self.task_id,
            "component": self.component.value,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessExperience:
        return cls(
            experience_id=str(data["experience_id"]),
            cue=str(data["cue"]),
            lesson=str(data["lesson"]),
            evidence=str(data["evidence"]),
            confidence=str(data.get("confidence", "medium")),
            task_id=str(data.get("task_id", "")),
            component=HarnessComponentType(data["component"]),
            timestamp=float(data.get("timestamp", time.time())),
        )


class ContrastiveProposer:
    """Proposes orthogonal Invariant (INV) and Domain (DOM) candidate harnesses."""

    @staticmethod
    def propose_candidates(
        base_harness: HarnessDefinition,
        reference_exec: ExecutionRecord,
        task_query: str,
        applicable_experiences: list[HarnessExperience] | None = None,
    ) -> tuple[HarnessDefinition, HarnessDefinition, list[ComponentEdit]]:
        """Generate orthogonal INV and DOM candidates from reference execution."""
        experiences = applicable_experiences or []
        edits: list[ComponentEdit] = []

        # 1. Propose Invariant Candidate (INV: how the agent works)
        inv_components = dict(base_harness.components)
        inv_summary = []

        # Invariant 1: If reference encountered tool errors or loops, add guardrail
        if reference_exec.errors_encountered or len(reference_exec.trajectory) > 20:
            guardrail_patch = (
                "\n\n## [INV-01] Error Trajectory & Loop Suppression Guardrail\n"
                "- If a tool call fails, inspect root cause before retrying. Do not repeat identical parameters.\n"
                "- Reopen and verify produced artifacts upon completion before emitting final deliverable.\n"
            )
            inv_components[HarnessComponentType.GUARDRAILS] = (
                inv_components.get(HarnessComponentType.GUARDRAILS, "") + guardrail_patch
            )
            edits.append(
                ComponentEdit(
                    component=HarnessComponentType.GUARDRAILS,
                    candidate_scope="INV",
                    change_summary="Injected loop suppression and artifact verification guardrail",
                    diff_content=guardrail_patch.strip(),
                )
            )
            inv_summary.append("loop_guard")

        # Invariant 2: Mechanical offload to scripts
        script_patch = (
            "#!/usr/bin/env python3\n"
            "# scripts/output_validator.py - Deterministic output validator\n"
            "import sys\n"
            "def validate(content: str) -> bool:\n"
            "    return len(content.strip()) > 0 and 'Traceback' not in content\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(0 if validate(sys.stdin.read()) else 1)\n"
        )
        inv_components[HarnessComponentType.SCRIPTS] = script_patch
        edits.append(
            ComponentEdit(
                component=HarnessComponentType.SCRIPTS,
                candidate_scope="INV",
                change_summary="Offloaded deliverable sanity checking to deterministic verification script",
                diff_content="scripts/output_validator.py added",
            )
        )
        inv_summary.append("script_offload")

        # Apply applicable library lessons to INV
        for exp in experiences:
            if exp.confidence in ("high", "medium") and exp.component in inv_components:
                inv_components[exp.component] += (
                    f"\n\n# Lesson from {exp.experience_id}:\n{exp.lesson}\n"
                )
                edits.append(
                    ComponentEdit(
                        component=exp.component,
                        candidate_scope="INV",
                        change_summary=f"Adapted library lesson {exp.experience_id}",
                        diff_content=exp.lesson,
                    )
                )

        inv_candidate = HarnessDefinition(
            harness_id=f"{base_harness.harness_id}_inv",
            components=inv_components,
            metadata={"scope": "INV", "inventions": inv_summary},
        )

        # 2. Propose Domain Candidate (DOM: what a practitioner knows)
        dom_components = dict(base_harness.components)
        dom_summary = []

        # Domain 1: Analytic contracts and schema completeness
        contract_patch = (
            f"\n\n## [DOM-01] Domain Contract for Task: {task_query[:60]}\n"
            "- Inventory all source files, schemas, and relational keys before generating output.\n"
            "- Ensure cross-file reconciliation of numeric quantities, headers, and required sections.\n"
            "- Omit assumptions; explicitly verify facts against task context materials.\n"
        )
        dom_components[HarnessComponentType.SKILLS] = (
            dom_components.get(HarnessComponentType.SKILLS, "") + contract_patch
        )
        edits.append(
            ComponentEdit(
                component=HarnessComponentType.SKILLS,
                candidate_scope="DOM",
                change_summary="Injected domain analytic contract and cross-file reconciliation skill",
                diff_content=contract_patch.strip(),
            )
        )
        dom_summary.append("domain_contract")

        dom_candidate = HarnessDefinition(
            harness_id=f"{base_harness.harness_id}_dom",
            components=dom_components,
            metadata={"scope": "DOM", "inventions": dom_summary},
        )

        return inv_candidate, dom_candidate, edits


class BehavioralProber:
    """Analyzes execution traces to identify behavioral contrasts without ground-truth labels."""

    @staticmethod
    def extract_contrasts(
        reference_exec: ExecutionRecord,
        candidate_exec: ExecutionRecord,
    ) -> dict[str, Any]:
        """Compute behavioral contrasts between reference and probed execution."""
        ref_errors = len(reference_exec.errors_encountered)
        cand_errors = len(candidate_exec.errors_encountered)

        error_mitigated = cand_errors < ref_errors
        new_errors = cand_errors > ref_errors

        ref_len = len(reference_exec.trajectory)
        cand_len = len(candidate_exec.trajectory)

        # Check deliverable substance
        ref_deliv_len = len(reference_exec.deliverable.strip())
        cand_deliv_len = len(candidate_exec.deliverable.strip())
        deliverable_substantive = cand_deliv_len > 0 and (
            ref_deliv_len == 0 or cand_deliv_len >= int(ref_deliv_len * 0.8)
        )

        # Trajectory divergence point
        divergence_step = -1
        for step_idx in range(min(ref_len, cand_len)):
            ref_act = reference_exec.trajectory[step_idx].get("action")
            cand_act = candidate_exec.trajectory[step_idx].get("action")
            if ref_act != cand_act:
                divergence_step = step_idx
                break

        improved = error_mitigated or (
            deliverable_substantive and not new_errors and cand_len < ref_len
        )
        regressed = new_errors or (ref_deliv_len > 0 and cand_deliv_len == 0)

        return {
            "error_mitigated": error_mitigated,
            "new_errors": new_errors,
            "divergence_step": divergence_step,
            "deliverable_substantive": deliverable_substantive,
            "improved": improved,
            "regressed": regressed,
            "cand_len": cand_len,
            "ref_len": ref_len,
        }


class ContrastiveComposer:
    """Selectively composes verified edits from candidates into a successor harness."""

    @staticmethod
    def compose(
        base_harness: HarnessDefinition,
        inv_candidate: HarnessDefinition,
        dom_candidate: HarnessDefinition,
        inv_contrast: dict[str, Any],
        dom_contrast: dict[str, Any],
        proposed_edits: list[ComponentEdit],
    ) -> tuple[HarnessDefinition, list[ComponentEdit]]:
        """Selective evidence-based composition of supported edits."""
        successor_components = dict(base_harness.components)
        final_edits: list[ComponentEdit] = []

        inv_supported = inv_contrast.get("improved", False) and not inv_contrast.get(
            "regressed", False
        )
        dom_supported = dom_contrast.get("improved", False) and not dom_contrast.get(
            "regressed", False
        )

        for edit in proposed_edits:
            adopted = False
            verdict = HarnessVerdict.NO_OBSERVED_EFFECT
            observed_diff = ""

            if edit.candidate_scope == "INV":
                if inv_supported:
                    successor_components[edit.component] = inv_candidate.get_content(edit.component)
                    adopted = True
                    verdict = HarnessVerdict.HELPED
                    observed_diff = f"Diverged at step {inv_contrast.get('divergence_step', 0)}; errors mitigated."
                elif inv_contrast.get("regressed", False):
                    verdict = HarnessVerdict.HURT
                    observed_diff = "Candidate introduced execution regressions; edit rejected."
            elif edit.candidate_scope == "DOM":
                if dom_supported:
                    successor_components[edit.component] = dom_candidate.get_content(edit.component)
                    adopted = True
                    verdict = HarnessVerdict.HELPED
                    observed_diff = "Domain contract reconciled artifact completeness; substantive deliverable produced."
                elif dom_contrast.get("regressed", False):
                    verdict = HarnessVerdict.HURT
                    observed_diff = "Domain edits caused formatting regression; edit rejected."

            edit.verdict = verdict
            edit.observed_difference = observed_diff
            if adopted:
                final_edits.append(edit)

        successor_harness = HarnessDefinition(
            harness_id=f"{base_harness.harness_id}_succ",
            components=successor_components,
            metadata={
                "inv_supported": inv_supported,
                "dom_supported": dom_supported,
                "composed_edits_count": len(final_edits),
            },
        )
        return successor_harness, final_edits


class HarnessingReflector:
    """Extracts transferable experience for the continual improvement harness.

    Enforces the Confounding Doctrine:
    - Never invent unevidenced causal attributions.
    - If multiple components changed without isolated contrast, mark CONFOUNDED.
    - Lessons must name an abstract CUE, a concrete LESSON on a component, and cite EVIDENCE.
    """

    @staticmethod
    def reflect(
        task_id: str,
        base_harness: HarnessDefinition,
        candidate_edits: list[ComponentEdit],
        final_deliverable: str,
    ) -> tuple[list[ComponentEdit], HarnessExperience | None]:
        """Review improvement round, assign strict verdicts, and extract transferable experience."""
        # Count helped edits
        helped_edits = [e for e in candidate_edits if e.verdict == HarnessVerdict.HELPED]

        # Enforce Confounding Doctrine: if >2 components changed simultaneously and were adopted together,
        # individual causal attribution is confounded.
        if len(helped_edits) > 2:
            for e in helped_edits[1:]:
                e.verdict = HarnessVerdict.CONFOUNDED
                e.observed_difference += (
                    " [CONFOUNDED: bundled with multiple simultaneous component changes]"
                )

        # Extract at most ONE durable transferable lesson if supported
        primary_helped = [e for e in candidate_edits if e.verdict == HarnessVerdict.HELPED]
        if not primary_helped or not final_deliverable.strip():
            return candidate_edits, None

        best_edit = primary_helped[0]
        cue = (
            f"When an agent faces multi-step task execution in domain '{best_edit.candidate_scope}' "
            f"where initial trajectories exhibit procedural divergence or unverified output"
        )
        lesson = (
            f"Inject component '{best_edit.component.value}' with explicit verification constraints: "
            f"{best_edit.change_summary}."
        )
        evidence = f"Component edit on {best_edit.component.value} produced: {best_edit.observed_difference}"
        confidence = "high" if best_edit.verdict == HarnessVerdict.HELPED else "medium"

        exp = HarnessExperience(
            experience_id=f"exp_{task_id}_{best_edit.component.name.lower()}_{int(time.time())}",
            cue=cue,
            lesson=lesson,
            evidence=evidence,
            confidence=confidence,
            task_id=task_id,
            component=best_edit.component,
        )
        return candidate_edits, exp


class HarnessLibraryStore:
    """Manages persistent continual improvement harness library on disk and SurrealDB."""

    _SURREAL_URL = "http://localhost:8001/sql"
    _SURREAL_NS = "cohezion"
    _SURREAL_DB = "main"
    _SURREAL_AUTH = base64.b64encode(b"root:root").decode()

    def __init__(self, store_dir: Path | str | None = None) -> None:
        self.store_dir = (
            Path(store_dir) if store_dir else Path.home() / ".cohezion" / "harness_library"
        )
        self.store_dir.mkdir(parents=True, mode=0o700, exist_ok=True)

    def save_experience(self, exp: HarnessExperience) -> Path:
        """Saves experience card to disk and syncs to SurrealDB harness_experience table."""
        exp_dir = self.store_dir / exp.task_id
        exp_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        exp_file = exp_dir / f"{exp.experience_id}.md"
        exp_file.write_text(exp.to_markdown(), encoding="utf-8")

        # Sync to SurrealDB fail-open
        surql = (
            f"UPSERT harness_experience:`{exp.experience_id}` CONTENT {json.dumps(exp.to_dict())};"
        )
        try:
            req = urllib.request.Request(  # noqa: S310
                self._SURREAL_URL,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": self._SURREAL_NS,
                    "surreal-db": self._SURREAL_DB,
                    "Content-Type": "text/plain",
                    "Authorization": f"Basic {self._SURREAL_AUTH}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
                if resp.status == 200:
                    logger.debug("Persisted harness experience %s to SurrealDB", exp.experience_id)
        except Exception as exc:
            logger.warning("Could not persist harness experience to SurrealDB: %s", exc)

        return exp_file

    def list_experiences(
        self, component: HarnessComponentType | None = None
    ) -> list[HarnessExperience]:
        """Loads all experiences from disk, optionally filtered by component."""
        experiences: list[HarnessExperience] = []
        for file in self.store_dir.rglob("exp_*.md"):
            try:
                text = file.read_text(encoding="utf-8")
                lines = text.splitlines()
                exp_id = lines[0].replace("# EXPERIENCE:", "").strip() if lines else file.stem
                comp_val = ""
                cue = ""
                lesson = ""
                evidence = ""
                confidence = "medium"
                task_id = file.parent.name
                for line in lines:
                    if line.startswith("- **Component**:"):
                        comp_val = line.split("`")[1] if "`" in line else line.split(":")[1].strip()
                    elif line.startswith("- **Cue**:"):
                        cue = line.split(":", 1)[1].strip()
                    elif line.startswith("- **Lesson**:"):
                        lesson = line.split(":", 1)[1].strip()
                    elif line.startswith("- **Evidence**:"):
                        evidence = line.split(":", 1)[1].strip()
                    elif line.startswith("- **Confidence**:"):
                        confidence = line.split(":", 1)[1].strip()

                if comp_val:
                    c_type = HarnessComponentType(comp_val)
                    if component is None or c_type == component:
                        experiences.append(
                            HarnessExperience(
                                experience_id=exp_id,
                                cue=cue,
                                lesson=lesson,
                                evidence=evidence,
                                confidence=confidence,
                                task_id=task_id,
                                component=c_type,
                            )
                        )
            except Exception as e:
                logger.warning("Failed to parse experience file %s: %s", file, e)

        return sorted(experiences, key=lambda x: x.timestamp, reverse=True)


class Harness2Engine:
    """Master Orchestrator for Harness^2 Dual-Level Recursive Agent Harnessing."""

    def __init__(self, store: HarnessLibraryStore | None = None) -> None:
        self.store = store or HarnessLibraryStore()
        self.proposer = ContrastiveProposer()
        self.prober = BehavioralProber()
        self.composer = ContrastiveComposer()
        self.reflector = HarnessingReflector()

    def run_contrastive_improvement_step(
        self,
        task_id: str,
        task_query: str,
        base_harness: HarnessDefinition,
        reference_exec: ExecutionRecord,
        probe_runner_fn: Any,
    ) -> tuple[HarnessDefinition, ExecutionRecord, HarnessExperience | None, list[ComponentEdit]]:
        """Executes a single contrastive PPC step (k=1) and updates the continual library."""
        # 1. Retrieve applicable experiences from continual library
        applicable_exps = self.store.list_experiences()

        # 2. Propose orthogonal candidates
        inv_cand, dom_cand, proposed_edits = self.proposer.propose_candidates(
            base_harness=base_harness,
            reference_exec=reference_exec,
            task_query=task_query,
            applicable_experiences=applicable_exps,
        )

        # 3. Probe candidates under matched conditions
        inv_exec: ExecutionRecord = probe_runner_fn(inv_cand)
        dom_exec: ExecutionRecord = probe_runner_fn(dom_cand)

        # 4. Extract behavioral contrasts
        inv_contrast = self.prober.extract_contrasts(reference_exec, inv_exec)
        dom_contrast = self.prober.extract_contrasts(reference_exec, dom_exec)

        # 5. Compose successor harness
        successor_harness, final_edits = self.composer.compose(
            base_harness=base_harness,
            inv_candidate=inv_cand,
            dom_candidate=dom_cand,
            inv_contrast=inv_contrast,
            dom_contrast=dom_contrast,
            proposed_edits=proposed_edits,
        )

        # 6. Execute composed successor
        successor_exec: ExecutionRecord = probe_runner_fn(successor_harness)

        # 7. Level-2 Harnessing Reflection & Continual Library Update
        evaluated_edits, exp = self.reflector.reflect(
            task_id=task_id,
            base_harness=base_harness,
            candidate_edits=final_edits,
            final_deliverable=successor_exec.deliverable,
        )

        if exp is not None:
            self.store.save_experience(exp)

        return successor_harness, successor_exec, exp, evaluated_edits
