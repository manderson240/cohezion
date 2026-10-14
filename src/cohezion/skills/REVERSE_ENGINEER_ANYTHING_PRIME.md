# SKILL: REVERSE_ENGINEER_ANYTHING_PRIME

## DOMAIN EXPERTISE
Investigating, decompiling, and dissecting shipped software artifacts, compiled binary layouts (ELF/Mach-O/PE), Python wheels, serialized model weights, and runtime bytecode without source code access using canonical Evidence records, progressive Unknown Ledgers, and prompt-injection-safe provenance boundaries in accordance with morluto/rea.

## KEY TEXTS & CONCEPTS
- **morluto/rea**: *Reverse Engineer Anything with Agents* (GitHub: morluto/rea, 2026).
- **Canonical Evidence Algebra**: Every inspection produces an immutable, content-addressed Evidence record with normalized semantics, raw upstream artifacts, and provenance markers.
- **Facet Availability**: Explicit declaration (`available: true` vs `available: false, reason: "..."`) that mathematically separates *observed absence* from *unsupported engine capability*.
- **The Unknown Ledger**: Progressive tracking of unanswered reverse engineering questions and hypothesis resolution ($\mathcal{U}_t \to \mathcal{U}_{t+1}$).
- **Target-Content Provenance**: Untrusted disassembly, extracted strings, and decompiled code are tagged with `untrusted_content: true` to prevent indirect prompt injection.
- **Session-Retained Paged Projections (`inspect_analysis_view`)**: Bounding serialized responses to fit within transport buffers via continuation pointers (`next_offset`).

## INSTRUCTION

### 1. Initialize an Analysis Session and Unknown Ledger
When tasked with investigating an unknown artifact or competitor pipeline:

```python
from cohezion.reverse_engineering import (
    AnalysisSession,
    ArtifactInspector,
    UnknownStatus,
)

session = AnalysisSession(session_id="kaggle_kernel_investigation")

# Record initial unknown hypothesis
unknown_item = session.unknown_ledger.record_unknown(
    domain="kaggle_weights",
    question="What backbone architecture and input resolution does the competitor checkpoint use?",
)
```

### 2. Inspect Artifacts and Capture Canonical Evidence
Inspect binary headers, Python distribution wheels, or compiled bytecode:

```python
# Inspect an offline Kaggle wheel
wheel_evidence = ArtifactInspector.inspect_python_wheel("dist/kaggle_wheels/cohezion_physics_core-0.1.0-cp313-cp313-linux_x86_64.whl")
session.record_evidence(wheel_evidence)

# Inspect binary layout
bin_evidence = ArtifactInspector.inspect_binary_layout("/usr/bin/python3")
session.record_evidence(bin_evidence)

# Inspect Python source/bytecode AST
code_evidence = ArtifactInspector.inspect_python_bytecode("def solve(x): return x * 2")
session.record_evidence(code_evidence)
```

### 3. Project Budget-Bounded Views and Resolve Unknowns
Query specific facets with offset/limit paging to avoid context bloat:

```python
# Page through discovered files or functions
page = session.inspect_analysis_view(
    evidence_id=wheel_evidence.evidence_id,
    facet="files",
    offset=0,
    limit=10,
)
print(f"Discovered {page.total_items} files. Next offset: {page.next_offset}")

# Resolve the tracked unknown with empirical proof
session.unknown_ledger.resolve_unknown(
    unknown_id=unknown_item.unknown_id,
    resolution="Wheel contains compiled native extension with 14 exported Rayon/PyO3 symbols",
    evidence_id=wheel_evidence.evidence_id,
)
```

## VERSION
v0.1

## SEE ALSO
- `STATELESS_LANGUAGE_AGENTS_PRIME`
- `AUTOHARNESS_ZERO_LATENCY_INVARIANT_COMPILER_PRIME`
- `TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME`
- `HARNESS_ENGINEERING_ETCLOVG_PRIME`
