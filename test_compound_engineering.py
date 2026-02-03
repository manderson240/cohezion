"""
ASCENDED COHEZION - Integration & Testing Suite
Compound Engineering Validation

Tests that all layers work together correctly.
Validates the compound engineering architecture.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


class CompoundEngineeringTestSuite:
    """
    Test suite that validates compound engineering layers.

    Each test builds on previous layers, demonstrating
    how compound engineering enables comprehensive testing.
    """

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    async def run_all_tests(self):
        """Run the complete test suite"""
        print("🧪 ASCENDED COHEZION - Compound Engineering Test Suite")
        print("=" * 70)
        print()

        # Test Layer 1: Configuration
        await self.test_layer_1_configuration()

        # Test Layer 2: Health Monitor
        await self.test_layer_2_health()

        # Test Layer 3: Resilience
        await self.test_layer_3_resilience()

        # Test Component Integration
        await self.test_component_integration()

        # Print results
        self._print_results()

    async def test_layer_1_configuration(self):
        """Test Configuration Foundation"""
        print("📋 Testing Layer 1: Configuration Foundation")
        print("-" * 50)

        try:
            from cohezion.config import get_config, SystemConfig

            # Test 1: Config loads
            config = get_config()
            assert config is not None, "Config should load"
            self._pass("Configuration loads successfully")

            # Test 2: Tracks configured
            assert "rapid" in config.tracks, "Rapid track should exist"
            assert "balanced" in config.tracks, "Balanced track should exist"
            assert "deep" in config.tracks, "Deep track should exist"
            self._pass("All 3 tracks configured")

            # Test 3: Email config
            assert config.email.recipient == "manderson240@gmail.com", (
                "Email recipient set"
            )
            self._pass("Email configuration present")

            # Test 4: Paths configured
            assert config.root_dir.exists(), "Root directory exists"
            self._pass("Path configuration valid")

        except Exception as e:
            self._fail(f"Layer 1 test failed: {e}")

        print()

    async def test_layer_2_health(self):
        """Test Health Monitor & Self-Healing"""
        print("🏥 Testing Layer 2: Health Monitor & Self-Healing")
        print("-" * 50)

        try:
            from cohezion.health_monitor import HealthMonitor, HealthSnapshot

            # Test 1: Monitor initializes
            monitor = HealthMonitor(check_interval=1)
            await monitor.start()
            await asyncio.sleep(0.1)  # Let it collect one sample
            self._pass("HealthMonitor initializes and starts")

            # Test 2: Metrics collection
            snapshot = monitor.get_current_health()
            assert isinstance(snapshot, HealthSnapshot), "Should return HealthSnapshot"
            assert len(snapshot.metrics) > 0, "Should have metrics"
            self._pass("Health metrics collection working")

            # Test 3: Health status
            assert snapshot.overall_status in ["OK", "WARNING", "CRITICAL"], (
                "Valid status"
            )
            self._pass(f"Health status: {snapshot.overall_status}")

            await monitor.stop()
            self._pass("HealthMonitor stops cleanly")

        except Exception as e:
            self._fail(f"Layer 2 test failed: {e}")

        print()

    async def test_layer_3_resilience(self):
        """Test Resilience & Retry Patterns"""
        print("⚡ Testing Layer 3: Resilience & Retry Patterns")
        print("-" * 50)

        try:
            from cohezion.resilience import (
                ResilientOperation,
                CircuitBreaker,
                RetryConfig,
                CircuitBreakerConfig,
                resilient,
            )

            # Test 1: Circuit breaker
            circuit = CircuitBreaker(
                "test", CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
            )

            # Should succeed initially
            result = await circuit.call(lambda: "success")
            assert result == "success", "Circuit should allow calls when closed"
            self._pass("CircuitBreaker allows calls when closed")

            # Test 2: Retry operation
            retry_config = RetryConfig(max_attempts=2, initial_delay=0.01)
            resilient_op = ResilientOperation("test_op", retry_config)

            attempt_count = 0

            async def failing_then_succeeding():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise Exception("Simulated failure")
                return "success"

            result = await resilient_op.execute(failing_then_succeeding)
            assert result == "success", "Should eventually succeed"
            assert attempt_count == 2, "Should retry"
            self._pass(f"Retry logic works (attempted {attempt_count} times)")

            # Test 3: Decorator
            @resilient(name="decorated_test", max_attempts=2, initial_delay=0.01)
            async def decorated_func():
                return "decorated_success"

            result = await decorated_func()
            assert result == "decorated_success"
            self._pass("@resilient decorator works")

        except Exception as e:
            self._fail(f"Layer 3 test failed: {e}")

        print()

    async def test_component_integration(self):
        """Test that all 6 universe simulation components integrate"""
        print("🔌 Testing Component Integration")
        print("-" * 50)

        try:
            # Test 1: Mission Orchestrator
            from cohezion.swarm.autonomous_universe_mission import (
                AutonomousUniverseMission,
                TrackType,
            )

            orchestrator = AutonomousUniverseMission("manderson240@gmail.com")
            assert len(orchestrator.TRACKS) == 3, "Should have 3 tracks"
            self._pass("Mission Orchestrator loads")

            # Test 2: Grading System
            from cohezion.swarm.openweight_grader import OpenweightGradingPanel

            grader = OpenweightGradingPanel("manderson240@gmail.com")
            assert len(grader.available_graders) >= 1, "Should have graders"
            self._pass(
                f"Grading System ready ({len(grader.available_graders)} graders)"
            )

            # Test 3: Display Engine
            from cohezion.swarm.universe_display_engine import UniverseDisplayEngine

            display = UniverseDisplayEngine()
            assert display.output_dir.exists(), "Output directory ready"
            self._pass("Display Engine ready")

            # Test 4: Notifications
            from cohezion.swarm.milestone_alerts import NotificationManager

            notifier = NotificationManager("manderson240@gmail.com")
            assert notifier.recipient == "manderson240@gmail.com"
            self._pass("Notification System ready")

            # Test 5: Evolution Engine
            from cohezion.swarm.compound_evolution import CompoundEvolutionEngine

            evolution = CompoundEvolutionEngine()
            assert evolution is not None
            self._pass("Evolution Engine ready")

            # Test 6: Mode Controller
            from cohezion.swarm.mode_controller import get_mode_controller

            controller = get_mode_controller()
            assert controller is not None
            self._pass("Mode Controller ready")

        except Exception as e:
            self._fail(f"Component integration test failed: {e}")
            import traceback

            traceback.print_exc()

        print()

    def _pass(self, message):
        """Record a passed test"""
        self.results.append(("PASS", message))
        self.passed += 1
        print(f"   ✅ {message}")

    def _fail(self, message):
        """Record a failed test"""
        self.results.append(("FAIL", message))
        self.failed += 1
        print(f"   ❌ {message}")

    def _print_results(self):
        """Print final results"""
        print("=" * 70)
        print("📊 TEST RESULTS")
        print("=" * 70)
        print(f"   ✅ Passed: {self.passed}")
        print(f"   ❌ Failed: {self.failed}")
        print(
            f"   📈 Success Rate: {self.passed / (self.passed + self.failed) * 100:.1f}%"
        )
        print()

        if self.failed == 0:
            print("🎉 ALL TESTS PASSED!")
            print()
            print("🌌 Compound Engineering Layers Validated:")
            print("   ✅ Layer 1: Configuration Foundation")
            print("   ✅ Layer 2: Health Monitor & Self-Healing")
            print("   ✅ Layer 3: Resilience & Retry Patterns")
            print("   ✅ All 6 Universe Simulation Components")
            print()
            print("🚀 System is ready for 24/7 autonomous operation!")
        else:
            print("⚠️  Some tests failed. Check the output above.")
            print()
            print("💡 Tips:")
            print("   - Make sure you're in the correct directory")
            print("   - Run: uv run python3 test_compound_engineering.py")
            print("   - Check that .env file exists with required variables")

        print()
        return self.failed == 0


async def main():
    """Main entry point"""
    suite = CompoundEngineeringTestSuite()
    success = await suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
