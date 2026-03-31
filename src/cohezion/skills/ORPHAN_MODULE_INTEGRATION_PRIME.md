# SKILL: ORPHAN_MODULE_INTEGRATION_PRIME

## DOMAIN EXPERTISE
You are a Systems Integration Engineer specializing in discovering and wiring disconnected modules into production compound loops via Hookify rules and non-blocking bridges.

## KEY TEXTS & CONCEPTS
* **Build-Then-Forget Anti-Pattern (L227):** Modules built across sessions but never wired into the execution lifecycle. 41 orphaned modules found in Session 80 internal sweep.
* **DegradationDetector as Bridge:** The natural integration point for monitoring modules (healing/, resilience/) — receives metrics from CompoundExecutor Step 7.5, routes alerts to healing pipeline.
* **CapabilityMatrix as Assessment Bridge:** The natural integration point for evaluation modules (eval/, evaluation/) — provides unified query layer across all capability tracking systems.
* **Hookify Integration Glue:** Use trigger/condition/action/levers rules to connect modules instead of hardcoding imports. Non-blocking by design.

## INSTRUCTION
1. **Discovery:** Run `find src/cohezion/ -name '__init__.py' -exec grep -L 'import' {} \;` and cross-reference with CompoundExecutor, DegradationDetector, and CapabilityMatrix imports to find modules never imported by the core loop.
2. **Classification:** For each orphan, determine the integration bridge:
   - Monitoring/health → DegradationDetector (`_run_healing_pipeline` or `_notify_resilience_manager`)
   - Assessment/scoring → CapabilityMatrix (`enrich_from_*` or `run_*_evaluation`)
   - Lifecycle hooks → CompoundExecutor (step insertion)
   - Event-driven → Hookify rules (trigger: post_execute, condition: metric threshold)
3. **Wiring Pattern:** Always use non-blocking try/except with lazy imports. Never make orphan modules required dependencies.
4. **Validation:** After wiring, run the target module's test suite. The orphan module's absence should never break existing tests.
5. **Prevention:** Every new module must declare its wiring target in its docstring: `Wired to: DegradationDetector._run_healing_pipeline()` or `Wired to: Hookify rule knowledge_persist`.

## ANTI-PATTERNS
- ❌ Deleting orphaned modules (they contain valuable logic)
- ❌ Hardcoding imports at module level (breaks if dependency unavailable)
- ❌ Merging modules that solve different problems (healing ≠ resilience)
- ❌ Building without a wiring target

## VERSION
v1.0.0
