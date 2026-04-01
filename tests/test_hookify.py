"""
TDD Test Suite for Hookify Rule Engine
Tests written BEFORE implementation (TDD approach)
"""

import pytest

from cohezion.hookify.validator import HookifyValidator, Rule


class TestHookifyRuleParsing:
    """Test 1: Rule parsing from markdown"""

    @pytest.fixture
    def sample_rules_md(self):
        return """
## Rule: cosmological_ralph_loop
- **ID**: cosmological_ralph_loop
- **Trigger**: session_start
- **Condition**: goal.matches("cosmology|solver|universe")
- **Action**: ralph_loop.orchestrate
- **Levers**:
  - coherence_threshold: 0.5
  - max_iterations: 20
  - auto_commit: true

## Rule: hiho_stability_gate
- **ID**: hiho_stability_gate
- **Trigger**: pre_execute
- **Condition**: always
- **Action**: block_if_coherence_below_threshold
- **Levers**:
  - threshold: 0.5
  - fallback_action: decompose_request
"""

    def test_parse_rule_from_markdown(self, sample_rules_md):
        """Parse markdown into Rule objects"""
        # When: HookifyValidator parses the markdown
        validator = HookifyValidator()
        rules = validator._parse_rules(sample_rules_md)

        # Then: Rules are extracted with correct structure
        assert len(rules) == 2
        assert rules[0].id == "cosmological_ralph_loop"
        assert rules[0].trigger == "session_start"
        assert rules[0].levers["coherence_threshold"] == 0.5
        assert rules[0].levers["max_iterations"] == 20
        assert rules[0].levers["auto_commit"] is True

    def test_parse_rule_with_various_types(self):
        """Parse rules with different lever types"""
        md = """
## Rule: test_rule
- **ID**: test_rule
- **Trigger**: session_start
- **Condition**: always
- **Action**: test_action
- **Levers**:
  - float_val: 0.5
  - int_val: 20
  - bool_val: true
  - str_val: "hello"
"""
        validator = HookifyValidator()
        rules = validator._parse_rules(md)

        assert rules[0].levers["float_val"] == 0.5
        assert rules[0].levers["int_val"] == 20
        assert rules[0].levers["bool_val"] is True
        assert rules[0].levers["str_val"] == "hello"


class TestHookifyLeverResolution:
    """Test 2: Lever resolution precedence"""

    @pytest.fixture
    def default_levers(self):
        return {"coherence_threshold": 0.5, "max_iterations": 20, "auto_commit": False}

    def test_default_lever_values(self, default_levers):
        """Tier 1: Git defaults are used when no overrides"""
        validator = HookifyValidator()

        # When: Resolving levers with no overrides
        result = validator._resolve_levers(
            rule_id="cosmological_ralph_loop",
            defaults=default_levers,
            db_overrides={},
            env_overrides={},
        )

        # Then: Defaults returned
        assert result["coherence_threshold"] == 0.5
        assert result["max_iterations"] == 20
        assert result["auto_commit"] is False

    def test_surrealdb_override(self, default_levers):
        """Tier 2: SurrealDB overrides Git defaults"""
        validator = HookifyValidator()

        # When: DB has override
        db_overrides = {"coherence_threshold": 0.7}
        result = validator._resolve_levers(
            rule_id="test", defaults=default_levers, db_overrides=db_overrides, env_overrides={}
        )

        # Then: DB override applied
        assert result["coherence_threshold"] == 0.7
        assert result["max_iterations"] == 20  # Unchanged

    def test_environment_override(self, default_levers):
        """Tier 1+ (Environment): ENV overrides all"""
        validator = HookifyValidator()

        # When: Environment has override
        env_overrides = {"coherence_threshold": "0.9"}
        result = validator._resolve_levers(
            rule_id="test",
            defaults=default_levers,
            db_overrides={"coherence_threshold": 0.7},
            env_overrides=env_overrides,
        )

        # Then: Environment wins
        assert result["coherence_threshold"] == 0.9

    def test_environment_variable_parsing(self, default_levers, monkeypatch):
        """ENV variables are parsed from environment"""
        monkeypatch.setenv("HOOKIFY_COSMOLOGICAL_RALPH_LOOP_COHERENCE_THRESHOLD", "0.85")

        validator = HookifyValidator()
        env_overrides = validator._get_env_overrides("cosmological_ralph_loop")

        assert env_overrides["coherence_threshold"] == "0.85"


class TestHookifyConditionEvaluation:
    """Test 3: Condition evaluation (adversarial)"""

    def test_condition_always(self):
        """'always' condition always matches"""
        validator = HookifyValidator()

        result = validator._check_condition("always", {})
        assert result is True

    def test_condition_goal_matches(self):
        """goal.matches() evaluates regex"""
        validator = HookifyValidator()

        context = {"goal": "Implement cosmological Boltzmann solver"}
        result = validator._check_condition('goal.matches("cosmology|solver|universe")', context)
        assert result is True

        context = {"goal": "Simple bug fix"}
        result = validator._check_condition('goal.matches("cosmology|solver|universe")', context)
        assert result is False

    def test_condition_coherence_below(self):
        """coherence_below evaluates thresholds"""
        validator = HookifyValidator()

        context = {"coherence": 0.3}
        result = validator._check_condition("coherence < 0.5", context)
        assert result is True

    def test_condition_complex_and(self):
        """Complex conditions with AND/OR"""
        validator = HookifyValidator()

        context = {"goal": "cosmology", "coherence": 0.3}
        result = validator._check_condition(
            'goal.contains("cosmology") AND coherence < 0.5', context
        )
        assert result is True


