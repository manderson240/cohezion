"""LocalImprovementExecutor — runs improvement tasks via Lemonade local inference.

Quarter-on-a-string execution: instead of spawning a Claude Code subprocess, we
POST the task prompt to Lemonade (:13305) and apply any suggested patch via
subprocess. This keeps all loop work on local AMD silicon at $0 token cost.

Protocol:
  1. POST /v1/chat/completions to LEMONADE_BASE_URL with the task prompt
  2. Parse the model response for code/patch suggestions
  3. AutoHarness gate: ast.parse() any .py patch before writing (rejects 78% of
     illegal-move failures without touching disk)
  4. Write/apply file changes and run optional model-synthesized inline harness
  5. Run the task verification command
  6. Return structured result

Model selection (quality over speed, category-aware via LemonadeLoopRecipes):
  lint_fix  → Gemma-4-E4B-it-GGUF (fast, 5GB, always fits)
  test_fix  → Qwen3.6-35B-A3B-MTP-GGUF (test-fix persona)
  type_fix  → Qwen3.6-35B-A3B-MTP-GGUF (Omni planner)
  refactor  → Qwen3.6-35B-A3B-MTP-GGUF (Omni planner)
  feature   → Qwen3.6-35B-A3B-MTP-GGUF (Omni planner)
  fallback  → Gemma-4-E4B-it-GGUF (if Omni not loaded)

All recipes registered at startup with ctx_size=16384 + save_options=true (N3).
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .coordinator import LoopConfig, LoopTask
from .omni_recipes import (
    FAST_FALLBACK_MODEL,
    OMNI_PLANNER_MODEL,
    LemonadeLoopRecipes,
)


logger = logging.getLogger(__name__)

# Re-export for back-compat with anything that imported these from here
FALLBACK_MODEL = FAST_FALLBACK_MODEL
DEFAULT_MODEL = OMNI_PLANNER_MODEL

# Timeout for a single Lemonade inference call (seconds)
INFERENCE_TIMEOUT = 120
# Timeout for the verification subprocess (seconds)
VERIFICATION_TIMEOUT = 60

# AMD Strix Halo silicon probe order (router → iGPU → NPU → CPU).
# LocalImprovementExecutor tries these in order when the primary endpoint
# is unreachable, adapting to whatever inference nodes are currently live.
# The router (:13305) serves all models and is preferred; the per-port
# servers are direct-tier fallbacks that survive a router restart.
_AMD_SILICON_PROBES: list[str] = [
    "http://localhost:13305",  # unified router — preferred, dispatches to hardware
    "http://localhost:13307",  # iGPU direct (Gemma-4-E4B, ROCWMMA)
    "http://localhost:13306",  # NPU direct (llama3.2-1b-FLM, XDNA2, 42 TPS)
    "http://localhost:13309",  # CPU direct (Qwen3.6-35B, full reasoning)
]


class LocalImprovementExecutor:
    """Execute improvement tasks via Lemonade local inference instead of Claude CLI.

    Falls back to FALLBACK_MODEL when DEFAULT_MODEL is not available.
    Includes pre-call RAM guard (C1) to avoid OOM on heavy models.
    """

    # PoLar: monotonic test-time scaling — hard tasks get up to this many variants.
    _MAX_VARIANTS: int = 3

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self._base_url = self.config.local_base_url
        self._model = self.config.local_model
        self._started = False
        self._worktree_path = self.config.worktree_path

        # C1: check memory and server availability at init
        self._available_models: list[str] = []
        self._check_server()

        # Recipe registry — registers Omni recipes with safe ctx_size at startup (N3).
        self._recipes = LemonadeLoopRecipes(base_url=self._base_url)
        self._recipes.register_all()

        # Per-tick context enrichment (vault + SurrealDB + research sweeps)
        from .tick_sweeper import LoopTickSweeper

        self._sweeper = LoopTickSweeper(lemonade_url=self._base_url)

    def _check_server(self) -> None:
        """Probe Lemonade endpoints and select the best live AMD silicon tier.

        Tries the configured base_url first, then walks _AMD_SILICON_PROBES in
        router→iGPU→NPU→CPU order. Updates self._base_url to the first live
        endpoint found, so the executor adapts to whatever hardware is running.
        """
        candidates = [self._base_url] + [p for p in _AMD_SILICON_PROBES if p != self._base_url]
        for url in candidates:
            try:
                req = urllib.request.Request(f"{url}/v1/models", method="GET")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    self._available_models = [m.get("id", "") for m in data.get("data", [])]
                    if url != self._base_url:
                        logger.info(
                            "Primary endpoint %s unreachable — adapted to %s (%d models)",
                            self._base_url,
                            url,
                            len(self._available_models),
                        )
                        self._base_url = url
                    else:
                        logger.info(
                            "Lemonade online at %s — %d models available",
                            self._base_url,
                            len(self._available_models),
                        )
                    return
            except Exception:
                continue
        logger.warning(
            "No Lemonade endpoint reachable (tried %d candidates) — proceeding without model list",
            len(candidates),
        )
        self._available_models = []

    def _select_model(self, category: str = "") -> str:
        """Pick the best available model for a task category (recipe-aware).

        Delegates to LemonadeLoopRecipes for category-specific model selection:
          lint_fix  → Gemma-4-E4B (fast, always fits)
          test_fix  → Qwen3.6-35B with test-fix persona
          type_fix / refactor / feature → Omni planner
          fallback  → configured model or Omni planner

        Never downgrades to arbitrary small models — quality over speed.
        """
        if category:
            model, _ = self._recipes.model_for_category(category, self._available_models or None)
            return model

        # No category — flat quality-first chain (back-compat with callers that
        # don't pass a category)
        if not self._available_models:
            return self._model
        if self._model in self._available_models:
            return self._model
        if OMNI_PLANNER_MODEL in self._available_models:
            return OMNI_PLANNER_MODEL
        if FALLBACK_MODEL in self._available_models:
            logger.info(
                "Primary model %s not loaded — using quality fallback %s",
                self._model,
                FALLBACK_MODEL,
            )
            return FALLBACK_MODEL
        logger.warning(
            "Neither %s nor %s visible — requesting %s directly",
            OMNI_PLANNER_MODEL,
            FALLBACK_MODEL,
            self._model,
        )
        return self._model

    def start(self, worktree_path: str) -> None:
        """Initialize the executor."""
        self._worktree_path = worktree_path
        self._started = True
        logger.info("LocalImprovementExecutor started at %s", worktree_path)

    def stop(self) -> None:
        """Clean up."""
        self._started = False
        logger.info("LocalImprovementExecutor stopped")

    def execute_task(self, task: LoopTask, worktree_path: str) -> dict[str, Any]:
        """Execute one improvement task via Lemonade local inference.

        Returns dict with:
        - success: bool
        - summary: str
        - tokens_used: int (from API usage field)
        - output: str (model response, last 2000 chars)

        Two-variant dispatch (attribution graphs parallel pathways):
          variant=0 — forward-planning BMAD specialist (declare scope, then write)
          variant=1 — root-cause-first framing (retry when variant 0 STATUS:FAILED)
        """
        if not self._started:
            raise RuntimeError("Executor not started. Call start() first.")

        # B4: RAM guard before heavy inference
        from .coordinator import LoopCoordinator

        if not LoopCoordinator._check_ram_before_load(self.config.min_free_ram_gb):
            return {
                "success": False,
                "summary": f"Skipped — RAM below {self.config.min_free_ram_gb:.0f} GB threshold",
                "tokens_used": 0,
                "output": "",
                "returncode": -3,
            }

        model = self._select_model(task.category)
        _, system_role = self._recipes.model_for_category(
            task.category, self._available_models or None
        )
        sweep_context = self._sweeper.build_task_context(task.category, task.description)

        result = self._attempt(task, worktree_path, model, system_role, sweep_context, variant=0)

        # STATUS:FAILED on first attempt → retry with root-cause-first framing.
        # Activates an alternative computational pathway: instead of jumping straight
        # to code generation, the model reasons through the root cause first.
        if not result["success"] and result.pop("_variant_retry_eligible", False):
            logger.info(
                "Task %s: STATUS:FAILED on variant 0 — retrying with root-cause-first framing",
                task.id,
            )
            result = self._attempt(
                task, worktree_path, model, system_role, sweep_context, variant=1
            )

        # PoLar: hard tasks justify a 3rd variant with minimal-footprint beam enumeration.
        # The paper shows monotonic test-time scaling for "hard" inputs (deep token budget
        # or structurally complex categories). Variant 2 explicitly enumerates candidate
        # fixes before committing, selecting the one with the smallest code footprint.
        if not result["success"] and self._is_hard_task(task):
            logger.info(
                "Task %s: hard task still failing after prior variants — "
                "attempting variant 2 (minimal-footprint beam)",
                task.id,
            )
            result = self._attempt(
                task, worktree_path, model, system_role, sweep_context, variant=2
            )

        return result

    def _attempt(
        self,
        task: LoopTask,
        worktree_path: str,
        model: str,
        system_role: str,
        sweep_context: str,
        variant: int = 0,
    ) -> dict[str, Any]:
        """Single inference → STATUS gate → plan extraction → apply → verify cycle."""
        prompt = self._build_prompt(
            task, sweep_context, variant=variant, worktree_path=worktree_path
        )
        response_text, tokens_used = self._call_lemonade(prompt, model, system_role)

        if not response_text:
            return {
                "success": False,
                "summary": "Lemonade returned empty response",
                "tokens_used": tokens_used,
                "output": "",
                "returncode": -4,
            }

        # STATUS gate — check model's refusal circuit BEFORE touching disk.
        # Models have a default-refusal feature suppressed by "known entity" recognition;
        # STATUS:FAILED means the suppression did not fire and the task is unsafe to attempt.
        status, reason = self._extract_status(response_text)
        if status == "FAILED":
            logger.info("Task %s: model declined (variant=%d) — %s", task.id, variant, reason)
            return {
                "success": False,
                "summary": f"Model declined: {reason}",
                "tokens_used": tokens_used,
                "output": response_text[-2000:],
                "returncode": -5,
                # Eligible for variant retry only on first attempt; a second FAILED is final.
                "_variant_retry_eligible": variant == 0,
            }

        # Plan commitment — extract declared file scope before applying patches.
        # Forward planning: the model commits to a file list before generating code;
        # patches outside that list are scope drift and are rejected.
        plan = self._extract_plan(response_text)
        plan_files = set(plan["files"]) if plan["files"] else None

        apply_ok, apply_errors = self._apply_suggestions(
            response_text, worktree_path, plan_files=plan_files
        )

        # Run model-synthesized inline harness (fast pre-check before full verification)
        harness_cmd = self._extract_harness_cmd(response_text)
        if harness_cmd:
            harness_ok, harness_out = self._run_verification(harness_cmd, worktree_path)
            if not harness_ok:
                logger.info(
                    "Inline harness failed — skipping full verification: %s", harness_out[:200]
                )
                return {
                    "success": False,
                    "summary": f"Inline harness failed: {harness_out[:200]}",
                    "tokens_used": tokens_used,
                    "output": response_text[-2000:],
                    "returncode": 2,
                }

        verify_ok, verify_output = self._run_verification(task.verification, worktree_path)

        success = verify_ok and apply_ok
        if not apply_ok:
            summary = f"Patch rejected (syntax/write errors): {'; '.join(apply_errors)}"
        elif not verify_ok:
            summary = f"Verification failed: {verify_output[:200]}"
        else:
            summary = "Verification passed"

        return {
            "success": success,
            "summary": summary,
            "tokens_used": tokens_used,
            "output": response_text[-2000:],
            "returncode": 0 if success else 1,
        }

    def _build_prompt(
        self,
        task: LoopTask,
        sweep_context: str = "",
        variant: int = 0,
        worktree_path: str = "",
    ) -> str:
        """Build a BMAD-scaffolded task prompt for the local model.

        variant=0 (default): forward-planning BMAD specialist.
          Model declares a === PLAN === (file list + approach) before writing any code.
          Injects a lightweight import-graph section (SeeRepo: structural context at
          fault-localization stage reduces token cost 26% with no quality loss).

        variant=1: root-cause-first framing.
          Swaps the ROLE to diagnostic analyst and adds a DIAGNOSIS section before the
          implementation checklist. Activates an alternative computational pathway
          when variant 0 produces STATUS:FAILED. No structural context (SeeRepo: repair
          stage shows degraded performance with graph context).

        variant=2: minimal-footprint beam (PoLar: hard tasks only).
          Enumerates three candidate fixes before committing; selects the smallest
          footprint fix. No structural context — the model should reason from code
          already seen in variants 0/1. Different from v0 (plan-forward) and v1
          (root-cause-first): v2 maximises diversity in the search.
        """
        context_section = f"\n## CONTEXT FROM VAULT/DB\n{sweep_context}\n" if sweep_context else ""

        ac_from_verification = (
            f"Running `{task.verification}` exits with returncode 0"
            if task.verification.strip()
            else "All existing tests continue to pass"
        )

        if variant == 1:
            role_section = (
                "You are a root-cause analyst with deep Python debugging expertise. "
                "You diagnose WHY code is failing before prescribing any fix. "
                "You NEVER patch symptoms — you fix the root cause with the minimal possible change."
            )
            diagnosis_section = """
