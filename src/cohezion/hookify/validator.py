"""
Hookify Rule Engine - Core Implementation
Universal rule system with cross-platform MCP bridge support
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Validates rule IDs from on-disk markdown before SQL interpolation
# (Ω12 P1 Patch 7 — defense-in-depth against SurrealQL injection).
_RULE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

try:
    from surrealdb.errors import SurrealDBMethodError
except (ImportError, AttributeError):
    SurrealDBMethodError = ()  # type: ignore[assignment,misc]


@dataclass
class Rule:
    """Hookify rule definition"""

    id: str
    trigger: str
    condition: str
    action: str
    levers: dict[str, Any] = field(default_factory=dict)
    adversarial_tests: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of rule validation"""

    proceed: bool
    block: bool = False
    violations: list[dict[str, Any]] = field(default_factory=list)
    modifications: dict[str, Any] = field(default_factory=dict)


class HookifyValidator:
    """
    Universal Hookify Rule Validator

    Supports three-tier persistence:
    - Tier 1: Git (.agent/HOOKIFY_RULES.md) - defaults
    - Tier 2: SurrealDB (hookify_rules) - runtime overrides
    - Tier 3: Vault (prefrontal/hookify-decisions/) - history

    Cross-platform support:
    - Opencode: Native integration
    - Claude Code: Shell hooks + MCP
    - Gemini CLI: MCP bridge
    """

    def __init__(self, rules: list[Rule] | None = None, rules_path: Path | None = None):
        self.rules = rules or []
        self._db = None  # SurrealDB connection (lazy init)
        self._vault = None  # Vault logger (lazy init)
        self._lever_overrides: dict[tuple[str, str], Any] = {}  # in-memory Tier 2 store
        self._violation_logs: dict[str, list[dict[str, Any]]] = {}  # in-memory Tier 3 store

        if rules_path:
            self.rules = self._load_rules_from_file(rules_path)

    # =========================================================================
    # RULE PARSING (Tier 1: Git)
    # =========================================================================

    def _parse_rules(self, md_content: str) -> list[Rule]:
        """Parse markdown content into Rule objects"""
        rules = []

        # Split by "## Rule:" headers
        sections = re.split(r"\n## Rule:\s*", md_content)

        for section in sections[1:]:  # Skip intro text
            try:
                rule = self._parse_rule_section(section)
                if rule:
                    rules.append(rule)
            except Exception:
                # Invalid rule format - skip gracefully
                continue

        return rules

    def _parse_rule_section(self, section: str) -> Rule | None:
        """Parse single rule section"""
        # Extract ID (first line is rule name if not using **ID**)
        lines = section.strip().split("\n")
        if not lines:
            return None

        rule_id = None
        trigger = None
        condition = None
        action = None
        levers = {}
        adversarial_tests = []

        in_levers = False
        in_tests = False

        for line in lines:
            line = line.strip()

            # Check for **ID** or use first line as ID
            if not rule_id:
                id_match = re.search(r"\*\*ID\*\*:\s*(\S+)", line)
                if id_match:
                    rule_id = id_match.group(1)
                elif lines[0] and not lines[0].startswith("-"):
                    rule_id = lines[0].strip()
                continue

            # Extract trigger
            if not trigger:
                trigger_match = re.search(r"\*\*Trigger\*\*:\s*(.+)", line)
                if trigger_match:
                    trigger = trigger_match.group(1).strip()
                continue

            # Extract condition
            if not condition:
                condition_match = re.search(r"\*\*Condition\*\*:\s*(.+)", line)
                if condition_match:
                    condition = condition_match.group(1).strip()
                continue

            # Extract action
            if not action:
                action_match = re.search(r"\*\*Action\*\*:\s*(.+)", line)
                if action_match:
                    action = action_match.group(1).strip()
                continue

            # Parse levers section
            if "**Levers**:" in line or "- **Levers**:" in line:
                in_levers = True
                in_tests = False
                continue

            # Parse adversarial tests
            if "**Adversarial Tests**:" in line or "- **Adversarial Tests**:" in line:
                in_levers = False
                in_tests = True
                continue

            # Parse lever value
            if in_levers and line.startswith("-"):
                lever_match = re.search(r"-\s*(\w+):\s*(.+)", line)
                if lever_match:
                    name = lever_match.group(1)
                    value = self._parse_value(lever_match.group(2).strip())
                    levers[name] = value

            # Parse test name
            if in_tests and line.startswith("-"):
                test_match = re.search(r"-\s*(test_\w+)", line)
                if test_match:
                    adversarial_tests.append(test_match.group(1))

        if not all([rule_id, trigger, condition, action]):
            return None

        return Rule(
            id=rule_id,
            trigger=trigger,
            condition=condition,
            action=action,
            levers=levers,
            adversarial_tests=adversarial_tests,
        )

    def _parse_value(self, value_str: str) -> float | int | bool | str:
        """Parse lever value string to appropriate type"""
        value_str = value_str.strip()

        # Boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # String (quoted)
        if (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]

        # Float
        if "." in value_str:
            try:
                return float(value_str)
            except ValueError:
                pass

        # Int
        try:
            return int(value_str)
        except ValueError:
            pass

        # String (unquoted)
        return value_str

    def _load_rules_from_file(self, path: Path) -> list[Rule]:
        """Load rules from markdown file"""
        if not path.exists():
            return []

        content = path.read_text()
        return self._parse_rules(content)

    # =========================================================================
    # LEVER RESOLUTION (Tier 1+2+Environment)
    # =========================================================================

    def _resolve_levers(
        self,
        rule_id: str,
        defaults: dict[str, Any],
        db_overrides: dict[str, Any],
        env_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve lever values with precedence:
        1. Environment variables (highest)
        2. SurrealDB runtime overrides
        3. Git defaults (lowest)
        """
        result = dict(defaults)

        # Apply SurrealDB overrides
        for key, value in db_overrides.items():
            if key in result:
                result[key] = value

        # Apply environment overrides (highest priority)
        for key, value in env_overrides.items():
            if key in result:
                # Parse environment value
                result[key] = self._parse_value(str(value))

        return result

    def _get_env_overrides(self, rule_id: str) -> dict[str, str]:
        """Parse environment variables for rule levers"""
        overrides = {}
        prefix = f"HOOKIFY_{rule_id.upper()}_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                lever_name = key[len(prefix) :].lower()
                overrides[lever_name] = value

        return overrides

    # =========================================================================
    # CONDITION EVALUATION
    # =========================================================================

    def _check_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """
        Evaluate rule condition against context

        Supported conditions:
        - "always": Always true
        - "goal.matches(regex)": Check goal against regex
        - "goal.contains(string)": Check goal contains substring
        - "coherence < threshold": Compare numeric values
        - "coherence > threshold": Compare numeric values
        - "cond1 AND cond2": Logical AND
        - "cond1 OR cond2": Logical OR
        """
        condition = condition.strip()

        # Security: validate condition format
        if not self._is_safe_condition(condition):
            raise ValueError(f"Unsafe condition expression: {condition}")

        # "always" condition
        if condition == "always":
            return True

        # Handle AND/OR
        if " AND " in condition:
            parts = condition.split(" AND ")
            return all(self._check_condition(part, context) for part in parts)

        if " OR " in condition:
            parts = condition.split(" OR ")
            return any(self._check_condition(part, context) for part in parts)

        # goal.matches(regex)
        match = re.search(r'goal\.matches\("(.+?)"\)', condition)
        if match:
            pattern = match.group(1)
            goal = context.get("goal", "")
            return bool(re.search(pattern, goal, re.IGNORECASE))

        # goal.contains(string)
        match = re.search(r'goal\.contains\("(.+?)"\)', condition)
        if match:
            substring = match.group(1)
            goal = context.get("goal", "")
            return substring.lower() in goal.lower()

        # Numeric comparison: coherence < 0.5
        match = re.search(r"(\w+)\s*([<>]=?)\s*([\d.]+)", condition)
        if match:
            var_name = match.group(1)
            operator = match.group(2)
            threshold = float(match.group(3))

            value = context.get(var_name, 0)
            if isinstance(value, (int, float)):
                if operator == "<":
                    return value < threshold
                elif operator == ">":
                    return value > threshold
                elif operator == "<=":
                    return value <= threshold
                elif operator == ">=":
                    return value >= threshold

        # Default: false (unknown condition)
        return False

    def _is_safe_condition(self, condition: str) -> bool:
        """Validate condition doesn't contain dangerous patterns"""
        dangerous = ["os.", "subprocess", "eval(", "exec(", "import", "__"]
        return not any(pattern in condition for pattern in dangerous)

    # =========================================================================
    # ACTION EXECUTION
    # =========================================================================

    def _execute_action(
        self, action: str, context: dict[str, Any], levers: dict[str, Any]
    ) -> ValidationResult:
        """
        Execute rule action

        Supported actions:
        - block_if_coherence_below_threshold: Block if coherence < threshold
        - ralph_loop.orchestrate: Initialize Ralph Loop mode
        - allow: Always allow
        - log_violation: Log but don't block
        """
        if action == "block_if_coherence_below_threshold":
            threshold = levers.get("threshold", 0.5)
            coherence = context.get("coherence", 0)

            if coherence < threshold:
                return ValidationResult(
                    proceed=False,
                    block=True,
                    violations=[
                        {
                            "rule": "hiho_stability_gate",
                            "message": f"Coherence {coherence} below threshold {threshold}",
                            "severity": "error",
                        }
                    ],
                    modifications={
                        "fallback_action": levers.get("fallback_action", "decompose_request")
                    },
                )
            else:
                return ValidationResult(proceed=True, block=False)

        elif action == "ralph_loop.orchestrate":
            # Initialize Ralph Loop mode
            return ValidationResult(
                proceed=True,
                block=False,
                modifications={
                    "ralph_mode": True,
                    "coherence_target": levers.get("coherence_threshold", 0.5),
                    "max_iterations": levers.get("max_iterations", 20),
                    "auto_commit": levers.get("auto_commit", True),
                },
            )

        elif action == "allow":
            return ValidationResult(proceed=True, block=False)

        elif action == "log_violation":
            # Log but don't block
            return ValidationResult(
                proceed=True,
                block=False,
                violations=[{"rule": context.get("rule_id"), "message": "Violation logged"}],
            )

        else:
            # Unknown action - allow with warning
            return ValidationResult(
                proceed=True, block=False, violations=[{"message": f"Unknown action: {action}"}]
            )

    # =========================================================================
    # VALIDATION WORKFLOW
    # =========================================================================

    def validate(self, trigger: str, context: dict[str, Any]) -> ValidationResult:
        """
        Validate context against rules matching trigger

        Returns ValidationResult with:
        - proceed: Whether execution should continue
        - block: Whether to block execution
        - violations: List of violations found
        - modifications: Context modifications from rules
        """
        violations = []
        modifications = {}
        should_block = False

        for rule in self.rules:
            if rule.trigger != trigger:
                continue

            # Check condition
            if not self._check_condition(rule.condition, context):
                continue

            # Resolve levers
            db_overrides = self._load_db_overrides(rule.id)
            env_overrides = self._get_env_overrides(rule.id)
            levers = self._resolve_levers(rule.id, rule.levers, db_overrides, env_overrides)

            # Execute action
            result = self._execute_action(rule.action, context, levers)

            # Collect violations
            violations.extend(result.violations)

            # Merge modifications
            modifications.update(result.modifications)

            # Track block
            if result.block:
                should_block = True

            # Log to vault (Tier 3)
            self._log_validation(rule.id, context, result)

        return ValidationResult(
            proceed=not should_block,
            block=should_block,
            violations=violations,
            modifications=modifications,
        )

    def _load_db_overrides(self, rule_id: str) -> dict[str, Any]:
        """Load runtime lever overrides from SurrealDB"""
        # Lazy initialization
        if self._db is None:
            self._db = self._init_surrealdb()

        if self._db:
            # rule_id can come from on-disk markdown — validate before SQL
            # (Ω12 P1 Patch 7 — SurrealQL injection defense).
            if not _RULE_ID_RE.match(rule_id):
                logger.warning("Skipping load_db_overrides: invalid rule_id %r", rule_id)
                return {}
            try:
                result = self._db.query(
                    "LET $rid = $rule_id; SELECT * FROM hookify_rules WHERE rule_id = $rid",
                    {"rule_id": rule_id},
                )
                if result and len(result) > 0:
                    return result[0].get("lever_overrides", {})
            except (
                ConnectionError,
                OSError,
                ValueError,
                TypeError,
                SurrealDBMethodError,
            ) as e:
                logger.debug("load_db_overrides failed: %s", e)

        return {}

    def _init_surrealdb(self):
        """Initialize SurrealDB connection"""
        try:
            from surrealdb import Surreal

            # Initialize with connection URL (placeholder - actual URL would come from config)
            db = Surreal("ws://localhost:8001")
            # Connection logic here - signin, use namespace, etc.
            return db
        except (
            ImportError,
            AttributeError,
            ConnectionError,
            OSError,
            RuntimeError,
            ValueError,
            SurrealDBMethodError,
        ):
            # SurrealDB not available or connection failed
            return None

    def _log_validation(self, rule_id: str, context: dict, result: ValidationResult):
        """Log validation result to vault (Tier 3)"""
        if result.violations:
            for violation in result.violations:
                self._log_violation(rule_id, context, violation)

    # =========================================================================
    # CROSS-PLATFORM TRIGGER NORMALIZATION
    # =========================================================================

    TRIGGER_MAP = {
        "opencode": {
            "CompoundSessionManager.start_session": "session_start",
            "CompoundSessionManager.check_alignment": "pre_execute",
            "CompoundExecutor.execute_task": "post_execute",
        },
        "claude_code": {
            "CLAUDE.md_load": "session_start",
            "pre_execute": "pre_execute",
            "post_execute": "post_execute",
        },
        "gemini": {
            "GEMINI.md_load": "session_start",
            "mcp_pre_execute": "pre_execute",
            "mcp_post_execute": "post_execute",
        },
    }

    def _normalize_trigger(self, trigger: str, platform: str) -> str:
        """
        Normalize platform-specific triggers to canonical names

        Args:
            trigger: Platform-specific trigger name
            platform: Platform identifier (opencode, claude_code, gemini)

        Returns:
            Canonical trigger name (session_start, pre_execute, post_execute, etc.)
        """
        platform_map = self.TRIGGER_MAP.get(platform, {})
        return platform_map.get(trigger, trigger)

    # =========================================================================
    # TIER 2+3 PERSISTENCE (Placeholder for integration)
    # =========================================================================

    def _save_lever_override(self, rule_id: str, lever_name: str, value: Any):
        """Save runtime lever override to SurrealDB"""
        # Placeholder - integrate with SurrealDB
        pass

    def _load_lever_override(self, rule_id: str, lever_name: str) -> Any:
        """Load runtime lever override from SurrealDB"""
        # Placeholder - integrate with SurrealDB
        return None

    def _log_violation(self, rule_id: str, context: dict, violation: dict):
        """Log violation to vault for recursive learning"""
        # Placeholder - integrate with VaultLogger
        pass

    def _get_violation_logs(self, rule_id: str) -> list[dict]:
        """Retrieve violation logs from vault"""
        # Placeholder - integrate with VaultLogger
        return []

    # =========================================================================
    # CONVENIENCE API
    # =========================================================================

    def get_rule(self, rule_id: str) -> Rule | None:
        """Get rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def list_rules(self) -> list[str]:
        """List all rule IDs"""
        return [rule.id for rule in self.rules]

    def get_lever_positions(self, rule_id: str) -> dict[str, Any]:
        """Get current lever positions for a rule"""
        rule = self.get_rule(rule_id)
        if not rule:
            return {}

        db_overrides = self._load_db_overrides(rule_id)
        env_overrides = self._get_env_overrides(rule_id)

        return self._resolve_levers(rule_id, rule.levers, db_overrides, env_overrides)

    def _save_lever_override(self, rule_id: str, lever_name: str, value: Any) -> None:
        """Persist lever override in-memory (Tier 2 write-ahead store)."""
        self._lever_overrides[(rule_id, lever_name)] = value

    def _load_lever_override(self, rule_id: str, lever_name: str) -> Any:
        """Load lever override from in-memory store. Returns None if not set."""
        return self._lever_overrides.get((rule_id, lever_name))

    def _log_violation(
        self, rule_id: str, context: dict[str, Any], violation: dict[str, Any]
    ) -> None:
        """Append violation to in-memory log (Tier 3 audit trail)."""
        if rule_id not in self._violation_logs:
            self._violation_logs[rule_id] = []
        self._violation_logs[rule_id].append({**context, "violation": violation})

    def _get_violation_logs(self, rule_id: str) -> list[dict[str, Any]]:
        """Return violation log entries for a rule."""
        return self._violation_logs.get(rule_id, [])

    def set_lever_position(self, rule_id: str, lever_name: str, value: Any) -> dict[str, Any]:
        """Set lever override (write-ahead: persists even for unknown rules).

        Returns:
            Dict with success status, previous and new values.
        """
        previous_value = self._load_lever_override(rule_id, lever_name)
        rule = self.get_rule(rule_id)
        if rule and lever_name in rule.levers:
            previous_value = rule.levers[lever_name]

        self._save_lever_override(rule_id, lever_name, value)

        return {
            "success": True,
            "rule_id": rule_id,
            "lever_name": lever_name,
            "previous_value": previous_value,
            "new_value": value,
        }
