"""Example usage of ResearchAgent.

Demonstrates elegant integration with Cohezion infrastructure.
"""

from __future__ import annotations

from cohezion.research import ResearchAgent, ResearchConfig


def run_research_session():
    """Run autonomous research session.

    Example: Optimize FLUME training overnight.
    """
    # Configure research
    config = ResearchConfig(
        experiment_time_budget=300.0,  # 5 minutes
        max_experiments=100,
        target_metric="val_bpb",
        model_depth=8,
        vocab_size=8192,
    )

    # Create agent
    agent = ResearchAgent(config=config)

    # Run research session
    session = agent.run_session(max_experiments=10)  # Start with 10

    # Get results
    best = agent.get_best_result()
    print(f"Best result: {best}")

    return session


def run_with_custom_executor():
    """Use existing CompoundExecutor."""
    from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig

    # Create custom executor
    executor = CompoundExecutor(
        execute_fn=lambda task, ctx: ("output", {"metric": 1.0}),
        config=ExecutionConfig(max_retries=2),
    )

    # Use with ResearchAgent
    agent = ResearchAgent(
        config=ResearchConfig(),
        executor=executor,
    )

    return agent


if __name__ == "__main__":
    # Run example
    session = run_research_session()
    print(f"Completed {session.experiments_completed} experiments")
