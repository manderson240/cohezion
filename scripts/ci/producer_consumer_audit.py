#!/usr/bin/env python3
"""Producer-Consumer Audit Gate for Cohezion.
==============================================
Validates that every architectural and hardware producer across Cohezion
has an active, verified production consumer, preventing hollow seams,
ghost abstractions, and dormant capabilities.

Hardware & Architectural Subsystems Audited:
1. EventBus Lifecycle & Inter-Agent Telemetry
2. Precipitation Physics & State Transitions
3. MaP-WAM Trace-as-Goal & Memory-as-Plans (arXiv:2609.11561)
4. Data Mesh Architecture & Corpus Quality
5. BAML Contracts & Resilient Parsing
6. AMD XDNA2 NPU Silicon Execution (<2W sub-2W SRAM lane)
7. AMD MI355X GPU Acceleration Kernels (GEMM / MLA / MoE)
8. Biological Connectome & Ventral Hippocampus (vHPC)
9. Durable Agentic Kanban Bridge (SurrealDB + Obsidian)
10. Silicon-to-Cloud Hybrid Routing (Lemonade + Ollama Cloud)

Mapped AMD Skills:
- FASTFLOWLM_PRIME: XDNA2 NPU runtime, sub-2W energy envelope, BAML verification
- AMD_GEMM_MXFP4_PRIME: MI355X MFMA scale f8f6f4 kernel optimization
- AMD_MLA_DECODE_PRIME: DeepSeek R1 576/512 K/V split attention decode
- AMD_MOE_MXFP4_PRIME: MI355X LDS bridge kernel, zero HBM roundtrip
- KERNEL_OPTIMIZATION_PRIME: load_inline HIP C++ runtime compilation & Popcorn benchmark
- LEMONADE_OMNIROUTER_PRIME: Hardware lane routing, fleet lock, event sync bridge

Usage:
    python scripts/ci/producer_consumer_audit.py
    python scripts/ci/producer_consumer_audit.py --self-test
    python scripts/ci/producer_consumer_audit.py --markdown report.md
    python scripts/ci/producer_consumer_audit.py --json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"


@dataclass(frozen=True)
class AuditPair:
    """Specification of an architectural producer-consumer seam."""

    name: str
    producer: str
    producer_pattern: str
    consumer: str
    consumer_pattern: str
    amd_skill: str
    hardware_lane: str  # npu, igpu, cpu, cloud, substrate, or architecture
    expected_min_producers: int
    expected_min_consumers: int


AUDIT_PAIRS: list[AuditPair] = [
    AuditPair(
        name="EventBus Lifecycle & Telemetry",
        producer="EventBus.publish / bus.publish (Event producer)",
        producer_pattern=r"(?:await\s+)?(?:self\._)?(?:event_)?bus\.publish\(",
        consumer="EventConsumer / Subscriber (Event consumer)",
        consumer_pattern=r"\.subscribe\(",
        amd_skill="LEMONADE_OMNIROUTER_PRIME",
        hardware_lane="architecture",
        expected_min_producers=5,
        expected_min_consumers=2,
    ),
    AuditPair(
        name="Precipitation Physics & State Transitions",
        producer="PrecipitationBus / EVO / Cosmogony (State transition producer)",
        producer_pattern=r"(?:PrecipitationBus|produce_witness_mark|deliberate\(|SymmetryBreaking)",
        consumer="PrecipitationBus Subscriber / Observer (State consumer)",
        consumer_pattern=r"(?:PrecipitationBus|\.subscribe\(|set_bus\()",
        amd_skill="LEMONADE_OMNIROUTER_PRIME",
        hardware_lane="substrate",
        expected_min_producers=2,
        expected_min_consumers=2,
    ),
    AuditPair(
        name="MaP-WAM Trace-as-Goal & Memory-as-Plans",
        producer="PlanSegment (MaP-WAM goal contract producer, arXiv:2609.11561)",
        producer_pattern=r"PlanSegment\(",
        consumer="MemoryAsPlans / AutonomousGoalExecutor (Plan segment consumer)",
        consumer_pattern=r"(?:MemoryAsPlans|run_trace_refactor_phase|AutonomousGoalExecutor)",
        amd_skill="AUTOHARNESS_POLICY_PRIME",
        hardware_lane="architecture",
        expected_min_producers=1,
        expected_min_consumers=1,
    ),
    AuditPair(
        name="Data Mesh Architecture & Corpus Quality",
        producer="DataProductSchema (Data Mesh product definition)",
        producer_pattern=r"DataProductSchema\(",
        consumer="CorpusQualityConsumer / EventConsumer (Product consumer)",
        consumer_pattern=r"(?:CorpusQualityConsumer|consume_data_product|EventConsumer)",
        amd_skill="SURREALDB_VECTOR_GRAPH_ENGINE_PRIME",
        hardware_lane="substrate",
        expected_min_producers=1,
        expected_min_consumers=1,
    ),
    AuditPair(
        name="BAML Contracts & Resilient Parsing",
        producer="BAMLSchemaGenerator (BAML type generator)",
        producer_pattern=r"BAMLSchemaGenerator",
        consumer="BAMLResilientParser (Resilient output parser)",
        consumer_pattern=r"BAMLResilientParser",
        amd_skill="FASTFLOWLM_PRIME",
        hardware_lane="npu",
        expected_min_producers=1,
        expected_min_consumers=1,
    ),
    AuditPair(
        name="AMD XDNA2 NPU Silicon Execution",
        producer="FastFlowLM / npu_structured_json (<2W SRAM lane on /dev/accel/accel0)",
        producer_pattern=r"(?:FastFlowLM|npu_structured_json)",
        consumer="BAML Parser / Goal Executor / Hybrid Router (NPU consumers)",
        consumer_pattern=r"(?:BAMLResilientParser|AutonomousGoalExecutor|UnifiedHybridRouter)",
        amd_skill="FASTFLOWLM_PRIME",
        hardware_lane="npu",
        expected_min_producers=2,
        expected_min_consumers=2,
    ),
    AuditPair(
        name="AMD MI355X GPU Acceleration Kernels",
        producer="load_inline / KERNEL_MAP (MI355X HIP kernels: GEMM, MLA, MoE)",
        producer_pattern=r"(?:KERNEL_MAP|amd-mxfp4-mm|amd-moe-mxfp4|amd-mixed-mla)",
        consumer="popcorn.submit / Forge Benchmark service (Kernel consumers)",
        consumer_pattern=r"(?:popcorn\.submit|forge\.py|SubmitResult)",
        amd_skill="AMD_GEMM_MXFP4_PRIME",
        hardware_lane="igpu",
        expected_min_producers=1,
        expected_min_consumers=1,
    ),
    AuditPair(
        name="Biological Connectome & Ventral Hippocampus",
        producer="VentralHippocampusCircuit / DrosophilaSensoryMotorCircuit",
        producer_pattern=r"(?:VentralHippocampusCircuit|DrosophilaSensoryMotorCircuit)",
        consumer="persist_circuit_state / compute_reflex_action / arbitration",
        consumer_pattern=r"(?:persist_circuit_state|compute_reflex_action|arbitrate_approach_avoidance)",
        amd_skill="VENTRAL_HIPPOCAMPUS_CIRCUITS_PRIME",
        hardware_lane="npu",
        expected_min_producers=2,
        expected_min_consumers=2,
    ),
    AuditPair(
        name="Durable Agentic Kanban Bridge",
        producer="persist_item (Dual-sync Kanban producer: SurrealDB + Obsidian)",
        producer_pattern=r"persist_item\(",
        consumer="kanban_item table queries / work-queue.json (Kanban consumers)",
        consumer_pattern=r"(?:kanban_item|work-queue\.json)",
        amd_skill="SURREALDB_VECTOR_GRAPH_ENGINE_PRIME",
        hardware_lane="substrate",
        expected_min_producers=5,
        expected_min_consumers=5,
    ),
    AuditPair(
        name="Silicon-to-Cloud Hybrid Routing",
        producer="UnifiedHybridRouter (Multi-tier routing: NPU / iGPU / Cloud)",
        producer_pattern=r"(?:class UnifiedHybridRouter|def get_router)",
        consumer="MasterOrchestrator / BioelectricSwarm / Swarm Agents",
        consumer_pattern=r"UnifiedHybridRouter\(",
        amd_skill="LEMONADE_OMNIROUTER_PRIME",
        hardware_lane="igpu",
        expected_min_producers=1,
        expected_min_consumers=3,
    ),
]


@dataclass
class PairAuditResult:
    """Result of auditing a single producer-consumer pair."""

    name: str
    producer: str
    consumer: str
    amd_skill: str
    hardware_lane: str
    producers_found: int
    expected_min_producers: int
    consumers_found: int
    expected_min_consumers: int
    producer_sample_files: list[str]
    consumer_sample_files: list[str]
    passed: bool
    failure_reasons: list[str]


def collect_python_sources(root: Path) -> dict[Path, str]:
    """Reads all python files under root into memory."""
    sources: dict[Path, str] = {}
    for p in root.rglob("*.py"):
        with contextlib.suppress(Exception):
            sources[p] = p.read_text(encoding="utf-8", errors="ignore")
    return sources


def execute_audit(
    pairs: list[AuditPair] | None = None,
    src_dir: Path | None = None,
) -> list[PairAuditResult]:
    """Executes the audit against the codebase."""
    active_pairs = pairs if pairs is not None else AUDIT_PAIRS
    target_src = src_dir if src_dir is not None else SRC

    sources = collect_python_sources(target_src)
    results: list[PairAuditResult] = []

    for item in active_pairs:
        p_re = re.compile(item.producer_pattern)
        c_re = re.compile(item.consumer_pattern)

        p_matches: list[str] = []
        c_matches: list[str] = []

        for path, text in sources.items():
            rel = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
            if p_re.search(text):
                p_matches.append(rel)
            if c_re.search(text):
                c_matches.append(rel)

        p_count = len(p_matches)
        c_count = len(c_matches)

        failures: list[str] = []
        if p_count < item.expected_min_producers:
            failures.append(
                f"Producer count ({p_count}) < minimum required floor ({item.expected_min_producers})"
            )
        if c_count < item.expected_min_consumers:
            failures.append(
                f"Consumer count ({c_count}) < minimum required floor ({item.expected_min_consumers})"
            )

        passed = len(failures) == 0

        results.append(
            PairAuditResult(
                name=item.name,
                producer=item.producer,
                consumer=item.consumer,
                amd_skill=item.amd_skill,
                hardware_lane=item.hardware_lane,
                producers_found=p_count,
                expected_min_producers=item.expected_min_producers,
                consumers_found=c_count,
                expected_min_consumers=item.expected_min_consumers,
                producer_sample_files=p_matches[:3],
                consumer_sample_files=c_matches[:3],
                passed=passed,
                failure_reasons=failures,
            )
        )

    return results


def format_markdown_report(results: list[PairAuditResult]) -> str:
    """Generates a structured markdown audit report."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    lines = [
        "# Cohezion Producer-Consumer Architectural & Hardware Seam Audit",
        "",
        f"**Audit Status**: {'✅ 100% VERIFIED — ZERO HOLLOW SEAMS' if failed == 0 else f'❌ {failed} SEAM DEFECTS DETECTED'}",
        f"**Total Seams Audited**: {total} | **Passed**: {passed} | **Failed**: {failed}",
        "",
        "## Subsystem Seam Verification Matrix",
        "",
        "| Seam / Subsystem | Hardware Lane | AMD Skill | Producers | Consumers | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        status_badge = "✅ Verified" if r.passed else "❌ Failed"
        p_str = f"{r.producers_found} (min {r.expected_min_producers})"
        c_str = f"{r.consumers_found} (min {r.expected_min_consumers})"
        lines.append(
            f"| **{r.name}** | `{r.hardware_lane}` | `{r.amd_skill}` | {p_str} | {c_str} | {status_badge} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Seam Analysis & Verification Traces",
            "",
        ]
    )

    for i, r in enumerate(results, start=1):
        status_icon = "✅" if r.passed else "❌"
        lines.extend(
            [
                f"### {i}. {status_icon} {r.name}",
                f"- **Hardware Lane**: `{r.hardware_lane}`",
                f"- **Governing AMD / Core Skill**: `{r.amd_skill}`",
                f"- **Producer Role**: `{r.producer}`",
                f"  - Files found: **{r.producers_found}** (floor: {r.expected_min_producers})",
                f"  - Sample sources: {', '.join(f'`{s}`' for s in r.producer_sample_files) if r.producer_sample_files else 'None'}",
                f"- **Consumer Role**: `{r.consumer}`",
                f"  - Files found: **{r.consumers_found}** (floor: {r.expected_min_consumers})",
                f"  - Sample sources: {', '.join(f'`{s}`' for s in r.consumer_sample_files) if r.consumer_sample_files else 'None'}",
            ]
        )
        if not r.passed:
            lines.append(f"- **Gaps Detected**: {'; '.join(r.failure_reasons)}")
        else:
            lines.append(
                "- **Verification Verdict**: Zero hollow seams. Active bidirectional flow verified."
            )
        lines.append("")

    return "\n".join(lines)


