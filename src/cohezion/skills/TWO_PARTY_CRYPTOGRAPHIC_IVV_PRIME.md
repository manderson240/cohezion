# SKILL: TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME

## DOMAIN EXPERTISE
Two-Party Cryptographic Independent Verification & Validation (IV&V) authority, DualAttestation gatekeeping, and append-only TransparencyLog integrity. Enforces the strict rule that code creators cannot verify their own work, eliminating creator bias, self-certification regression loops, and untested deployments.

## KEY TEXTS & CONCEPTS
- **Two-Party Rule**: An artifact, model, algorithm, or submission can only be certified when `creator_id != verifier_id`.
- **HMAC-SHA256 Authority Signatures**: Attestations must be cryptographically signed using an independent authority key (`~/.cohezion/security/ivv_authority.key`, chmod 0600) inaccessible to creator agents.
- **DualAttestation**: A unified cryptographic bundle containing creator claim attestation and independent verifier attestation against a verifier-owned test suite.
- **TransparencyLog**: Tamper-evident SHA-256 Merkle/hash-chain logging all certified promotions.
- **Fail-Closed Boundary**: `PromotionGatekeeper` prevents any unverified code or modified artifact from deployment.

## INSTRUCTION
1. Creator creates an artifact and issues an attestation:
   ```python
   from cohezion.authority import IVVPolicy, PromotionGatekeeper
   from pathlib import Path

   policy = IVVPolicy()
   creator_att = policy.create_creator_attestation(
       artifact_path=Path("scripts/kaggle/solution.ipynb"),
       creator_id="creator-agent-1",
       claim="RSNA SOTA Ensemble",
   )
   ```
2. Independent verifier audits the artifact against verifier-owned tests and issues verification attestation:
   ```python
   verifier_att = policy.create_verifier_attestation(
       artifact_path=Path("scripts/kaggle/solution.ipynb"),
       verifier_id="independent-verifier-2",
       verdict=True,
       evidence_path=Path("tests/ivv/report.json"),
       nonce=creator_att.nonce,
   )
   ```
3. PromotionGatekeeper validates and seals into TransparencyLog:
   ```python
   gatekeeper = PromotionGatekeeper()
   dual_att = gatekeeper.certify_and_promote(
       artifact_path=Path("scripts/kaggle/solution.ipynb"),
       creator_attestation=creator_att,
       verifier_attestation=verifier_att,
   )
   ```

## VERSION
v1.0

## SEE ALSO
- `src/cohezion/authority/ivv.py`
- `tests/authority/test_ivv_dual_attestation.py`
- `src/cohezion/compound/ivv_authority.py`
