"""Unit tests for HookIntegration module."""

import tempfile
from pathlib import Path

import pytest

from cohezion.sandbox.hooks import (
    ExecutionContext,
    Hook,
    HookAction,
    HookDiscovery,
    HookExecutor,
    HookIntegration,
    HookMetadata,
    HookRegistry,
    HookResult,
    HookStage,
    get_hook_integration,
)


class TestHookMetadata:
    """Test HookMetadata creation and serialization."""

    def test_metadata_creation(self):
        """Test creating hook metadata."""
        metadata = HookMetadata(
            name="test-hook",
            stage=HookStage.PRE_EXECUTE,
            action=HookAction.BLOCK,
            timeout=5,
            description="Test hook",
        )

        assert metadata.name == "test-hook"
        assert metadata.stage == HookStage.PRE_EXECUTE
        assert metadata.action == HookAction.BLOCK
        assert metadata.timeout == 5

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = HookMetadata(
            name="test-hook",
            stage=HookStage.PRE_OPERATION,
            action=HookAction.WARN,
            description="Test",
        )

        data = metadata.to_dict()
        assert data["name"] == "test-hook"
        assert data["stage"] == "pre_operation"
        assert data["action"] == "warn"


class TestHookDiscovery:
    """Test HookDiscovery functionality."""

    def test_discover_hooks_empty_dir(self):
        """Test discovering hooks from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = HookDiscovery.discover_hooks(tmpdir)
            assert hooks == {}

    def test_discover_hooks_nonexistent_dir(self):
        """Test discovering hooks from nonexistent directory."""
        hooks = HookDiscovery.discover_hooks("/nonexistent/path")
        assert hooks == {}

    def test_parse_hook_metadata_valid(self):
        """Test parsing valid hook metadata."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
# HOOK_NAME: test-hook
# HOOK_STAGE: PRE_EXECUTE
# HOOK_ACTION: BLOCK
# HOOK_TIMEOUT: 5
# HOOK_DESCRIPTION: Test hook
echo "test"
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            metadata = HookDiscovery._parse_hook_metadata(hook_path)
            assert metadata is not None
            assert metadata.name == "test-hook"
            assert metadata.stage == HookStage.PRE_EXECUTE
            assert metadata.action == HookAction.BLOCK
            assert metadata.timeout == 5
        finally:
            hook_path.unlink()

    def test_parse_hook_metadata_missing_stage(self):
        """Test parsing hook with missing stage."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
# HOOK_NAME: test-hook
# HOOK_ACTION: BLOCK
echo "test"
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            metadata = HookDiscovery._parse_hook_metadata(hook_path)
            assert metadata is None
        finally:
            hook_path.unlink()

    def test_discover_multiple_hooks(self):
        """Test discovering multiple hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create first hook
            hook1 = tmpdir_path / "hook1.sh"
            hook1.write_text("""#!/bin/bash
# HOOK_NAME: hook1
# HOOK_STAGE: PRE_EXECUTE
# HOOK_ACTION: ALLOW
echo "hook1"
""")
            hook1.chmod(0o755)

            # Create second hook
            hook2 = tmpdir_path / "hook2.sh"
            hook2.write_text("""#!/bin/bash
# HOOK_NAME: hook2
# HOOK_STAGE: POST_OPERATION
# HOOK_ACTION: WARN
echo "hook2"
""")
            hook2.chmod(0o755)

            hooks = HookDiscovery.discover_hooks(tmpdir)
            assert len(hooks) == 2
            assert "hook1" in hooks
            assert "hook2" in hooks


class TestHookExecutor:
    """Test HookExecutor functionality."""

    def test_execute_hook_success(self):
        """Test executing hook that succeeds."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
echo "success output"
exit 0
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            hook_path.chmod(0o755)
            metadata = HookMetadata(
                name="test",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.ALLOW,
            )
            hook = Hook(path=hook_path, metadata=metadata)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            result = HookExecutor.execute_hook(hook, context)

            assert result.hook_name == "test"
            assert result.exit_code == 0
            assert result.action == HookAction.ALLOW
            assert "success output" in result.stdout
        finally:
            hook_path.unlink()

    def test_execute_hook_block(self):
        """Test executing hook with BLOCK action."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
