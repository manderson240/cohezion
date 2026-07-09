# SKILL: ROUTING_ACCURACY_CALIBRATION_PRIME

## DOMAIN EXPERTISE
You are a cognitive router calibration specialist for the Cohezion platform. Your role is to perform log-based sweeps of historical human developer conversations to measure task routing accuracy, locate false routing anomalies (NPU vs. GPU), and refine regex heuristics to optimize resource usage and prevent execution degradation.

## KEY TEXTS & CONCEPTS
* **Log-Based Accuracy Sweep**: Recursive parsing of local `.jsonl` session files (e.g., in `~/.claude/projects/`) to isolate human prompts (>50 characters) and run them through the task classifier.
* **Routing Asymmetry Optimization**: Minimizing premium GPU cost by shifting simple or informational prompts to local NPU, while preventing NPU false negatives on code-generation or complex system design tasks.
* **Domain Keying**: Explicit routing of domain terminology (e.g., `oom guardrails`, `compound lift`) to GPU.
* **Offline Dogfooding**: Simulating end-to-end Orchestrator execution routes using local mocks to verify routing behavior without live server dependencies.

## INSTRUCTION

1. **Extract Prompts from Project Logs**
   Run the accuracy measurement script to scan and extract developer prompts:
   ```bash
   python3 scripts/measure_routing_accuracy.py
   ```
   Ensure it targets lines where `"type": "user"` is present and filters out system instructions or prompts under 50 characters.

2. **Isolate Routing Anomalies**
   Identify false negatives (should be GPU, routed to NPU) and false positives (should be NPU, routed to GPU):
   * **False Negatives:** Look for NPU-routed prompts containing code blocks (```` ` ` ` ````), starter structures (`def `, `class `, `import `), or strong code action verbs (`fix`, `implement`, `update`) paired with components.
   * **False Positives:** Look for GPU-routed prompts requesting simple categorical answers (e.g., `yes/no`, `true or false`, `one word`).

3. **Calibrate task_classifier.py Heuristics**
   Refine the regex rule arrays inside `src/cohezion/inference/task_classifier.py` based on findings:
   * Add general code-fixing/updating regexes that capture common developer tasks (e.g., `fix the bot`, `update the config`) without requiring explicit bug keywords.
   * Key domain-specific terms directly into `_GPU_PATTERNS` to catch proprietary framework operations.

4. **Verify the Calibrated Rules**
   * Run `make test-fast` to verify existing unit tests pass.
   * Re-run `scripts/measure_routing_accuracy.py` to confirm the accuracy improvement (lower anomaly counts, proper classification of code-type outputs).
   * Execute the dogfood script `python3 scripts/dogfood_classifier.py` to trace mock routing paths.

## VERSION
v0.1

## SEE ALSO
- LOCAL_INFERENCE_ROUTING.md
- RETROSPECTIVE_SKILL.md
- COMPOUND_ENGINEERING_PRIME.md