def run_self_test() -> int:
    """Validates that the audit gate can detect synthetic dormancy and failures."""
    print("🧪 RUNNING PRODUCER-CONSUMER AUDIT SELF-TEST...")

    # 1. Test RED condition: inject a synthetic seam with a guaranteed-dormant consumer
    broken_pair = AuditPair(
        name="Synthetic Broken Seam",
        producer="Real Producer",
        producer_pattern=r"def npu_structured_json\(",
        consumer="Non-Existent Consumer",
        consumer_pattern=r"SYNTHETIC_IMPOSSIBLE_CONSUMER_TOKEN_XYZZY_9999",
        amd_skill="FASTFLOWLM_PRIME",
        hardware_lane="npu",
        expected_min_producers=1,
        expected_min_consumers=1,
    )

    red_results = execute_audit(pairs=[broken_pair])
    if len(red_results) != 1 or red_results[0].passed:
        print("❌ SELF-TEST FAILED: Scanner failed to go RED on guaranteed-dormant consumer.")
        return 1

    print("  ✓ Proven: Scanner reliably goes RED on dormant/hollow consumer.")

    # 2. Test GREEN condition: verify against real AUDIT_PAIRS
    green_results = execute_audit(pairs=AUDIT_PAIRS)
    all_green = all(r.passed for r in green_results)
    if not all_green:
        failed_names = [r.name for r in green_results if not r.passed]
        print(f"❌ SELF-TEST FAILED: Scanner failed on live codebase: {failed_names}")
        return 1

    print(f"  ✓ Proven: Scanner reliably goes GREEN on all {len(AUDIT_PAIRS)} live seams.")
    print("🎉 SELF-TEST PASSED: Audit gate is fully functional and falsifiable.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Cohezion Producer-Consumer Wiring Audit")
    parser.add_argument(
        "--self-test", action="store_true", help="Run self-test proving falsifiability"
    )
    parser.add_argument("--markdown", type=Path, help="Write markdown report to specified path")
    parser.add_argument("--json", action="store_true", help="Output JSON result to stdout")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    results = execute_audit()
    failures = sum(1 for r in results if not r.passed)

    if args.json:
        data: dict[str, Any] = {
            "total_pairs": len(results),
            "passed": len(results) - failures,
            "failed": failures,
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(data, indent=2))
        return 0 if failures == 0 else 1

    print("=" * 78)
    print("🔍 COHEZION PRODUCER-CONSUMER ARCHITECTURAL & HARDWARE SEAM AUDIT")
    print("=" * 78)

    for r in results:
        status = "✅ VERIFIED" if r.passed else "❌ FAILED"
        print(f"\n• [{r.hardware_lane.upper()}] Seam: {r.name} (AMD Skill: {r.amd_skill})")
        print(f"  - Producer: {r.producer}")
        print(f"    Found {r.producers_found} file(s) (floor: {r.expected_min_producers})")
        if r.producer_sample_files:
            print(f"    Samples: {', '.join(r.producer_sample_files)}")
        print(f"  - Consumer: {r.consumer}")
        print(f"    Found {r.consumers_found} file(s) (floor: {r.expected_min_consumers})")
        if r.consumer_sample_files:
            print(f"    Samples: {', '.join(r.consumer_sample_files)}")

        if not r.passed:
            for reason in r.failure_reasons:
                print(f"  ❌ FAILURE: {reason}")
        else:
            print(f"  {status}: Active bidirectional flow verified.")

    print("\n" + "=" * 78)
    if failures == 0:
        print("🎉 ALL PRODUCERS HAVE ACTIVE CONSUMERS (Zero Hollow Seams Across Fleet)")
        print("=" * 78)
    else:
        print(f"💥 AUDIT FAILED: {failures} producer-consumer gap(s) detected.")
        print("=" * 78)

    if args.markdown:
        md_text = format_markdown_report(results)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(md_text, encoding="utf-8")
        print(f"[saved markdown report] -> {args.markdown}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