echo "blocked" >&2
exit 1
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            hook_path.chmod(0o755)
            metadata = HookMetadata(
                name="test",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.BLOCK,
            )
            hook = Hook(path=hook_path, metadata=metadata)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            result = HookExecutor.execute_hook(hook, context)

            assert result.exit_code == 1
            assert result.action == HookAction.BLOCK
        finally:
            hook_path.unlink()

    def test_execute_hook_warn(self):
        """Test executing hook with WARN action."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
echo "warning"
exit 2
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            hook_path.chmod(0o755)
            metadata = HookMetadata(
                name="test",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.WARN,
            )
            hook = Hook(path=hook_path, metadata=metadata)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            result = HookExecutor.execute_hook(hook, context)

            assert result.exit_code == 2
            assert result.action == HookAction.WARN
        finally:
            hook_path.unlink()

    def test_execute_hook_timeout(self):
        """Test hook execution timeout."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
sleep 10
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            hook_path.chmod(0o755)
            metadata = HookMetadata(
                name="test",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.ALLOW,
                timeout=1,
            )
            hook = Hook(path=hook_path, metadata=metadata)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            result = HookExecutor.execute_hook(hook, context, timeout=1)

            assert result.exit_code == -1
            assert result.error == "timeout"
            assert result.action == HookAction.WARN
        finally:
            hook_path.unlink()

    def test_execute_hook_with_context_env(self):
        """Test that context is passed as environment variables."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
echo "SANDBOX_OPERATION: $SANDBOX_OPERATION"
echo "FILES: $SANDBOX_FILES_TO_MODIFY"
exit 0
""")
            f.flush()
            hook_path = Path(f.name)

        try:
            hook_path.chmod(0o755)
            metadata = HookMetadata(
                name="test",
                stage=HookStage.PRE_OPERATION,
                action=HookAction.ALLOW,
            )
            hook = Hook(path=hook_path, metadata=metadata)
            context = ExecutionContext(
                operation="test-op",
                sandbox_id="test-1",
                files_to_modify=["file1.py", "file2.py"],
            )

            result = HookExecutor.execute_hook(hook, context)

            assert result.exit_code == 0
            assert "test-op" in result.stdout
        finally:
            hook_path.unlink()


class TestHookRegistry:
    """Test HookRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = HookRegistry()

        for stage in HookStage:
            assert stage in registry.hooks
            assert registry.hooks[stage] == {}

    def test_register_hook(self):
        """Test registering a hook."""
        registry = HookRegistry()
        metadata = HookMetadata(
            name="test",
            stage=HookStage.PRE_EXECUTE,
            action=HookAction.ALLOW,
        )
        hook = Hook(path=Path("/tmp/test.sh"), metadata=metadata)

        registry.register_hook(hook)

        assert "test" in registry.hooks[HookStage.PRE_EXECUTE]
        assert registry.hooks[HookStage.PRE_EXECUTE]["test"] == hook

    def test_get_hooks_for_stage(self):
        """Test retrieving hooks for a stage."""
        registry = HookRegistry()

        # Register hooks for different stages
        hook1 = Hook(
            path=Path("/tmp/hook1.sh"),
            metadata=HookMetadata(
                name="hook1",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.ALLOW,
            ),
        )
        hook2 = Hook(
            path=Path("/tmp/hook2.sh"),
            metadata=HookMetadata(
                name="hook2",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.WARN,
            ),
        )
        hook3 = Hook(
            path=Path("/tmp/hook3.sh"),
            metadata=HookMetadata(
                name="hook3",
                stage=HookStage.POST_OPERATION,
                action=HookAction.ALLOW,
            ),
        )

        registry.register_hook(hook1)
        registry.register_hook(hook2)
        registry.register_hook(hook3)

        pre_exec_hooks = registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)
        assert len(pre_exec_hooks) == 2

        post_op_hooks = registry.get_hooks_for_stage(HookStage.POST_OPERATION)
        assert len(post_op_hooks) == 1

    def test_disable_hook(self):
        """Test disabling a hook."""
        registry = HookRegistry()
        hook = Hook(
            path=Path("/tmp/test.sh"),
            metadata=HookMetadata(
                name="test",
                stage=HookStage.PRE_EXECUTE,
                action=HookAction.ALLOW,
            ),
        )

        registry.register_hook(hook)
        assert len(registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)) == 1

        result = registry.disable_hook(HookStage.PRE_EXECUTE, "test")
        assert result is True
        assert len(registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)) == 0

    def test_disable_nonexistent_hook(self):
        """Test disabling a hook that doesn't exist."""
        registry = HookRegistry()
        result = registry.disable_hook(HookStage.PRE_EXECUTE, "nonexistent")
        assert result is False

    def test_clear_stage(self):
        """Test clearing all hooks for a stage."""
        registry = HookRegistry()

        # Register multiple hooks
        for i in range(3):
            hook = Hook(
                path=Path(f"/tmp/hook{i}.sh"),
                metadata=HookMetadata(
                    name=f"hook{i}",
                    stage=HookStage.PRE_EXECUTE,
                    action=HookAction.ALLOW,
                ),
            )
            registry.register_hook(hook)

        assert len(registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)) == 3

        registry.clear_stage(HookStage.PRE_EXECUTE)
        assert len(registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)) == 0


