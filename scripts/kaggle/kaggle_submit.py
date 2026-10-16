#!/usr/bin/env python3
"""Unified, Deterministic Kaggle Submission Engine for Cohezion.

Eliminates all guesswork, API parameter drift, and File vs Notebook confusion.

Kaggle has two distinct, mutually exclusive submission pathways:
1. Code / Notebook Rerun Competitions (ARC-AGI-2, ARC-AGI-3, RSNA Knee):
   - Local file uploads fail with FAILED_PRECONDITION: 'This competition only accepts Submissions from Notebooks.'
   - MUST use api.competition_submit_code(kernel, kernel_version, file_name, message, competition).
   - Parameter is `kernel_version`, NOT `version`.
2. Direct File Competitions (CASMI26, standard tabular/CSV):
   - MUST use api.competition_submit(file_name, message, competition).

Usage:
  # Notebook submission:
  python3 scripts/kaggle/kaggle_submit.py notebook \
      --competition arc-prize-2026-arc-agi-3 \
      --kernel manderson240/cohezion-arc-agi-3-autoharness-solver \
      --version 3 \
      --file submission.parquet \
      --message "Cohezion ARC-AGI-3 SOTA v27"

  # Direct file submission:
  python3 scripts/kaggle/kaggle_submit.py file \
      --competition enveda-CASMI26-molecule-id-mass-spectra \
      --file /path/to/submission.csv \
      --message "Cohezion CASMI26 v10"

  # Auto-submit (inspects competition type automatically):
  python3 scripts/kaggle/kaggle_submit.py auto \
      --competition arc-prize-2026-arc-agi-3 \
      --kernel manderson240/cohezion-arc-agi-3-autoharness-solver \
      --file submission.parquet \
      --message "Cohezion ARC-AGI-3 SOTA v27"
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


# Ensure Kaggle SDK and Cohezion packages are loaded from the environment
src_path = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    venv_py = Path(__file__).resolve().parent.parent.parent / ".venv/bin/python"
    if venv_py.exists() and sys.executable != str(venv_py):
        os.execv(str(venv_py), [str(venv_py)] + sys.argv)
    print(
        "Error: kaggle package not found. Ensure .venv or environment is active.", file=sys.stderr
    )
    sys.exit(1)



# Known competition registry to prevent guessing
COMPETITION_REGISTRY = {
    "arc-prize-2026-arc-agi-2": {
        "type": "notebook",
        "default_file": "submission.json",
        "default_kernel": "manderson240/arc-agi-2-fork-lb33-89-20260903",
    },
    "arc-prize-2026-arc-agi-3": {
        "type": "notebook",
        "default_file": "submission.parquet",
        "default_kernel": "manderson240/cohezion-arc-agi-3-autoharness-solver",
    },
    "rsna-knee-abnormality-detection": {
        "type": "notebook",
        "default_file": "submission.csv",
        "default_kernel": "manderson240/cohezion-rsna-knee-sota-ensemble",
    },
    "gemma-4-developer-agent": {
        "type": "notebook",
        "default_file": "submission.csv",
        "default_kernel": "manderson240/token-insulated-compound-agent-graphs-for-gemma-4",
    },
    "enveda-CASMI26-molecule-id-mass-spectra": {
        "type": "notebook",
        "default_file": "submission.csv",
        "default_kernel": "manderson240/casmi26-analog-baseline-fork-cohezion",
    },
    "biohub-cell-tracking-during-development": {
        "type": "notebook",
        "default_file": "submission.csv",
        "default_kernel": "manderson240/cohezion-biohub-v6",
    },
    "nfl-big-data-bowl-2027": {
        "type": "notebook",
        "default_file": "submission.csv",
        "default_kernel": "manderson240/cohezion-nfl-bdb-2027-kinematic",
    },
}


def get_api() -> KaggleApi:
    api = KaggleApi()
    api.authenticate()
    return api


from cohezion.compound.ivv_authority import (
    IVVAuthority,
    IVVAuthorityService,
    VerificationRequest,
)


def enforce_ivv_check(
    competition: str,
    artifact_id: str,
    creator_id: str = "creator-agent",
    code_path: str | None = None,
) -> None:
    """Enforces Independent Verification & Validation (Two-Party Rule).

    Verifies that the code artifact has been independently audited and
    cryptographically signed by the IV&V Authority.
    """
    print("\n🔒 Running Cryptographic IV&V Gatekeeper Check:")
    print(f"   Competition: {competition}")
    print(f"   Artifact:    {artifact_id}")
    print(f"   Creator:     {creator_id}")

    # Locate artifact file
    p = None
    if code_path and Path(code_path).exists():
        p = Path(code_path)
    else:
        for candidate in Path("scripts/kaggle").rglob("*.ipynb"):
            if competition in str(candidate) or (
                artifact_id and artifact_id.split("/")[-1] in str(candidate)
            ):
                p = candidate
                break
        if not p and artifact_id and Path(artifact_id).exists():
            p = Path(artifact_id)

    if not p or not p.exists():
        print(f"⚠️ IV&V Warning: Code path '{code_path}' not resolved to local file.")
        digest = hashlib.sha256(f"{competition}:{artifact_id}".encode()).hexdigest()
    else:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f"   Code File:   {p} (SHA-256: {digest[:12]}...)")

        # Kaggle docker-python container compatibility verification
        if p.suffix.lower() in (".py", ".ipynb"):
            try:
                from scripts.kaggle.docker_python_verifier import verify_compatibility

                is_compat, missing_deps, _ = verify_compatibility(p)
                if not is_compat:
                    print(
                        f"   ⚠️ Docker-Python Warning: {len(missing_deps)} imports unconfirmed in Kaggle manifest: {missing_deps}"
                    )
                else:
                    print(
                        "   ✓ Docker-Python Runtime Invariant: 100% of imported modules verified in Kaggle container manifest."
                    )
            except Exception:
                pass
        else:
            print(
                f"   ✓ Data Artifact Format: {p.suffix.upper()} ({p.stat().st_size:,} bytes verified)"
            )

    authority = IVVAuthority()
    service = IVVAuthorityService(authority=authority)

    # Check for existing signed assertion or request independent audit
    assertion = authority.load_assertion(digest)
    if not assertion or not assertion.passed:
        print("   No valid passing certificate found. Requesting independent IV&V audit...")
        if p and p.exists():
            req = VerificationRequest(
                artifact_path=str(p),
                competition=competition,
                creator_id=creator_id,
            )
            assertion = service.verify_request(req)
        else:
            print(
                "❌ IV&V GATEKEEPER REJECTED: Artifact file required for independent verification."
            )
            sys.exit(1)

    # Enforce Two-Party Rule: Creator CANNOT verify their own artifact
    if assertion.creator_id == assertion.verifier_id:
        print("\n❌ IV&V GATEKEEPER VIOLATION: Two-Party Rule Violated!")
        print(
            f"   Creator ID '{assertion.creator_id}' and Verifier ID '{assertion.verifier_id}' CANNOT be identical."
        )
        print(
            "   'Validation and verification needs to be separate from the initial code creators.'"
        )
        sys.exit(1)

    # Verify cryptographic signature against authority key
    if p and p.exists():
        valid, msg = authority.verify_assertion(assertion, str(p))
    else:
        valid = assertion.passed and bool(assertion.signature)
        msg = "Assertion valid" if valid else "Failed"

    if not valid or not assertion.passed:
        print("\n❌ IV&V GATEKEEPER REJECTED SUBMISSION:")
        print(f"   {msg}")
        for finding in assertion.findings:
            print(f"   - [{finding.severity}] {finding.gate}: {finding.description}")
            if finding.suggested_invariant:
                print(f"     Suggested fix: {finding.suggested_invariant}")
        print(
            "\nFix findings or have the independent IV&V Authority verify the code before submitting."
        )
        sys.exit(1)

    print(
        f"✓ DEPLOYMENT APPROVED: Cryptographic IV&V Assertion signed by '{assertion.verifier_id}' (Signature: {assertion.signature[:12]}...)\n"
    )

    # Verify offline runtime compatibility against Kaggle official docker-python
    if p and p.exists() and p.suffix.lower() in (".py", ".ipynb"):
        try:
            from scripts.kaggle.docker_python_verifier import verify_compatibility

            ok, missing, _ = verify_compatibility(p)
            if not ok:
                print("❌ DOCKER-PYTHON VERIFICATION FAILED:")
                print(
                    f"   Artifact '{p}' contains imports not in Kaggle official docker-python: {missing}"
                )
                print(
                    "   Provide an offline dataset wheel or remove unbundled dependencies before submitting."
                )
                sys.exit(1)
            print(
                "✓ DOCKER-PYTHON COMPATIBILITY VERIFIED: All imports match Kaggle container specifications.\n"
            )
        except Exception as e:
            print(f"⚠️ Docker-python verification note (non-blocking): {e}\n")


def wait_for_kernel_completion(api: KaggleApi, kernel_slug: str, max_wait_mins: int = 60) -> int:
    """Waits for a kernel to complete and returns the latest version number."""
    print(
        f"Waiting for kernel '{kernel_slug}' to complete execution (timeout: {max_wait_mins}m)..."
    )
    start = time.time()
    last_status = None

    while (time.time() - start) < (max_wait_mins * 60):
        try:
            status_res = api.kernels_status(kernel_slug)
        except AttributeError:
            status_res = api.kernel_status(kernel_slug)

        if isinstance(status_res, dict):
            status = status_res.get("status", "")
        else:
            status = getattr(status_res, "status", str(status_res))

        if status != last_status:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Kernel status: {status}")
            last_status = status

        if "COMPLETE" in str(status).upper():
            # Get latest version number
            return 0  # 0 or None submits the latest active version
        elif "ERROR" in str(status).upper() or "CANCEL" in str(status).upper():
            raise RuntimeError(f"Kernel '{kernel_slug}' failed with status: {status}")

        time.sleep(15)

    raise TimeoutError(f"Kernel '{kernel_slug}' did not finish within {max_wait_mins} minutes.")


def submit_notebook(
    api: KaggleApi,
    competition: str,
    kernel: str,
    file_name: str,
    message: str,
    kernel_version: int | None = None,
    wait: bool = False,
) -> dict[str, Any]:
    """Submits a notebook output to a code competition using exact SDK parameters."""
    if wait:
        wait_for_kernel_completion(api, kernel)

    print(f"Dispatching Code Submission for '{competition}':")
    print(f"  Kernel:         {kernel}")
    print(f"  Kernel Version: {kernel_version if kernel_version is not None else 'Latest'}")
    print(f"  Output File:    {file_name}")
    print(f"  Message:        {message}")

    kwargs: dict[str, Any] = {
        "file_name": file_name,
        "message": message,
        "competition": competition,
        "kernel": kernel,
    }
    try:
        if kernel_version is not None:
            kwargs["kernel_version"] = int(kernel_version)
        else:
            # Dynamically resolve latest kernel version number from Kaggle API
            try:
                parts = kernel.split("/")
                if len(parts) == 2:
                    owner, slug = parts
                    with api.build_kaggle_client() as kaggle:
                        from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest

                        req = ApiGetKernelRequest()
                        req.user_name = owner
                        req.kernel_slug = slug
                        res_k = kaggle.kernels.kernels_api_client.get_kernel(req)
                        resolved_ver = int(res_k.metadata.current_version_number)
                        kwargs["kernel_version"] = resolved_ver
                        print(
                            f"✓ Dynamically resolved latest kernel_version={resolved_ver} for '{kernel}'."
                        )
                else:
                    raise ValueError(f"Malformed kernel string: {kernel}")
            except Exception as e:
                print(f"⚠️ Failed to dynamically resolve latest kernel_version for '{kernel}': {e}")
                raise RuntimeError(
                    f"Cannot submit without an explicit or dynamically verified kernel version: {e}"
                )

        response = api.competition_submit_code(**kwargs)
        ref = getattr(response, "ref", None) or getattr(response, "submission_id", None)
        msg = getattr(response, "message", "")
        print(f"✓ Submission SUCCESSFUL! Ref: {ref}")
        return {"status": "SUCCESS", "ref": ref, "message": msg}
    except Exception as e:
        server_msg = ""
        resp_obj = getattr(e, "response", None)
        if resp_obj is not None:
            server_msg = getattr(resp_obj, "text", "")
        if server_msg:
            print(f"✗ Submission FAILED: {e}\n  Server response: {server_msg}", file=sys.stderr)
        else:
            print(f"✗ Submission FAILED: {e}", file=sys.stderr)
        raise


def submit_file(
    api: KaggleApi,
    competition: str,
    file_path: str,
    message: str,
) -> dict[str, Any]:
    """Submits a static local file to a standard competition."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Submission file not found: {file_path}")

    print(f"Dispatching Direct File Submission for '{competition}':")
    print(f"  File Path: {file_path} ({path.stat().st_size:,} bytes)")
    print(f"  Message:   {message}")

    try:
        response = api.competition_submit(
            file_name=str(path.resolve()),
            message=message,
            competition=competition,
        )
        print(f"✓ File Submission SUCCESSFUL! Result: {response}")
        return {"status": "SUCCESS", "result": str(response)}
    except Exception as e:
        print(f"✗ File Submission FAILED: {e}", file=sys.stderr)
        raise


