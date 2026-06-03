---
name: self-healing
description: Self-healing AI system patterns for detecting performance drift,
  diagnosing failures, and applying autonomous corrections. Use when setting up
  health monitoring, implementing auto-recovery, or when user mentions "self
  healing", "drift detection", "auto correction", "health check", or
  "autonomous recovery".
metadata:
  version: "0.1"
  legacy-name: SELF_HEALING_PRIME
---

# SKILL: SELF_HEALING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **self-healing AI systems** - detecting performance drift, diagnosing failures, and applying autonomous corrections.

## KEY TEXTS & CONCEPTS
- **Drift Detection** – Monitor metrics against baselines
- **LLM-based Diagnosis** – Use language models to analyze failures
- **Autonomous Correction** – Auto-apply fixes for known issues
- **Unicron** – Self-healing LLM training framework (HuggingFace)
- **H-LLM** – Self-healing ML framework (arxiv)

## INSTRUCTION

### 1. Drift Detection
```python
from cohezion.healing import get_healing_system

system = get_healing_system()
system.detector.set_baseline("swarm", "latency", 100.0)

status = system.detector.check("swarm", "latency", 150.0)
if status.status != "healthy":
    print(f"Drift detected: {status}")
```

### 2. Diagnosis
```python
diagnosis = system.diagnostician.diagnose(status)
print(f"Issue: {diagnosis.issue}")
print(f"Cause: {diagnosis.probable_cause}")
print(f"Action: {diagnosis.recommended_action}")
```

### 3. Auto-Correction
```python
await system.corrector.apply_correction(diagnosis)
```

### 4. Full Health Check
```python
issues = await system.health_check()
healed = await system.heal(issues)
print(f"Healed {healed} issues")
```

### 5. Autonomous Patching with Rollback Safety
Always wrap non-deterministic code modifications in a backup-restore harness to prevent verification failures (e.g. pytest errors or crashes) from leaving the codebase in a broken state:
```python
backup_path = Path(file_path).with_suffix(".bak")
# 1. Back up original file state
original_content = Path(file_path).read_text()
Path(backup_path).write_text(original_content)

# 2. Apply modifications and verify
success = verify_via_tests()

# 3. Roll back on failure, or clean up backup on success
if not success:
    Path(file_path).write_text(original_content)
if backup_path.exists():
    backup_path.unlink()
```

## PATTERNS

### Known Issue Patterns (runtime metrics)
| Metric | Threshold | Status | Action |
|--------|-----------|--------|--------|
| latency_ms | >120% baseline | degraded | Swap to faster model |
| quality_score | <0.6 | failing | Benchmark alternatives |
| available | 0 | failing | Restart service |

### Systemd Crash-Loop Patterns (updated 2026-06-03)
Repo reorganizations (e.g. an "archaeology" commit that relocates files to `archives/backups/`) frequently leave systemd unit files -- which live outside the repo at `~/.config/systemd/user/` and `/etc/systemd/system/` -- pointing at stale paths. Units with `Restart=always` then crash-loop at ~12 restarts/minute per affected service. This can contribute to system-wide instability on memory-pressured hardware.

| Symptom | Diagnosis | Remediation |
|---------|-----------|-------------|
| `restart counter` >100/hr on a unit | `ExecStart`/`WorkingDirectory` path missing post-reorg | Drop-in override at `<name>.service.d/NN-*.conf`, OR mask if source truly lost |
| Stale ExecStart/WorkingDirectory | Target paths do not exist on disk | SelfDiagnostic flags path existence failure and triggers correction request |
| Many units spinning after repo reorg | Archaeology commit didn't grep `/etc/systemd/system/` or `~/.config/systemd/user/` | `grep -rE "dev/cohezion" ~/.config/systemd/user/ /etc/systemd/system/` post-reorg to find stale refs |
| `/tmp/<dir>` fails hard on fresh boot | tmpfs wipes `/tmp/*` on every boot | `ExecStartPre=/bin/mkdir -p /tmp/<dir>` OR `RuntimeDirectory=<name>` + point arg at `%t/<name>` |
| Crash-loop detection unit itself failing | guardian script missing/broken | Rebuild from `scripts/service_guardian.sh` (see ref below); narrow remediations only |

**Narrow-remediation principle**: a self-healing guardian should (a) recreate transient runtime dirs, and (b) `reset-failed` on known services so `StartLimitBurst` doesn't permanently block them. It should NOT auto-mask units with missing `ExecStart` files -- real regressions must stay visible. Flapping > silently-masked as a default.

Reference implementation: `scripts/service_guardian.sh` (restored in commit `8b870acb9`, 2026-04-21, after original was lost in commit `9dfb5a4e`).

Post-reorg audit one-liner:

```bash
for unit_dir in ~/.config/systemd/user /etc/systemd/system; do
    grep -rhE "^(ExecStart|WorkingDirectory)=" "$unit_dir"/*.service 2>/dev/null \
        | grep -oE "(/home|/opt|/var)[^ ;]+" | sort -u \
        | xargs -I {} sh -c 'test -e "{}" || echo "MISSING: {}"'
done
```

## CITATIONS
- [Unicron](https://huggingface.co/papers/unicron)
- [H-LLM Framework](https://arxiv.org/abs/2312.xxxxx)
- [Reflexion](https://arxiv.org/abs/2303.11366)
- `patterns/systemd-drop-in-override-vs-mask-precedence.md` (vault)
- `learnings/2026-04-21-turboquant-phase0-and-crash-loop-triage.md` (vault)

## VERSION
v0.3 -- 2026-06-03 added systemd stale path verification and backup/rollback mechanisms

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME.md
- OLLAMA_MANAGEMENT_PRIME.md
- TURBOQUANT_PHASE_RECOVERY_S104.md (Phase 4 -- sibling verification pattern)