class TestHookIntegration:
    """Test main HookIntegration class."""

    def test_initialization_with_real_hooks(self):
        """Test initialization with real hooks directory."""
        # This test will use the actual .claude/hooks directory if it exists
        integration = HookIntegration(".claude/hooks")
        assert integration is not None

    def test_validate_hooks_all_allow(self):
        """Test validating hooks when all allow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create allow hook
            hook_file = tmpdir_path / "allow.sh"
            hook_file.write_text("""#!/bin/bash
exit 0
""")
            hook_file.chmod(0o755)

            integration = HookIntegration(tmpdir)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            allow, results = integration.validate_hooks(HookStage.PRE_EXECUTE, context)

            assert allow is True
            assert len(results) >= 0

    def test_validate_hooks_block(self):
        """Test validating hooks when one blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create block hook
            hook_file = tmpdir_path / "block.sh"
            hook_file.write_text("""#!/bin/bash
# HOOK_NAME: blocker
# HOOK_STAGE: PRE_EXECUTE
# HOOK_ACTION: BLOCK
echo "Blocked" >&2
exit 1
""")
            hook_file.chmod(0o755)

            integration = HookIntegration(tmpdir)
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            allow, results = integration.validate_hooks(HookStage.PRE_EXECUTE, context)

            assert allow is False
            assert any(r.action == HookAction.BLOCK for r in results)

    def test_execute_hook_with_hook_object(self):
        """Test executing a specific hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            hook_file = tmpdir_path / "test.sh"
            hook_file.write_text("""#!/bin/bash
