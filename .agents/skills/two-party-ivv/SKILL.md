---
name: two-party-ivv
description: Independent Verification and Validation (IV&V) protocol. Enforces physical, algorithmic, and cryptographic separation between code creators and verifiers, executes verifier-owned adversarial test suites in tests/ivv/, and generates tamper-proof HMAC-SHA256 assertion certificates required before any Kaggle submission or production merge.
---

# Two-Party Independent Verification & Validation (IV&V)

## Purpose
Enforces the strict **Two-Party Rule** mandated across Cohezion: **Code creators are strictly prohibited from self-certifying their own code.** All candidate solutions must pass independent, verifier-owned adversarial testing in `tests/ivv/` and receive a cryptographically signed HMAC-SHA256 assertion before deployment.

---

## The Core Invariants

1. **Physical & Identity Separation**:
   - `creator_id` $\ne$ `verifier_id`.
   - Creators only submit verification requests; verifiers own the test suites, execution environment, and signing key.

2. **Tamper-Proof Test Manifest**:
   - The verifier test suite (`tests/ivv/`) is hashed deterministically (`compute_suite_hash()`).
   - If tests are modified or skipped, the suite hash changes and assertions become invalid.

3. **Algorithmic Invariants by Domain**:
   - **ARC-AGI**: Neural `attempt_1` is immutable. DSL heuristics are strictly quarantined to `attempt_2`. Small-sample overfit trap ($N_{\text{train}} \le 2$) is blocked.
   - **RSNA Knee**: Kolmogorov Monotonicity $P(\text{Abnormal}) \ge \max_k P_k$ must hold across 100% of rows.
   - **CASMI26**: Mass window uses flat-top filter ($w_{\text{ppm}} = 0.0$ inside 10 ppm). InChIKey slot canonicalization via RDKit `canonical_ik14` is mandatory.

---

## Verification Commands & Protocol

### 1. Requesting Verification on an Artifact
From any creator agent or session:
```python
from cohezion.compound.ivv_authority import VerificationRequest, IVVAuthorityService

service = IVVAuthorityService()
request = VerificationRequest(
    artifact_path="scripts/kaggle/casmi26_kernel/casmi26-analog-baseline-fork-cohezion.ipynb",
    competition="enveda-CASMI26-molecule-id-mass-spectra",
    creator_id="casmi26-pipeline-engineer",
)
assertion = service.audit_and_sign(request)
if not assertion.passed:
    print(f"FAILED: {assertion.findings}")
else:
    print(f"PASSED: Signature={assertion.signature}")
```

### 2. CLI Audit via Python Test Suite
Run the verifier-owned adversarial test suite:
```bash
.venv/bin/pytest tests/unit/test_ivv_authority.py tests/ivv/ -v
```

### 3. Submission Gatekeeping
When submitting via `scripts/kaggle/kaggle_submit.py`:
- The gatekeeper automatically recalculates the artifact SHA256 and test suite hash.
- It queries `IVVAuthorityService` and validates the HMAC-SHA256 signature using `~/.cohezion/security/ivv_authority.key` (POSIX 0600).
- If unverified, the submission is rejected with a fail-closed exit code.
