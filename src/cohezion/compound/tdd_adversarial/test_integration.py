"""
Test script for TDD and Adversarial Review integration
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from cohezion.compound.tdd_adversarial.tdd_integration import get_tdd_integration
from cohezion.compound.tdd_adversarial.adversarial_review import (
    get_adversarial_review_system,
    ReviewPerspective
)
from cohezion.compound.tdd_adversarial.coordinator import get_tdd_adversarial_coordinator


async def test_tdd_integration():
    """Test the TDD integration system."""
    print("Testing TDD Integration...")
    
    project_root = Path.cwd()
    tdd_integration = get_tdd_integration(project_root)
    
    # Test getting TDD state
    session_id = "test_session_001"
    tdd_state = tdd_integration.get_or_create_tdd_state(session_id)
    print(f"✓ Created TDD state for session {session_id}")
    
    # Test getting metrics (should be empty initially)
    metrics = tdd_integration.get_tdd_metrics(session_id)
    print(f"✓ Got initial TDD metrics: {len(metrics)} items")
    
    print("✓ TDD Integration test completed\n")


async def test_adversarial_review():
    """Test the adversarial review system."""
    print("Testing Adversarial Review System...")
    
    project_root = Path.cwd()
    review_system = get_adversarial_review_system(project_root)
    
    # Test getting perspective state
    session_id = "test_session_001"
    perspective = ReviewPerspective.SECURITY
    perspective_state = review_system.get_or_create_perspective_state(perspective, session_id)
    print(f"✓ Created perspective state for {perspective.value}")
    
    # Test getting metrics (should be empty initially)
    metrics = review_system.get_adversarial_metrics(session_id)
    print(f"✓ Got initial adversarial metrics: {len(metrics)} items")
    
    print("✓ Adversarial Review test completed\n")


async def test_coordinator():
    """Test the TDD-Adversarial coordinator."""
    print("Testing TDD-Adversarial Coordinator...")
    
    project_root = Path.cwd()
    coordinator = get_tdd_adversarial_coordinator(project_root)
    
    # Test getting state
    session_id = "test_session_001"
    state = coordinator.get_or_create_state(session_id)
    print(f"✓ Created coordinator state for session {session_id}")
    
    # Test getting metrics (should be empty initially)
    metrics = coordinator.get_integration_metrics(session_id)
    print(f"✓ Got initial coordinator metrics: {len(metrics)} items")
    
    print("✓ Coordinator test completed\n")


async def test_workflow_initializer():
    """Test the workflow initializer."""
    print("Testing Workflow Initializer...")
    
    from cohezion.compound.daemon.workflow_initializer import get_workflow_initializer
    
    project_root = Path.cwd()
    initializer = get_workflow_initializer(project_root)
    
    # Test getting status
    status = initializer.get_status()
    print(f"✓ Got workflow initializer status: {status}")
    
    print("✓ Workflow Initializer test completed\n")


async def main():
    """Run all tests."""
    print("Running TDD and Adversarial Review Integration Tests\n")
    
    await test_tdd_integration()
    await test_adversarial_review()
    await test_coordinator()
    await test_workflow_initializer()
    
    print("All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