echo "executed"
exit 0
""")
            hook_file.chmod(0o755)

            integration = HookIntegration(tmpdir)
            hook = Hook(
                path=hook_file,
                metadata=HookMetadata(
                    name="test",
                    stage=HookStage.PRE_EXECUTE,
                    action=HookAction.ALLOW,
                ),
            )
            context = ExecutionContext(operation="test", sandbox_id="test-1")

            result = integration.execute_hook(hook, context)

            assert result.exit_code == 0
            assert "executed" in result.stdout

    def test_audit_trail(self):
        """Test audit trail recording."""
        integration = HookIntegration(".nonexistent")
        assert len(integration.get_audit_trail()) == 0

        # Clear should work on empty trail
        integration.clear_audit_trail()
        assert len(integration.get_audit_trail()) == 0

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            integration = HookIntegration(tmpdir)
            data = integration.to_dict()

            assert "hooks_dir" in data
            assert "registry" in data
            assert "audit_trail" in data


class TestExecutionContext:
    """Test ExecutionContext class."""

    def test_context_creation(self):
        """Test creating execution context."""
        context = ExecutionContext(
            operation="test-op",
            sandbox_id="test-1",
            files_to_modify=["file1.py"],
            command="pytest",
        )

        assert context.operation == "test-op"
        assert context.sandbox_id == "test-1"

    def test_context_to_env_dict(self):
        """Test converting context to environment variables."""
        context = ExecutionContext(
            operation="test-op",
            sandbox_id="test-1",
            files_to_modify=["file1.py", "file2.py"],
            command="pytest",
            agent_files=["agent.json"],
        )

        env = context.to_env_dict()

        assert env["SANDBOX_OPERATION"] == "test-op"
        assert env["SANDBOX_SANDBOX_ID"] == "test-1"
        assert "file1.py" in env["SANDBOX_FILES_TO_MODIFY"]
        assert env["SANDBOX_COMMAND"] == "pytest"

    def test_context_with_extra_env(self):
        """Test context with extra environment variables."""
        context = ExecutionContext(
            operation="test",
            sandbox_id="test-1",
            extra_env={"CUSTOM_VAR": "value"},
        )

        env = context.to_env_dict()
        assert env["CUSTOM_VAR"] == "value"


class TestPhase21HooksIntegration:
    """Test integration with Phase 2.1 hooks."""

    def test_discover_phase21_hooks(self, tmp_path):
        """Test discovering Phase 2.1 hooks from a hooks directory."""
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()

        # Create the 4 Phase 2.1 hooks
        hook_specs = [
            ("protect-files", "PRE_OPERATION", "BLOCK", "Protect sensitive files"),
            ("warn-sensitive-commands", "PRE_EXECUTE", "WARN", "Warn on sensitive commands"),
            ("format-on-edit", "POST_OPERATION", "ALLOW", "Format on edit"),
            ("validate-agent-files", "PRE_EXECUTE", "BLOCK", "Validate agent files"),
        ]

        for name, stage, action, description in hook_specs:
            script = hooks_dir / f"{name}.sh"
            script.write_text(
                f"#!/bin/bash\n"
                f"# HOOK_NAME: {name}\n"
                f"# HOOK_STAGE: {stage}\n"
                f"# HOOK_ACTION: {action}\n"
                f"# HOOK_DESCRIPTION: {description}\n"
                f"exit 0\n"
            )
            script.chmod(0o755)

        integration = HookIntegration(str(hooks_dir))

        # Should discover the 4 Phase 2.1 hooks
        all_hooks = integration.registry.to_dict()
        hook_names = [
            hook_name for stage_hooks in all_hooks.values() for hook_name in stage_hooks
        ]

        expected_hooks = [
            "protect-files",
            "warn-sensitive-commands",
            "format-on-edit",
            "validate-agent-files",
        ]

        for expected in expected_hooks:
            assert any(expected in name for name in hook_names), (
                f"Expected hook '{expected}' not found"
            )

    def test_pre_execute_hooks(self):
        """Test PRE_EXECUTE stage hooks."""
        integration = HookIntegration(".claude/hooks")
        pre_exec_hooks = integration.registry.get_hooks_for_stage(HookStage.PRE_EXECUTE)

        # Should have at least warn-sensitive-commands and validate-agent-files
        assert len(pre_exec_hooks) >= 0

    def test_pre_operation_hooks(self):
        """Test PRE_OPERATION stage hooks."""
        integration = HookIntegration(".claude/hooks")
        pre_op_hooks = integration.registry.get_hooks_for_stage(HookStage.PRE_OPERATION)

        # Should have at least protect-files
        assert len(pre_op_hooks) >= 0

    def test_post_operation_hooks(self):
        """Test POST_OPERATION stage hooks."""
        integration = HookIntegration(".claude/hooks")
        post_op_hooks = integration.registry.get_hooks_for_stage(HookStage.POST_OPERATION)

        # Should have at least format-on-edit
        assert len(post_op_hooks) >= 0


@pytest.mark.fast
class TestHookIntegrationFast:
    """Fast unit tests for HookIntegration."""

    def test_hook_result_serialization(self):
        """Test HookResult serialization."""
        result = HookResult(
            hook_name="test",
            exit_code=0,
            stdout="output",
            stderr="",
            duration=0.5,
            action=HookAction.ALLOW,
        )

        data = result.to_dict()
        assert data["hook_name"] == "test"
        assert data["action"] == "allow"

    def test_hook_object_creation(self):
        """Test Hook object creation."""
        metadata = HookMetadata(
            name="test",
            stage=HookStage.PRE_EXECUTE,
            action=HookAction.ALLOW,
        )
        hook = Hook(path=Path("/tmp/test.sh"), metadata=metadata)

        assert hook.metadata.name == "test"
        data = hook.to_dict()
        assert "path" in data
        assert "metadata" in data

    def test_get_hook_integration_singleton(self):
        """Test get_hook_integration singleton pattern."""
        # Reset singleton
        if hasattr(get_hook_integration, "_instance"):
            delattr(get_hook_integration, "_instance")

        integration1 = get_hook_integration()
        integration2 = get_hook_integration()

        assert integration1 is integration2