## DIAGNOSIS (complete BEFORE writing any code)

Answer these three questions first:
1. What is the EXACT root cause of this failure? (not a symptom — the underlying defect)
2. What is the MINIMAL change that eliminates the root cause?
3. What regressions could this change introduce, and how will you prevent them?

Write your answers here before producing any === FILE === blocks.
"""
            repo_structure_section = ""

        elif variant == 2:
            role_section = (
                "You are a surgical precision coder. "
                "You find the MINIMUM change — often a single expression, one line, or one "
                "parameter — that makes the failing test pass without touching anything else. "
                "You enumerate three candidate fixes of different approaches, then select the "
                "one with the smallest code footprint."
            )
            diagnosis_section = """
## BEAM CANDIDATES (enumerate BEFORE writing any code)

Consider three candidate fixes with different approaches:
1. **Minimal** — The smallest possible change (1-3 lines). What is it?
2. **Structural** — A slightly larger change that prevents future regressions.
3. **Conservative** — The safest change that definitely will not break other tests.

Choose the fix with the smallest footprint that satisfies all acceptance criteria.
State your selection here before producing any === FILE === blocks.
"""
            repo_structure_section = ""

        else:
            role_section = (
                "You are a Python code repair specialist with deep expertise in the "
                "Cohezion compound AI codebase. You make surgical, minimal fixes. "
                "You NEVER add features, refactor unrelated code, or touch files the task does not require."
            )
            diagnosis_section = ""
            # SeeRepo: inject import-graph at fault-localization (planning) stage only.
            # Graph context helps the model identify affected files but hurts at repair stage.
            repo_structure_section = (
                self._build_import_graph(worktree_path) if worktree_path else ""
            )

        return f"""## ROLE