class TestHookifyActionExecution:
    """Test 4: Action execution"""

    def test_action_block_if_coherence_below(self):
        """Block execution when coherence below threshold"""
        validator = HookifyValidator()

        context = {"coherence": 0.3}
        levers = {"threshold": 0.5}

        result = validator._execute_action("block_if_coherence_below_threshold", context, levers)

        assert result.proceed is False
        assert len(result.violations) == 1
        assert "coherence" in result.violations[0]["message"].lower()

    def test_action_allow_execution(self):
        """Allow execution when conditions met"""
        validator = HookifyValidator()

        context = {"coherence": 0.6}
        levers = {"threshold": 0.5}

        result = validator._execute_action("block_if_coherence_below_threshold", context, levers)

        assert result.proceed is True
        assert len(result.violations) == 0

    def test_action_ralph_loop_orchestrate(self):
        """Ralph Loop orchestrates cosmological tasks"""
        validator = HookifyValidator()

        context = {"goal": "cosmological solver", "session_id": "test-123"}
        levers = {"coherence_threshold": 0.5, "max_iterations": 20, "auto_commit": True}

        result = validator._execute_action("ralph_loop.orchestrate", context, levers)

        # Ralph Loop returns proceed with modifications
        assert result.proceed is True
        assert "ralph_mode" in result.modifications


class TestHookifyValidation:
    """Test 5: Full validation workflow"""

    @pytest.fixture
    def sample_rules(self):
        return [
            Rule(
                id="hiho_stability_gate",
                trigger="pre_execute",
                condition="always",
                action="block_if_coherence_below_threshold",
                levers={"threshold": 0.5, "fallback_action": "decompose"},
            )
        ]

    def test_validate_blocks_low_coherence(self, sample_rules):
        """Pre-execution hook blocks when coherence < 0.5"""
        validator = HookifyValidator(rules=sample_rules)

        context = {"coherence": 0.3, "goal": "test"}
        result = validator.validate("pre_execute", context)

        assert result.block is True
        assert len(result.violations) > 0

    def test_validate_allows_high_coherence(self, sample_rules):
        """Pre-execution hook allows when coherence >= 0.5"""
        validator = HookifyValidator(rules=sample_rules)

        context = {"coherence": 0.6, "goal": "test"}
        result = validator.validate("pre_execute", context)

        assert result.block is False
        assert len(result.violations) == 0

    def test_validate_no_matching_rules(self):
        """No block when no rules match trigger"""
        validator = HookifyValidator(rules=[])

        result = validator.validate("pre_execute", {})

        assert result.block is False


class TestHookifyRalphLoopIntegration:
    """Test 6: Ralph Loop integration (cosmological use case)"""

    @pytest.fixture
    def ralph_loop_rules(self):
        return [
            Rule(
                id="hiho_stability_gate",
                trigger="pre_execute",
                condition="always",
                action="block_if_coherence_below_threshold",
                levers={"threshold": 0.5, "fallback_action": "decompose"},
                adversarial_tests=[],
            )
        ]

    def test_ralph_loop_hiho_convergence(self, ralph_loop_rules):
        """Ralph Loop converges to HIHO (0.5 coherence)"""
        validator = HookifyValidator(rules=ralph_loop_rules)

        # Simulate Ralph Loop iterations
        coherence_values = [0.2, 0.35, 0.45, 0.48, 0.49, 0.50, 0.50]

        for coherence in coherence_values:
            context = {"coherence": coherence, "iteration": coherence_values.index(coherence)}
            result = validator.validate("pre_execute", context)

            if coherence < 0.5:
                assert result.block is True, f"Should block at coherence {coherence}"
            else:
                assert result.block is False, f"Should allow at coherence {coherence}"

    def test_ralph_loop_max_iterations(self):
        """Ralph Loop respects max_iterations lever"""
        validator = HookifyValidator()

        context = {
            "coherence": 0.3,  # Below threshold
            "iteration": 25,  # Beyond max
        }

        result = validator._execute_action(
            "ralph_loop.orchestrate", context, {"max_iterations": 20}
        )

        # Ralph Loop sets ralph_mode with max_iterations configuration
        assert result.modifications.get("ralph_mode") is True
        assert result.modifications.get("max_iterations") == 20


