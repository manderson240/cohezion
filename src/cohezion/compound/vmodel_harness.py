"""V-Model coverage harness for Cohezion PRIME skills.

Implements the systems engineering V-Model bi-directional traceability principle:
  LEFT branch  (decomposition): PRIME skill spec → architecture → execution
  RIGHT branch (verification):  execution traces → DRR gates → coverage evidence

Coverage levels per skill:
  VERIFIED  — spec + tests + execution traces + passing DRR gate
  TRACED    — spec + execution traces (no dedicated test file)
  TESTED    — spec + test file (no execution traces yet)
  SPEC_ONLY — spec only (not yet exercised)

CLI:
    uv run python -m cohezion.compound.vmodel_harness
    uv run python -m cohezion.compound.vmodel_harness --skill ADVERSARIAL_TDD_PRIME
    uv run python -m cohezion.compound.vmodel_harness --json
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).parent.parent / "registry" / "skill_registry.json"
_TESTS_ROOT = Path(__file__).parent.parent.parent.parent / "tests"
_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = ("root", "root")
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}


@dataclass
class SkillVModelRecord:
    """V-Model coverage record for a single skill."""

    skill_name: str
    spec_path: str
    spec_exists: bool
    test_path: str
    test_exists: bool
    trace_count: int
    drr_gate_passed: bool
    spec_hash: str
    coverage_level: str = field(init=False)

    def __post_init__(self) -> None:
        if self.drr_gate_passed and self.trace_count > 0 and self.test_exists:
            self.coverage_level = "VERIFIED"
        elif self.trace_count > 0:
            self.coverage_level = "TRACED"
        elif self.test_exists:
            self.coverage_level = "TESTED"
        else:
            self.coverage_level = "SPEC_ONLY"

    @property
    def v_score(self) -> float:
        """0-1 V-model completeness score."""
        score = 0.25  # always have a spec if in registry
        if self.test_exists:
            score += 0.25
        if self.trace_count >= 10:
            score += 0.25
        elif self.trace_count > 0:
            score += 0.15
        if self.drr_gate_passed:
            score += 0.25
        return round(score, 2)


@dataclass
class VModelCoverageReport:
    """Full V-Model coverage report for all skills."""

    generated_at: float
    total_skills: int
    records: list[SkillVModelRecord]

    @property
    def by_level(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {"VERIFIED": [], "TRACED": [], "TESTED": [], "SPEC_ONLY": []}
        for r in self.records:
            out[r.coverage_level].append(r.skill_name)
        return out

    @property
    def summary(self) -> str:
        levels = self.by_level
        lines = [
            f"V-Model Coverage — {self.total_skills} skills",
            f"  VERIFIED  (spec+test+traces+DRR): {len(levels['VERIFIED'])}",
            f"  TRACED    (spec+traces):           {len(levels['TRACED'])}",
            f"  TESTED    (spec+test):             {len(levels['TESTED'])}",
            f"  SPEC_ONLY:                         {len(levels['SPEC_ONLY'])}",
        ]
        return "\n".join(lines)


class VModelHarness:
    """Compound V-Model harness — scans skill library and verifies coverage."""

    def __init__(
        self,
        registry_path: Path = _REGISTRY_PATH,
        tests_root: Path = _TESTS_ROOT,
        surreal_url: str = _SURREAL_URL,
        timeout: float = 10.0,
    ) -> None:
        self._registry_path = registry_path
        self._tests_root = tests_root
        self._surreal_url = surreal_url
        self._client = httpx.Client(timeout=timeout)
        self._registry: dict[str, Any] = {}
        self._trace_counts: dict[str, int] = {}
        self._drr_gates: dict[str, bool] = {}
        self._ensure_vmodel_tables()

    def _ensure_vmodel_tables(self) -> None:
        """Create vmodel_gate and proof_obligation tables (idempotent)."""
        ddl = """
        DEFINE TABLE IF NOT EXISTS vmodel_gate SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS skill_name  ON vmodel_gate TYPE string;
        DEFINE FIELD IF NOT EXISTS gate_level  ON vmodel_gate TYPE string;
        DEFINE FIELD IF NOT EXISTS passed      ON vmodel_gate TYPE bool;
        DEFINE FIELD IF NOT EXISTS spec_hash   ON vmodel_gate TYPE string;
        DEFINE FIELD IF NOT EXISTS trace_count ON vmodel_gate TYPE int;
        DEFINE FIELD IF NOT EXISTS session_id  ON vmodel_gate TYPE string;
        DEFINE FIELD IF NOT EXISTS created_at  ON vmodel_gate TYPE datetime VALUE time::now() READONLY;
        DEFINE INDEX IF NOT EXISTS idx_vmodel_skill ON vmodel_gate FIELDS skill_name;

        DEFINE TABLE IF NOT EXISTS proof_obligation SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS skill_name   ON proof_obligation TYPE string;
        DEFINE FIELD IF NOT EXISTS obligation   ON proof_obligation TYPE string;
        DEFINE FIELD IF NOT EXISTS satisfied_by ON proof_obligation TYPE string;
        DEFINE FIELD IF NOT EXISTS verified     ON proof_obligation TYPE bool;
        DEFINE FIELD IF NOT EXISTS created_at   ON proof_obligation TYPE datetime VALUE time::now() READONLY;
        """
        try:
            self._client.post(
                self._surreal_url,
                content=ddl,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
                timeout=15.0,
            )
        except Exception as exc:
            logger.debug("VModelHarness: table setup failed (non-fatal): %s", exc)

    def _load_registry(self) -> None:
        if not self._registry:
            self._registry = json.loads(self._registry_path.read_text())

    @staticmethod
    def _normalize_skill_name(name: str) -> str:
        """Normalize a skill name for fuzzy matching across naming conventions.

        Handles: "IDEATOR_PRIME" → "ideator", "ideator" → "ideator",
        "adversarial_tdd" → "adversarialtdd" matching "ADVERSARIAL_TDD_PRIME".
        """
        return name.lower().replace("_prime", "").replace("-", "").replace("_", "")

    def _fetch_trace_counts(self) -> None:
        """Query SurrealDB for execution trace counts per skill.

        Builds both exact and normalized lookup tables so that informal caller
        names (e.g. "ideator") match registry canonical names ("IDEATOR_PRIME").
        """
        sql = "SELECT skill_name, count() AS n FROM execution_trace GROUP BY skill_name;"
        try:
            resp = self._client.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                self._trace_counts = {r["skill_name"]: r["n"] for r in rows if "skill_name" in r}
                # Build normalized lookup: normalized_key → cumulative count
                # This bridges the gap between informal execute_task names and registry names.
                self._trace_counts_normalized: dict[str, int] = {}
                for raw_name, count in self._trace_counts.items():
                    key = self._normalize_skill_name(raw_name)
                    self._trace_counts_normalized[key] = (
                        self._trace_counts_normalized.get(key, 0) + count
                    )
        except Exception as exc:
            logger.debug("VModelHarness: trace count query failed: %s", exc)

    def _get_trace_count(self, skill_name: str) -> int:
        """Look up trace count for a skill, with normalized fallback."""
        exact = self._trace_counts.get(skill_name, 0)
        if exact:
            return exact
        normalized = getattr(self, "_trace_counts_normalized", {})
        return normalized.get(self._normalize_skill_name(skill_name), 0)

    def _fetch_drr_gates(self) -> None:
        """Query SurrealDB for latest DRR gate result per skill."""
        sql = "SELECT skill_name, passed FROM vmodel_gate ORDER BY created_at DESC LIMIT 500;"
        try:
            resp = self._client.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                for r in rows:
                    skill = r.get("skill_name", "")
                    if skill and skill not in self._drr_gates:
                        self._drr_gates[skill] = bool(r.get("passed", False))
        except Exception as exc:
            logger.debug("VModelHarness: DRR gate query failed: %s", exc)

    def _find_test_file(self, skill_name: str) -> tuple[str, bool]:
        """Find the right-branch test file for a skill."""
        # Normalize skill name: ADVERSARIAL_TDD_PRIME → adversarial_tdd
        base = skill_name.lower().replace("_prime", "").replace("-", "_")
        candidates = [
            self._tests_root / "skills" / f"test_{base}.py",
            self._tests_root / "compound" / f"test_{base}.py",
            self._tests_root / f"test_{base}.py",
        ]
        for p in candidates:
            if p.exists():
                return str(p), True
        return str(candidates[0]), False

    def _generate_drr(
        self, skill_name: str, spec_path: str, test_path: str, test_exists: bool, trace_count: int
    ) -> bool:
        """Run DRR-3 (IMPLEMENTATION gate) for one skill and persist result."""
        spec_hash = ""
        p = Path(spec_path) if spec_path else None
        spec_file_exists = bool(p and p.is_file())
        if spec_file_exists and p:
            spec_hash = hashlib.sha256(p.read_bytes()).hexdigest()

        # V-model gate logic:
        # Pass conditions: spec exists AND (has traces OR has test)
        passed = spec_file_exists and (trace_count > 0 or test_exists)

        session_id = f"vmodel-harness-{int(time.time())}"
        skill_esc = skill_name.replace('"', '\\"')
        sql = (
            f"CREATE vmodel_gate SET "
            f'skill_name = "{skill_esc}", '
            f'gate_level = "DRR-3-IMPLEMENTATION", '
            f"passed = {str(passed).lower()}, "
            f'spec_hash = "{spec_hash[:16]}", '
            f"trace_count = {trace_count}, "
            f'session_id = "{session_id}";'
        )
        try:
            self._client.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
        except Exception as exc:
            logger.debug("VModelHarness: DRR persist failed for %s: %s", skill_name, exc)

        return passed

    def scan(
        self, skill_filter: str | None = None, persist_drr: bool = True
    ) -> VModelCoverageReport:
        """Scan skill registry and build V-Model coverage report.

        Args:
            skill_filter: If set, only process this skill name.
            persist_drr: If True, write DRR gate results to SurrealDB.
        """
        self._load_registry()
        self._fetch_trace_counts()
        self._fetch_drr_gates()

        records: list[SkillVModelRecord] = []
        skills = (
            self._registry
            if skill_filter is None
            else {
                k: v
                for k, v in self._registry.items()
                if k.lower() == skill_filter.lower()
                or k.lower() == skill_filter.lower().replace("-", "_")
            }
        )

        repo_root = Path(__file__).parent.parent.parent.parent
        for skill_name, meta in skills.items():
            raw_path = meta.get("path") or ""
            spec_path = str(repo_root / raw_path) if raw_path else ""
            spec_p = Path(spec_path) if spec_path else None
            spec_exists = bool(spec_p and spec_p.is_file())
            test_path, test_exists = self._find_test_file(skill_name)
            trace_count = self._get_trace_count(skill_name)

            if persist_drr:
                drr_passed = self._generate_drr(
                    skill_name, spec_path, test_path, test_exists, trace_count
                )
            else:
                drr_passed = self._drr_gates.get(skill_name, False)

            spec_hash = ""
            if spec_exists and spec_p:
                spec_hash = hashlib.sha256(spec_p.read_bytes()).hexdigest()[:16]

            records.append(
                SkillVModelRecord(
                    skill_name=skill_name,
                    spec_path=spec_path,
                    spec_exists=spec_exists,
                    test_path=test_path,
                    test_exists=test_exists,
                    trace_count=trace_count,
                    drr_gate_passed=drr_passed,
                    spec_hash=spec_hash,
                )
            )

        records.sort(key=lambda r: (-r.v_score, r.skill_name))
        return VModelCoverageReport(
            generated_at=time.time(),
            total_skills=len(records),
            records=records,
        )

    def upsert_proof_obligations(self, skill_name: str, obligations: list[dict[str, Any]]) -> None:
        """Write proof obligation records to SurrealDB for a skill.

        Each obligation: {"obligation": str, "satisfied_by": str, "verified": bool}
        """
        for ob in obligations:
            skill_esc = skill_name.replace('"', '\\"')
            ob_esc = str(ob.get("obligation", "")).replace('"', '\\"')
            by_esc = str(ob.get("satisfied_by", "")).replace('"', '\\"')
            verified = str(ob.get("verified", False)).lower()
            sql = (
                f"CREATE proof_obligation SET "
                f'skill_name = "{skill_esc}", '
                f'obligation = "{ob_esc}", '
                f'satisfied_by = "{by_esc}", '
                f"verified = {verified};"
            )
            try:
                self._client.post(
                    self._surreal_url,
                    content=sql,
                    headers=_SURREAL_HEADERS,
                    auth=_SURREAL_AUTH,
                )
            except Exception as exc:
                logger.debug("Proof obligation write failed: %s", exc)


def run_coverage(skill_filter: str | None = None, as_json: bool = False) -> VModelCoverageReport:
    """Convenience entry point for CLI and compound loop use."""
    harness = VModelHarness()
    report = harness.scan(skill_filter=skill_filter, persist_drr=True)

    if as_json:
        print(
            json.dumps(
                {
                    "generated_at": report.generated_at,
                    "total_skills": report.total_skills,
                    "by_level": {k: len(v) for k, v in report.by_level.items()},
                    "records": [
                        {
                            "skill_name": r.skill_name,
                            "coverage_level": r.coverage_level,
                            "v_score": r.v_score,
                            "trace_count": r.trace_count,
                            "test_exists": r.test_exists,
                            "drr_gate_passed": r.drr_gate_passed,
                        }
                        for r in report.records
                    ],
                },
                indent=2,
            )
        )
    else:
        print(report.summary)
        print()
        # Show top gaps
        gaps = [r for r in report.records if r.coverage_level == "SPEC_ONLY"][:10]
        if gaps:
            print(f"Top {len(gaps)} SPEC_ONLY skills (need tests + execution traces):")
            for r in gaps:
                print(f"  {r.skill_name}")

    return report


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Cohezion V-Model coverage harness")
    parser.add_argument("--skill", help="Scan a single skill by name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-persist", action="store_true", help="Skip DRR SurrealDB writes")
    args = parser.parse_args()

    harness = VModelHarness()
    report = harness.scan(skill_filter=args.skill, persist_drr=not args.no_persist)

    if args.json:
        print(
            json.dumps(
                {
                    "total": report.total_skills,
                    "by_level": {k: len(v) for k, v in report.by_level.items()},
                    "records": [asdict(r) for r in report.records],
                },
                indent=2,
            )
        )
    else:
        print(report.summary)
        if args.skill:
            for r in report.records:
                print(f"\n{r.skill_name}")
                print(f"  spec:       {r.spec_path} ({'✓' if r.spec_exists else '✗'})")
                print(f"  test:       {r.test_path} ({'✓' if r.test_exists else '✗'})")
                print(f"  traces:     {r.trace_count}")
                print(f"  DRR gate:   {'PASS' if r.drr_gate_passed else 'FAIL'}")
                print(f"  v_score:    {r.v_score}")
                print(f"  coverage:   {r.coverage_level}")


if __name__ == "__main__":
    main()