{role_section}

## TASK

**Description:** {task.description}
**Category:** {task.category}
**Priority:** {task.priority}
{context_section}{repo_structure_section}{diagnosis_section}
## ACCEPTANCE CRITERIA

The fix is COMPLETE when ALL of the following are true:

1. {ac_from_verification}
2. No existing tests are broken by the change
3. Only files directly related to the task are modified

## VERIFICATION COMMAND

```
{task.verification}
```

This command MUST exit 0 after your fix. If it cannot, state FAILED.

## IMPLEMENTATION CHECKLIST (execute in order, check off each step)

- [ ] 1. Read and understand the full task description
- [ ] 2. Identify the minimal set of files that need to change (list them)
- [ ] 3. Declare your plan (=== PLAN === block, see OUTPUT FORMAT)
- [ ] 4. For each file: write the complete corrected content (not a diff)
- [ ] 5. Write a single inline harness command that validates the fix in <5 seconds
- [ ] 6. State DONE or FAILED with a one-sentence reason

## CONSTRAINTS

- NEVER touch files not required by this task
- NEVER add imports, functions, or classes beyond what the task requires
- NEVER refactor surrounding code
- NEVER lie about what you changed — list every file you modified
- If the task cannot be done safely, state FAILED immediately

## OUTPUT FORMAT