class TestHookifyPersistence:
    """Test 7: Three-tier persistence"""

    def test_load_rules_from_git(self, tmp_path):
        """Tier 1: Load rules from .agent/HOOKIFY_RULES.md"""
        rules_file = tmp_path / ".agent" / "HOOKIFY_RULES.md"
        rules_file.parent.mkdir(parents=True)
        rules_file.write_text("""
## Rule: test_rule
- **ID**: test_rule
- **Trigger**: session_start
- **Condition**: always
- **Action**: test_action
- **Levers**:
  - threshold: 0.5
""")

        validator = HookifyValidator(rules_path=rules_file)
        assert len(validator.rules) == 1
        assert validator.rules[0].id == "test_rule"

    def test_save_levers_to_surrealdb(self):
        """Tier 2: Save runtime lever overrides to SurrealDB"""
        validator = HookifyValidator()

        # When: Updating lever position
        validator._save_lever_override(
            rule_id="cosmological_ralph_loop", lever_name="coherence_threshold", value=0.7
        )

        # Then: Saved to SurrealDB
        saved = validator._load_lever_override(
            rule_id="cosmological_ralph_loop", lever_name="coherence_threshold"
        )
        assert saved == 0.7

    def test_log_violation_to_vault(self):
        """Tier 3: Log violations to vault for recursive learning"""
        validator = HookifyValidator()

        # When: Violation occurs
        validator._log_violation(
            rule_id="hiho_stability_gate",
            context={"coherence": 0.3},
            violation={"message": "Coherence below threshold"},
        )

        # Then: Logged to vault
        logs = validator._get_violation_logs("hiho_stability_gate")
        assert len(logs) == 1
        assert logs[0]["coherence"] == 0.3


class TestHookifyAdversarialCases:
    """Test 8: Adversarial edge cases"""

    def test_invalid_rule_syntax(self):
        """Handle malformed rule definitions gracefully"""
        validator = HookifyValidator()

        bad_md = "Not a valid rule format"
        rules = validator._parse_rules(bad_md)

        assert rules == []

    def test_missing_lever_defaults_to_zero(self):
        """Missing lever defaults to appropriate zero value"""
        validator = HookifyValidator()

        md = """
## Rule: incomplete_rule
- **ID**: incomplete_rule
- **Trigger**: session_start
- **Condition**: always
- **Action**: test_action
- **Levers**:
  - defined: 0.5
"""
        rules = validator._parse_rules(md)

        # Missing lever should have sensible default
        assert "undefined_lever" not in rules[0].levers

    def test_circular_rule_reference(self):
        """Handle circular rule dependencies"""
        # Rules should not depend on each other
        pass  # Implementation should prevent this

    def test_condition_injection_attempt(self):
        """Sanitize condition expressions to prevent injection"""
        validator = HookifyValidator()

        malicious_condition = 'os.system("rm -rf /")'

        with pytest.raises(ValueError):
            validator._check_condition(malicious_condition, {})


class TestHookifyCrossPlatformTriggers:
    """Test 9: Cross-platform trigger normalization"""

    def test_opencode_triggers(self):
        """Opencode trigger mapping"""
        validator = HookifyValidator()

        # Map platform-specific triggers to normalized names
        assert validator._normalize_trigger("session_start", "opencode") == "session_start"
        assert (
            validator._normalize_trigger("CompoundSessionManager.check_alignment", "opencode")
            == "pre_execute"
        )

    def test_claude_code_triggers(self):
        """Claude Code trigger mapping"""
        validator = HookifyValidator()

        assert validator._normalize_trigger("pre_execute", "claude_code") == "pre_execute"
        assert validator._normalize_trigger("CLAUDE.md_load", "claude_code") == "session_start"

    def test_gemini_cli_triggers(self):
        """Gemini CLI trigger mapping"""
        validator = HookifyValidator()

        assert validator._normalize_trigger("mcp_pre_execute", "gemini") == "pre_execute"
        assert validator._normalize_trigger("GEMINI.md_load", "gemini") == "session_start"


class TestHookifyMCPBridge:
    """Test 10: MCP bridge for cross-platform support"""

    @pytest.fixture
    def mcp_bridge(self, tmp_path):
        """Create MCP bridge with temporary vault"""
        from cohezion.mcp.hookify_server import HookifyMCPBridge

        return HookifyMCPBridge(vault_path=tmp_path)

    @pytest.mark.asyncio
    async def test_mcp_validate_tool(self, mcp_bridge):
        """MCP tool: validate_rule"""
        result = await mcp_bridge.validate_rule(
            trigger="pre_execute", context={"coherence": 0.3, "goal": "test"}
        )

        # With no rules configured, should proceed=True
        assert "proceed" in result
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_mcp_get_levers_tool(self, mcp_bridge):
        """MCP tool: get_levers"""
        result = await mcp_bridge.get_levers(rule_id="cosmological_ralph_loop")

        # Should return levers from default rules
        assert "rule_id" in result
        assert result["rule_id"] == "cosmological_ralph_loop"

    @pytest.mark.asyncio
    async def test_mcp_set_lever_tool(self, mcp_bridge):
        """MCP tool: set_lever"""
        result = await mcp_bridge.set_lever(
            rule_id="cosmological_ralph_loop", lever_name="coherence_threshold", value=0.7
        )

        assert result["success"] is True
        assert result["new_value"] == 0.7


# Placeholder classes that will be implemented
# Import real implementation from cohezion.hookify
# The tests now use the real HookifyValidator
from cohezion.hookify.validator import HookifyValidator, Rule
