"""IV&V Cryptographic Authority System.

Provides true cryptographic and architectural separation between code creation
and independent verification & validation (IV&V).

Key components:
- IVVSeverity: Finding severity taxonomy (P0_CRITICAL, P1_HIGH, P2_MODERATE, PASS).
- IVVFinding: Structured finding record with gate, invariant, and counterexamples.
- VerificationRequest: Work package request submitted for independent audit.
- IVVAssertion: Cryptographically signed assertion payload binding artifact and test suite.
- IVVKeyManager: Manages 256-bit authority secret key (~/.cohezion/security/ivv_authority.key).
- IVVAuthority: Signs and verifies assertions with strict independence checks.
- IVVAuthorityService: High-level independent verifier discovering tests, auditing AST,
  executing test suites, signing assertions, and syncing to SurrealDB.
"""

from __future__ import annotations

import ast
import base64
import csv
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import subprocess
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class IVVSeverity(str, Enum):
    """Severity classification for IV&V findings."""

    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_MODERATE = "P2_MODERATE"
    PASS = "PASS"


@dataclass
class IVVFinding:
    """Finding surfaced during IV&V analysis or test suite execution."""

    gate: str
    severity: IVVSeverity
    description: str
    counterexample: str = ""
    suggested_invariant: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding to dictionary."""
        return {
            "gate": self.gate,
            "severity": self.severity.value
            if isinstance(self.severity, Enum)
            else str(self.severity),
            "description": self.description,
            "counterexample": self.counterexample,
            "suggested_invariant": self.suggested_invariant,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IVVFinding:
        """Instantiate finding from dictionary."""
        sev_raw = data.get("severity", IVVSeverity.PASS.value)
        try:
            sev = IVVSeverity(sev_raw)
        except ValueError:
            sev = IVVSeverity.PASS
        return cls(
            gate=str(data.get("gate", "")),
            severity=sev,
            description=str(data.get("description", "")),
            counterexample=str(data.get("counterexample", "")),
            suggested_invariant=str(data.get("suggested_invariant", "")),
        )


@dataclass
class VerificationRequest:
    """Request submitted to IV&V Authority for independent verification."""

    artifact_path: str
    competition: str
    creator_id: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize verification request to dictionary."""
        return {
            "artifact_path": self.artifact_path,
            "competition": self.competition,
            "creator_id": self.creator_id,
            "timestamp": self.timestamp,
        }