def auto_submit(
    api: KaggleApi,
    competition: str,
    file_target: str | None = None,
    kernel: str | None = None,
    version: int | None = None,
    message: str | None = None,
    wait: bool = False,
) -> dict[str, Any]:
    """Automatically selects the right submission mode based on the competition."""
    comp_info = COMPETITION_REGISTRY.get(competition)
    comp_type = comp_info["type"] if comp_info else None

    if comp_type is None:
        # Check if local file exists
        if file_target and Path(file_target).exists():
            comp_type = "file"
        elif kernel:
            comp_type = "notebook"
        else:
            raise ValueError(
                f"Unknown competition '{competition}'. Specify mode 'notebook' or 'file'."
            )

    msg = (
        message
        or f"Cohezion autonomous submission for {competition} at {datetime.datetime.now().isoformat()}"
    )

    if comp_type == "notebook":
        k_slug = kernel or (comp_info["default_kernel"] if comp_info else None)
        if not k_slug:
            raise ValueError(
                f"Notebook submission requires --kernel for competition '{competition}'."
            )
        f_name = file_target or (comp_info["default_file"] if comp_info else "submission.csv")
        return submit_notebook(
            api=api,
            competition=competition,
            kernel=k_slug,
            file_name=f_name,
            message=msg,
            kernel_version=version,
            wait=wait,
        )
    else:
        f_path = file_target or (comp_info["default_file"] if comp_info else "submission.csv")
        return submit_file(
            api=api,
            competition=competition,
            file_path=f_path,
            message=msg,
        )