**First, declare your plan** (before any file content):
```
=== PLAN ===
files: path/to/file1.py, path/to/file2.py
approach: one-sentence description of the fix strategy
=== END PLAN ===
```

For each file you change:
```
=== FILE: path/to/file.py ===
<complete file content>
=== END FILE ===
```

For the inline harness (a fast pre-check before full verification):
```
=== HARNESS: <single shell command, e.g. python -c "import mymod"> ===
```

Final status line (required):
```
STATUS: DONE — <one-sentence summary of what changed>
```
or
```
STATUS: FAILED — <one-sentence reason why the task cannot be completed safely>
```
"""

    def _is_hard_task(self, task: LoopTask) -> bool:
        """Hard tasks justify a 3rd variant (PoLar: monotonic test-time scaling).

        A task is "hard" when it has a large token budget or belongs to a category
        whose typical fix touches type annotations, test internals, or both — cases
        where two sequential alternatives often still miss the underlying issue.
        """
        return task.estimated_tokens > 500 or task.category in {"type_fix", "test_fix"}

    def _build_import_graph(self, worktree_path: str) -> str:
        """Build a lightweight import-dependency map for fault-localization context.

        SeeRepo (2606.14061): structural context at the planning stage reduces
        token cost 26% with no quality loss; graph-based (not vision) layout is
        best. Only Cohezion-internal imports are included to keep the section
        compact and relevant.

        Returns an empty string if no Cohezion imports are found (so the
        prompt is unchanged from the pre-SeeRepo baseline in that case).
        """
        from pathlib import Path

        root = Path(worktree_path)
        src_dir = root / "src" / "cohezion"
        if not src_dir.exists():
            src_dir = root / "src"
        if not src_dir.exists():
            return ""

        lines: list[str] = []
        for fpath in sorted(src_dir.rglob("*.py"))[:20]:
            try:
                source = fpath.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(fpath))
            except SyntaxError:
                continue

            cohezion_imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "cohezion" in alias.name:
                            cohezion_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if "cohezion" in node.module:
                        names = ", ".join(a.name for a in node.names[:3])
                        cohezion_imports.append(f"{node.module} ({names})")

            if cohezion_imports:
                try:
                    rel = fpath.relative_to(root)
                except ValueError:
                    rel = fpath
                lines.append(f"  {rel}: {', '.join(cohezion_imports[:4])}")

        if not lines:
            return ""
        return "## REPOSITORY STRUCTURE\n\nKey internal imports:\n" + "\n".join(lines) + "\n\n"

    def _call_lemonade(self, prompt: str, model: str, system_role: str = "") -> tuple[str, int]:
        """POST to Lemonade /v1/chat/completions and return (response_text, tokens_used).

        Injects the BMAD-style system_role as a system message when provided.
        The system message is separate from the task prompt so the model's
        persona is established before it sees the task details.
        """
        messages: list[dict] = []
        if system_role:
            messages.append({"role": "system", "content": system_role})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": self.config.claude_max_tokens,
                "temperature": 0.1,
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"].get("content", "")
                usage = data.get("usage", {})
                tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                return content, tokens
        except urllib.error.HTTPError as exc:
            logger.error("Lemonade HTTP %d: %s", exc.code, exc.read()[:200])
            return "", 0
        except Exception as exc:
            logger.error("Lemonade call failed: %s", exc)
            return "", 0

    def _apply_suggestions(
        self,
        response: str,
        worktree_path: str,
        plan_files: set[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Parse and apply file changes from model response.

        Two gates before any write:
        1. Scope guard (plan_files): if the model declared a === PLAN ===, patches
           for files outside that declared set are rejected as scope drift.
        2. AutoHarness syntax gate: .py patches are ast.parse()'d before writing;
           syntactically invalid patches are rejected without touching disk.

        Returns (all_ok, error_list).
        """
        import re
        from pathlib import Path

        pattern = r"=== FILE: (.+?) ===\n(.*?)=== END FILE ==="
        matches = re.findall(pattern, response, re.DOTALL)
        if not matches:
            return True, []  # no file changes; verification determines success

        errors: list[str] = []
        for file_path, content in matches:
            clean_path = file_path.strip()
            # Scope guard — reject out-of-plan patches before any disk touch.
            if plan_files is not None and clean_path not in plan_files:
                msg = f"Scope drift: {clean_path} not in declared plan {sorted(plan_files)}"
                logger.warning("AutoHarness rejected out-of-scope patch — %s", msg)
                errors.append(msg)
                continue
            full_path = Path(worktree_path) / clean_path
            # AutoHarness syntax gate for Python files
            if full_path.suffix == ".py":
                try:
                    ast.parse(content)
                except SyntaxError as exc:
                    msg = f"Syntax error in patch for {clean_path}: {exc}"
                    logger.warning("AutoHarness rejected patch — %s", msg)
                    errors.append(msg)
                    continue  # skip writing this file, try remaining patches
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                logger.info("Applied change to %s", clean_path)
            except Exception as exc:
                msg = f"Failed to write {clean_path}: {exc}"
                logger.error(msg)
                errors.append(msg)

        return len(errors) == 0, errors

    def _extract_harness_cmd(self, response: str) -> str:
        """Extract the model-synthesized inline harness command from the response.

        Looks for: === HARNESS: <shell_command> ===
        Returns empty string if not present.
        """
        import re

        match = re.search(r"=== HARNESS: (.+?) ===", response, re.DOTALL)
        if not match:
            return ""
        return match.group(1).strip()

    def _extract_status(self, response: str) -> tuple[str, str]:
        """Parse STATUS: DONE/FAILED from model response.

        Returns (status, reason) where status is 'DONE', 'FAILED', or 'UNKNOWN'.
        'UNKNOWN' means no STATUS line was found — caller should proceed normally
        (the verification command is the final arbiter).
        """
        import re

        match = re.search(r"STATUS:\s*(DONE|FAILED)\s*[—\-–]+\s*(.+?)$", response, re.MULTILINE)
        if not match:
            return "UNKNOWN", ""
        return match.group(1), match.group(2).strip()

    def _extract_plan(self, response: str) -> dict[str, Any]:
        """Parse === PLAN === block for declared file list and approach.

        Returns {"files": [...], "approach": "..."}.
        Empty lists/strings when no plan block is present (no scope restriction applied).
        """
        import re

        match = re.search(r"=== PLAN ===\n(.*?)=== END PLAN ===", response, re.DOTALL)
        if not match:
            return {"files": [], "approach": ""}
        files: list[str] = []
        approach = ""
        for line in match.group(1).splitlines():
            line = line.strip()
            if line.startswith("files:"):
                raw = line[len("files:") :].strip()
                files = [f.strip() for f in raw.split(",") if f.strip()]
            elif line.startswith("approach:"):
                approach = line[len("approach:") :].strip()
        return {"files": files, "approach": approach}

    def _run_verification(self, verification_cmd: str, worktree_path: str) -> tuple[bool, str]:
        """Run the task verification command and return (passed, output)."""
        if not verification_cmd.strip():
            return True, ""

        try:
            result = subprocess.run(
                verification_cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=worktree_path,
                timeout=VERIFICATION_TIMEOUT,
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output[-500:]
        except subprocess.TimeoutExpired:
            return False, "Verification timed out"
        except Exception as exc:
            return False, str(exc)