@dataclass
class IVVAssertion:
    """Cryptographically signed assertion certifying independent verification."""

    artifact_hash: str
    test_suite_hash: str
    creator_id: str
    verifier_id: str
    competition: str
    timestamp: float
    passed: bool
    findings: list[IVVFinding] = field(default_factory=list)
    signature: str = ""

    def canonical_payload(self) -> bytes:
        """Deterministically serialize assertion payload for HMAC signature generation."""
        payload = {
            "artifact_hash": self.artifact_hash,
            "competition": self.competition,
            "creator_id": self.creator_id,
            "findings": [f.to_dict() for f in self.findings],
            "passed": self.passed,
            "test_suite_hash": self.test_suite_hash,
            "timestamp": round(float(self.timestamp), 4),
            "verifier_id": self.verifier_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Serialize assertion to dictionary."""
        return {
            "artifact_hash": self.artifact_hash,
            "test_suite_hash": self.test_suite_hash,
            "creator_id": self.creator_id,
            "verifier_id": self.verifier_id,
            "competition": self.competition,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IVVAssertion:
        """Instantiate assertion from dictionary."""
        findings_data = data.get("findings", [])
        findings = [IVVFinding.from_dict(f) if isinstance(f, dict) else f for f in findings_data]
        return cls(
            artifact_hash=str(data["artifact_hash"]),
            test_suite_hash=str(data["test_suite_hash"]),
            creator_id=str(data["creator_id"]),
            verifier_id=str(data["verifier_id"]),
            competition=str(data["competition"]),
            timestamp=float(data.get("timestamp", 0.0)),
            passed=bool(data.get("passed", False)),
            findings=findings,
            signature=str(data.get("signature", "")),
        )


class IVVKeyManager:
    """Manages the private authority key file and cryptographic HMAC operations."""

    DEFAULT_KEY_PATH = Path.home() / ".cohezion" / "security" / "ivv_authority.key"

    def __init__(self, key_path: Path | str | None = None) -> None:
        self.key_path = Path(key_path) if key_path else self.DEFAULT_KEY_PATH
        self._key: bytes | None = None
        self._ensure_key()

    def _ensure_key(self) -> None:
        """Generates 256-bit secret key with 0600 permissions if not exists, or loads existing."""
        if not self.key_path.exists():
            self.key_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            try:
                os.chmod(self.key_path.parent, 0o700)
            except OSError:
                pass

            secret_key = secrets.token_bytes(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            mode = 0o600
            fd = os.open(str(self.key_path), flags, mode)
            with os.fdopen(fd, "wb") as f:
                f.write(secret_key)
            self._key = secret_key
            logger.info("Initialized IV&V Authority secret key at %s (chmod 0600)", self.key_path)
        else:
            try:
                os.chmod(self.key_path, 0o600)
            except OSError as err:
                logger.warning("Could not enforce 0600 permissions on %s: %s", self.key_path, err)
            raw = self.key_path.read_bytes()
            if len(raw) == 64:
                try:
                    self._key = bytes.fromhex(raw.decode("ascii"))
                except ValueError:
                    self._key = raw
            else:
                self._key = raw

    @property
    def key(self) -> bytes:
        """Return the raw 256-bit secret authority key."""
        if self._key is None:
            self._ensure_key()
        return self._key  # type: ignore[return-value]

    def sign(self, message: bytes) -> str:
        """Compute HMAC-SHA256 signature over binary payload."""
        return hmac.new(self.key, message, hashlib.sha256).hexdigest()

    def verify(self, message: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature in constant time."""
        expected = self.sign(message)
        return hmac.compare_digest(expected, signature)


class IVVAuthority:
    """Cryptographic authority issuing and validating IV&V assertions."""

    DEFAULT_STORE_DIR = Path.home() / ".cohezion" / "security" / "assertions"

    def __init__(
        self,
        key_manager: IVVKeyManager | None = None,
        store_dir: Path | str | None = None,
    ) -> None:
        self.key_manager = key_manager or IVVKeyManager()
        self.store_dir = Path(store_dir) if store_dir else self.DEFAULT_STORE_DIR

    def sign_assertion(
        self,
        artifact_hash: str,
        test_suite_hash: str,
        creator_id: str,
        verifier_id: str,
        competition: str,
        passed: bool,
        findings: list[IVVFinding] | None = None,
        timestamp: float | None = None,
    ) -> IVVAssertion:
        """Signs an assertion payload with the private authority key.

        Parameters
        ----------
        artifact_hash : str
            SHA-256 hash of the artifact under test.
        test_suite_hash : str
            SHA-256 hash of the independent test suite.
        creator_id : str
            Identity of the code author or creator agent.
        verifier_id : str
            Identity of the independent verifier agent or service.
        competition : str
            Competition or task name.
        passed : bool
            Whether all gates and test requirements passed.
        findings : list[IVVFinding] | None
            Findings surfaced during verification.
        timestamp : float | None
            Timestamp for the assertion.

        Returns
        -------
        IVVAssertion
            The cryptographically signed assertion.

        Raises
        ------
        ValueError
            If creator_id equals verifier_id (independence violation).
        """
        if creator_id == verifier_id:
            raise ValueError(
                f"Independence violation: creator_id '{creator_id}' matches verifier_id '{verifier_id}'"
            )

        ts = timestamp if timestamp is not None else time.time()
        findings_list = findings or []

        assertion = IVVAssertion(
            artifact_hash=artifact_hash,
            test_suite_hash=test_suite_hash,
            creator_id=creator_id,
            verifier_id=verifier_id,
            competition=competition,
            timestamp=ts,
            passed=passed,
            findings=findings_list,
            signature="",
        )
        canonical = assertion.canonical_payload()
        assertion.signature = self.key_manager.sign(canonical)
        return assertion

    def verify_assertion(
        self,
        assertion: IVVAssertion,
        artifact_path: str,
    ) -> tuple[bool, str]:
        """Cryptographically verifies independence, file hash match, and HMAC signature.

        Parameters
        ----------
        assertion : IVVAssertion
            The signed assertion to evaluate.
        artifact_path : str
            Path to the artifact file on disk.

        Returns
        -------
        tuple[bool, str]
            (True, "Verification successful") if valid, else (False, reason).
        """
        # 1. Enforce creator != verifier
        if assertion.creator_id == assertion.verifier_id:
            return (
                False,
                f"Independence violated: creator and verifier are identical ('{assertion.creator_id}')",
            )

        # 2. Check artifact file existence & sha256 match
        path = Path(artifact_path)
        if not path.is_file():
            return False, f"Artifact file not found: {artifact_path}"

        computed_artifact_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if computed_artifact_hash != assertion.artifact_hash:
            return (
                False,
                f"Artifact hash mismatch: expected {assertion.artifact_hash}, computed {computed_artifact_hash}",
            )

        # 3. Verify HMAC signature against authority key
        payload = assertion.canonical_payload()
        if not self.key_manager.verify(payload, assertion.signature):
            return False, "Invalid cryptographic HMAC signature: assertion modified or forged"

        # 4. Verify passed status
        if not assertion.passed:
            return False, "Assertion verification status is marked as failed"

        return True, "Verification assertion passed: independent signature and integrity confirmed"

    def save_assertion(
        self,
        assertion: IVVAssertion,
        path: Path | str | None = None,
    ) -> Path:
        """Saves assertion to ~/.cohezion/security/assertions/{artifact_hash}.json or custom path."""
        target_path = Path(path) if path else (self.store_dir / f"{assertion.artifact_hash}.json")
        target_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        target_path.write_text(json.dumps(assertion.to_dict(), indent=2), encoding="utf-8")
        try:
            os.chmod(target_path, 0o600)
        except OSError:
            pass
        logger.info("Saved signed IV&V assertion to %s", target_path)
        return target_path

    def load_assertion(
        self,
        artifact_hash: str,
        path: Path | str | None = None,
    ) -> IVVAssertion | None:
        """Loads assertion from disk by artifact hash."""
        target_path = Path(path) if path else (self.store_dir / f"{artifact_hash}.json")
        if not target_path.is_file():
            return None
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            return IVVAssertion.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load assertion from %s: %s", target_path, exc)
            return None


class IVVAuthorityService:
    """High-level independent verification and validation authority service."""

    DEFAULT_TESTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "ivv"
    _SURREAL_URL = "http://localhost:8001/sql"
    _SURREAL_NS = "cohezion"
    _SURREAL_DB = "main"
    _SURREAL_AUTH = base64.b64encode(b"root:root").decode()

    def __init__(
        self,
        authority: IVVAuthority | None = None,
        verifier_id: str = "ivv-authority-daemon-v1",
        tests_dir: Path | str | None = None,
        surreal_url: str = _SURREAL_URL,
    ) -> None:
        self.authority = authority or IVVAuthority()
        self.verifier_id = verifier_id
        self.tests_dir = Path(tests_dir) if tests_dir else self.DEFAULT_TESTS_DIR
        self.surreal_url = surreal_url

    def discover_test_suite(self, competition: str) -> list[Path]:
        """Discovers verifier-owned test suite files in tests/ivv/ matching competition."""
        if not self.tests_dir.exists():
            return []

        comp_slug = competition.lower().replace("-", "_").replace(" ", "_")
        matches: list[Path] = []
        for file in self.tests_dir.rglob("*.py"):
            name = file.stem.lower()
            if comp_slug in name or name in comp_slug:
                matches.append(file)

        if not matches:
            generic = list(self.tests_dir.glob("test_general*.py")) + list(
                self.tests_dir.glob("test_ivv*.py")
            )
            matches = generic

        return sorted(matches)

    def calculate_test_suite_hash(self, test_files: list[Path]) -> str:
        """Calculates deterministic SHA256 of discovered test suite files."""
        if not test_files:
            return hashlib.sha256(b"").hexdigest()

        hasher = hashlib.sha256()
        for f in sorted(test_files):
            hasher.update(f.name.encode("utf-8"))
            hasher.update(f.read_bytes())
        return hasher.hexdigest()

    def audit_ast_and_invariants(self, code: str) -> list[IVVFinding]:
        """Audits artifact code AST for syntax errors, key exfiltration, or tampering."""
        findings: list[IVVFinding] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as err:
            findings.append(
                IVVFinding(
                    gate="AST_PARSE",
                    severity=IVVSeverity.P0_CRITICAL,
                    description=f"Syntax error in artifact: {err}",
                    counterexample=str(err.text or "").strip(),
                    suggested_invariant="Artifact must be syntactically valid Python",
                )
            )
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "ivv_authority.key" in node.value:
                    findings.append(
                        IVVFinding(
                            gate="SECURITY_BOUNDARY",
                            severity=IVVSeverity.P0_CRITICAL,
                            description="Artifact contains reference to private authority key path",
                            counterexample=node.value,
                            suggested_invariant="Creator artifact must not reference internal authority key",
                        )
                    )
            if isinstance(node, ast.Attribute) and node.attr in (
                "_key",
                "sign",
                "verify_assertion",
            ):
                findings.append(
                    IVVFinding(
                        gate="SECURITY_INTEGRITY",
                        severity=IVVSeverity.P1_HIGH,
                        description=f"Artifact accesses sensitive authority attribute: {node.attr}",
                        counterexample=f"Access to attribute {node.attr}",
                        suggested_invariant="Artifact must not manipulate internal verification attributes",
                    )
                )

        return findings

    def audit_tabular_and_data_artifacts(
        self, artifact_path: Path, artifact_bytes: bytes
    ) -> list[IVVFinding]:
        """Audits data/tabular artifacts (CSV, Parquet, JSON, text) for structural validity and security."""
        findings: list[IVVFinding] = []
        if len(artifact_bytes) == 0:
            findings.append(
                IVVFinding(
                    gate="DATA_INTEGRITY",
                    severity=IVVSeverity.P0_CRITICAL,
                    description=f"Artifact {artifact_path.name} is 0 bytes (empty file)",
                    suggested_invariant="Artifact must contain non-empty data",
                )
            )
            return findings

        # Check for authority key leak in raw text/bytes
        try:
            sample_text = artifact_bytes[:500000].decode("utf-8", errors="replace")
            if "ivv_authority.key" in sample_text:
                findings.append(
                    IVVFinding(
                        gate="SECURITY_BOUNDARY",
                        severity=IVVSeverity.P0_CRITICAL,
                        description="Artifact contains reference to private authority key path",
                        counterexample="ivv_authority.key found in data artifact",
                        suggested_invariant="Creator artifact must not reference internal authority key",
                    )
                )
        except Exception:
            pass

        suffix = artifact_path.suffix.lower()
        if suffix in (".csv", ".tsv"):
            delimiter = "\t" if suffix == ".tsv" else ","
            try:
                # Sample up to 100,000 characters
                sample_str = artifact_bytes[:100000].decode("utf-8", errors="replace")
                reader = csv.reader(io.StringIO(sample_str), delimiter=delimiter)
                header = next(reader, None)
                if not header:
                    findings.append(
                        IVVFinding(
                            gate="CSV_VALIDITY",
                            severity=IVVSeverity.P0_CRITICAL,
                            description=f"CSV artifact {artifact_path.name} has no valid header row",
                            suggested_invariant="CSV artifact must contain a valid header row",
                        )
                    )
                else:
                    first_row = next(reader, None)
                    if not first_row:
                        findings.append(
                            IVVFinding(
                                gate="CSV_VALIDITY",
                                severity=IVVSeverity.P1_HIGH,
                                description=f"CSV artifact {artifact_path.name} has a header but no data rows",
                                suggested_invariant="CSV artifact must contain data rows",
                            )
                        )
            except Exception as exc:
                findings.append(
                    IVVFinding(
                        gate="CSV_VALIDITY",
                        severity=IVVSeverity.P0_CRITICAL,
                        description=f"Error parsing CSV artifact: {exc}",
                        suggested_invariant="CSV artifact must be valid delimiter-separated text",
                    )
                )
        elif suffix == ".json":
            try:
                json.loads(artifact_bytes.decode("utf-8"))
            except Exception as exc:
                findings.append(
                    IVVFinding(
                        gate="JSON_VALIDITY",
                        severity=IVVSeverity.P0_CRITICAL,
                        description=f"Error parsing JSON artifact: {exc}",
                        suggested_invariant="JSON artifact must be syntactically valid JSON",
                    )
                )
        elif suffix in (".parquet", ".feather"):
            if suffix == ".parquet" and not artifact_bytes.startswith(b"PAR1"):
                findings.append(
                    IVVFinding(
                        gate="PARQUET_VALIDITY",
                        severity=IVVSeverity.P0_CRITICAL,
                        description="Parquet artifact missing standard PAR1 magic header",
                        suggested_invariant="Parquet artifact must start with PAR1 magic bytes",
                    )
                )

        return findings

    def execute_test_suite(self, test_files: list[Path], artifact_path: Path) -> list[IVVFinding]:
        """Executes verifier-owned pytest suite against artifact if tests exist."""
        findings: list[IVVFinding] = []
        if not test_files:
            return findings

        test_paths = [str(p) for p in test_files]
        cmd = ["pytest", "-q", "--disable-warnings"] + test_paths
        env = dict(os.environ)
        env["IVV_ARTIFACT_PATH"] = str(artifact_path)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            if result.returncode != 0:
                findings.append(
                    IVVFinding(
                        gate="TEST_SUITE_EXECUTION",
                        severity=IVVSeverity.P0_CRITICAL,
                        description=f"Independent test suite failed (exit code {result.returncode})",
                        counterexample=result.stdout[-500:]
                        if result.stdout
                        else result.stderr[-500:],
                        suggested_invariant="All tests in independent verifier suite must pass",
                    )
                )
        except subprocess.TimeoutExpired:
            findings.append(
                IVVFinding(
                    gate="TEST_SUITE_EXECUTION",
                    severity=IVVSeverity.P0_CRITICAL,
                    description="Independent test suite timed out after 120s",
                    suggested_invariant="Test suite execution must finish within time bounds",
                )
            )
        except Exception as exc:
            findings.append(
                IVVFinding(
                    gate="TEST_SUITE_EXECUTION",
                    severity=IVVSeverity.P1_HIGH,
                    description=f"Error executing independent test suite: {exc}",
                    suggested_invariant="Test suite execution must execute cleanly",
                )
            )

        return findings

    def _persist_to_surrealdb(self, assertion: IVVAssertion) -> bool:
        """Persists signed assertion to SurrealDB verification_assertion table (fail-open)."""
        safe_id = (
            assertion.artifact_hash
            if assertion.artifact_hash.isalnum()
            else f"`{assertion.artifact_hash}`"
        )
        data = assertion.to_dict()
        surql = f"UPSERT verification_assertion:{safe_id} CONTENT {json.dumps(data)};"
        try:
            req = urllib.request.Request(
                self.surreal_url,
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
                return resp.status == 200
        except Exception as exc:
            logger.warning("Could not persist assertion to SurrealDB: %s", exc)
            return False

    def verify_request(self, request: VerificationRequest) -> IVVAssertion:
        """Process verification request, audit artifact, execute test suite, and sign assertion."""
        artifact_path = Path(request.artifact_path)
        if not artifact_path.is_file():
            finding = IVVFinding(
                gate="ARTIFACT_EXISTS",
                severity=IVVSeverity.P0_CRITICAL,
                description=f"Artifact not found at {request.artifact_path}",
            )
            return self.authority.sign_assertion(
                artifact_hash="0" * 64,
                test_suite_hash="0" * 64,
                creator_id=request.creator_id,
                verifier_id=self.verifier_id,
                competition=request.competition,
                passed=False,
                findings=[finding],
            )

        artifact_bytes = artifact_path.read_bytes()
        artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()

        # Handle notebook vs zip vs python file vs tabular/data artifact
        suffix = artifact_path.suffix.lower()
        is_code = suffix in (".py", ".ipynb")
        is_zip = suffix == ".zip"
        code = ""

        if suffix == ".ipynb":
            try:
                nb_data = json.loads(artifact_bytes.decode("utf-8", errors="replace"))
                code_blocks = []
                for cell in nb_data.get("cells", []):
                    if cell.get("cell_type") == "code":
                        source = "".join(cell.get("source", []))
                        clean_lines = []
                        for line in source.splitlines():
                            s = line.strip()
                            if s.startswith("!") or s.startswith("%"):
                                clean_lines.append(f"# [magic] {line}")
                            else:
                                clean_lines.append(line)
                        code_blocks.append("\n".join(clean_lines))
                code = "\n\n".join(code_blocks)
            except Exception as e:
                code = f"# Error reading notebook: {e}"
        elif is_zip:
            # For zip archives, extract and audit text/code files inside
            code_blocks = []
            try:
                with zipfile.ZipFile(artifact_path, "r") as zf:
                    for name in sorted(zf.namelist()):
                        if name.endswith(".py"):
                            code_blocks.append(zf.read(name).decode("utf-8", errors="replace"))
                        elif name.endswith((".yaml", ".yml", ".md", ".txt", ".json")):
                            text_content = zf.read(name).decode("utf-8", errors="replace")
                            # Add comments so security scan can check for authority key leaks
                            code_blocks.append(f"# {name}\n# {text_content[:200]}")
                code = (
                    "\n\n".join(code_blocks) if code_blocks else "# Empty or non-code zip archive"
                )
            except Exception as e:
                code = f"# Error reading zip: {e}"
        elif is_code:
            code = artifact_bytes.decode("utf-8", errors="replace")

        findings: list[IVVFinding] = []
        effective_verifier = self.verifier_id

        # Independence verification
        if request.creator_id == self.verifier_id:
            effective_verifier = f"{self.verifier_id}-anti-spoof"
            findings.append(
                IVVFinding(
                    gate="INDEPENDENCE_CHECK",
                    severity=IVVSeverity.P0_CRITICAL,
                    description=f"Creator ID matches verifier ID ('{request.creator_id}'). Independence spoofing detected.",
                    suggested_invariant="Verification must be performed by a distinct verifier identity.",
                )
            )

        test_files = self.discover_test_suite(request.competition)
        test_suite_hash = self.calculate_test_suite_hash(test_files)

        if is_code or is_zip:
            findings.extend(self.audit_ast_and_invariants(code))
        else:
            findings.extend(self.audit_tabular_and_data_artifacts(artifact_path, artifact_bytes))

        has_p0 = any(f.severity == IVVSeverity.P0_CRITICAL for f in findings)
        if not has_p0 and test_files:
            test_findings = self.execute_test_suite(test_files, artifact_path)
            findings.extend(test_findings)

        passed = not any(
            f.severity in (IVVSeverity.P0_CRITICAL, IVVSeverity.P1_HIGH) for f in findings
        )

        assertion = self.authority.sign_assertion(
            artifact_hash=artifact_hash,
            test_suite_hash=test_suite_hash,
            creator_id=request.creator_id,
            verifier_id=effective_verifier,
            competition=request.competition,
            passed=passed,
            findings=findings,
        )

        self.authority.save_assertion(assertion)
        self._persist_to_surrealdb(assertion)

        return assertion