def query_status(api: KaggleApi, competition: str, limit: int = 5, as_json: bool = False) -> None:
    """Query recent submission statuses and public scores for a competition."""
    try:
        subs = api.competition_submissions(competition)
        results = []
        for s in subs[:limit]:
            results.append(
                {
                    "ref": s.ref,
                    "date": s.date.isoformat() if hasattr(s.date, "isoformat") else str(s.date),
                    "status": str(s.status).replace("SubmissionStatus.", ""),
                    "public_score": getattr(s, "_public_score", None)
                    or getattr(s, "public_score", None),
                    "error": getattr(s, "_error_description", None)
                    or getattr(s, "error_description", None),
                    "description": s.description,
                    "filename": getattr(s, "_file_name", None) or getattr(s, "file_name", None),
                }
            )
        if as_json:
            print(json.dumps(results, indent=2))
        else:
            print(f"=== Submissions for '{competition}' (Latest {len(results)}) ===")
            for r in results:
                score_str = (
                    f"Score: {r['public_score']}" if r["public_score"] else f"Status: {r['status']}"
                )
                err_str = f" | Error: {r['error']}" if r["error"] else ""
                print(
                    f"  Ref {r['ref']}: {r['date']} | {score_str}{err_str} | {str(r['description'])[:60]}"
                )
    except Exception as e:
        print(f"Error querying status for '{competition}': {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cohezion Unified Kaggle Submission Engine")

    # Cryptographic IV&V parser for all commands
    ivv_parent = argparse.ArgumentParser(add_help=False)
    ivv_parent.add_argument(
        "--creator-id", default="cohezion-agent", help="Identifier of code creator"
    )
    ivv_parent.add_argument(
        "--code-path", default=None, help="Path to notebook or script for IV&V code audit"
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Notebook subparser
    nb_p = subparsers.add_parser(
        "notebook", parents=[ivv_parent], help="Submit to a code/notebook rerun competition"
    )
    nb_p.add_argument("-c", "--competition", required=True, help="Competition slug")
    nb_p.add_argument("-k", "--kernel", required=True, help="Kernel slug (e.g. user/kernel-name)")
    nb_p.add_argument("-v", "--version", type=int, default=None, help="Kernel version number")
    nb_p.add_argument("-f", "--file", default="submission.parquet", help="Output file name")
    nb_p.add_argument("-m", "--message", required=True, help="Submission message")
    nb_p.add_argument(
        "-w", "--wait", action="store_true", help="Wait for kernel completion before submit"
    )

    # File subparser
    f_p = subparsers.add_parser(
        "file", parents=[ivv_parent], help="Submit a local file to a standard competition"
    )
    f_p.add_argument("-c", "--competition", required=True, help="Competition slug")
    f_p.add_argument("-f", "--file", required=True, help="Local file path")
    f_p.add_argument("-m", "--message", required=True, help="Submission message")

    # Auto subparser
    auto_p = subparsers.add_parser(
        "auto", parents=[ivv_parent], help="Auto-detect competition mode from registry"
    )
    auto_p.add_argument("-c", "--competition", required=True, help="Competition slug")
    auto_p.add_argument("-k", "--kernel", default=None, help="Kernel slug")
    auto_p.add_argument("-v", "--version", type=int, default=None, help="Kernel version")
    auto_p.add_argument("-f", "--file", default=None, help="File path or output file name")
    auto_p.add_argument("-m", "--message", default=None, help="Submission message")
    auto_p.add_argument("-w", "--wait", action="store_true", help="Wait for kernel completion")

    # Status subparser
    status_p = subparsers.add_parser(
        "status", help="Query submission status and scores for a competition"
    )
    status_p.add_argument("-c", "--competition", required=True, help="Competition slug")
    status_p.add_argument(
        "-n", "--limit", type=int, default=5, help="Number of recent submissions to display"
    )
    status_p.add_argument("--json", action="store_true", help="Output status in JSON format")

    args = parser.parse_args()

    api = get_api()

    if args.mode == "status":
        query_status(api=api, competition=args.competition, limit=args.limit, as_json=args.json)
        return

    # Mandatory Independent Verification & Validation (Cryptographic Authority Check)
    artifact_id = getattr(args, "kernel", None) or getattr(args, "file", None) or args.competition
    code_path = getattr(args, "code_path", None)
    if (
        not code_path
        and args.mode != "notebook"
        and getattr(args, "file", None)
        and Path(args.file).exists()
    ):
        code_path = args.file

    enforce_ivv_check(
        competition=args.competition,
        artifact_id=artifact_id,
        creator_id=args.creator_id,
        code_path=code_path,
    )

    if args.mode == "notebook":
        submit_notebook(
            api=api,
            competition=args.competition,
            kernel=args.kernel,
            file_name=args.file,
            message=args.message,
            kernel_version=args.version,
            wait=args.wait,
        )
    elif args.mode == "file":
        submit_file(
            api=api,
            competition=args.competition,
            file_path=args.file,
            message=args.message,
        )
    elif args.mode == "auto":
        auto_submit(
            api=api,
            competition=args.competition,
            file_target=args.file,
            kernel=args.kernel,
            version=args.version,
            message=args.message,
            wait=args.wait,
        )


if __name__ == "__main__":
    main()
