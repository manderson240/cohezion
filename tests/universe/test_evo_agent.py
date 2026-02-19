"""Tests for EVO Agent Model."""

from cohezion.universe.engine import AxiomaticState
from cohezion.universe.evo_agent import EVOAgent, EVOPopulation


class TestEVOAgent:
    """Test EVO Agent lifecycle."""

    def test_agent_creation(self):
        """Should create EVO agent with initial state."""
        initial_state = AxiomaticState()
        agent = EVOAgent(agent_id="agent-1", state=initial_state)
        assert agent.agent_id == "agent-1"
        assert agent.state == initial_state
        assert len(agent.coherence_history) > 0
        assert agent.memory_buffer == []

    def test_perceive_returns_local_environment(self):
        """Agent should perceive local environment state."""
        agent = EVOAgent(agent_id="agent-1")
        # Simple environment: just the agent's own state
        environment = {"local_field": 0.5, "nearby_agents": []}
        perception = agent.perceive(environment)
        assert "local_field" in perception
        assert "state" in perception
        assert perception["state"] == agent.state

    def test_decide_returns_action(self):
        """Agent should decide on action based on perception."""
        agent = EVOAgent(agent_id="agent-1")
        perception = {"local_field": 0.5, "state": agent.state}
        action = agent.decide(perception)
        assert "action_vector" in action
        assert len(action["action_vector"]) == 12  # 12D morphospace

    def test_act_updates_state(self):
        """Agent should update state based on action."""
        agent = EVOAgent(agent_id="agent-1")
        initial_coherence = agent.state.coherence_score()
        action = {"action_vector": [0.01] * 12}  # Small change
        agent.act(action)
        # State should have changed
        assert agent.state != AxiomaticState()
        # Coherence history should grow
        assert len(agent.coherence_history) > 1

    def test_coherence_history_tracking(self):
        """Agent should track coherence history over time."""
        agent = EVOAgent(agent_id="agent-1")
        initial_len = len(agent.coherence_history)

        # Perform multiple actions
        for _ in range(5):
            perception = agent.perceive({})
            action = agent.decide(perception)
            agent.act(action)

        # Coherence history should grow
        assert len(agent.coherence_history) == initial_len + 5

    def test_memory_buffer_stores_interactions(self):
        """Agent should store interactions in memory buffer."""
        agent = EVOAgent(agent_id="agent-1", memory_capacity=3)
        assert agent.memory_capacity == 3

        # Add interactions
        for i in range(5):
            agent.remember({"step": i, "data": f"event-{i}"})

        # Should only keep last 3 (capacity limit)
        assert len(agent.memory_buffer) == 3
        assert agent.memory_buffer[-1]["step"] == 4

    def test_hiho_coherence_tendency(self):
        """Agent coherence should tend toward HIHO target (0.5)."""
        agent = EVOAgent(agent_id="agent-1")
        # Start with deviated state
        agent.state.physics = 0.1
        agent.state.biology = 0.9

        # Run many steps to allow convergence
        for _ in range(50):
            perception = agent.perceive({})
            action = agent.decide(perception)
            agent.act(action)

        # Final coherence should be closer to HIHO (0.5) than initial
        final_coherence = agent.state.coherence_score()
        # HIHO coherence score is high when dimensions are near 0.5
        # So we expect final_coherence to be reasonably high (>0.5)
        assert final_coherence > 0.5

    def test_to_numpy_conversion(self):
        """Should convert AxiomaticState to numpy array."""
        agent = EVOAgent(agent_id="agent-1")
        arr = agent.to_numpy()
        assert len(arr) == 12
        assert arr.dtype == float

    def test_update_from_numpy(self):
        """Should update AxiomaticState from numpy array."""
        import numpy as np

        agent = EVOAgent(agent_id="agent-1")
        new_arr = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.2, 0.3])
        agent.update_from_numpy(new_arr)
        assert agent.state.spatial_x == 0.1
        assert agent.state.spatial_y == 0.2
        assert agent.state.precipitation == 0.3


class TestEVOPopulation:
    """Test EVO Population multi-agent dynamics."""

    def test_population_creation(self):
        """Should create population with multiple agents."""
        pop = EVOPopulation(num_agents=5)
        assert len(pop.agents) == 5
        assert all(agent.agent_id.startswith("evo-") for agent in pop.agents)

    def test_field_interactions(self):
        """Agents should interact via field influences."""
        pop = EVOPopulation(num_agents=3)
        # Get initial states
        initial_states = [agent.state.to_vector() for agent in pop.agents]

        # Step population (agents interact)
        pop.step()

        # States should have changed due to field interactions
        final_states = [agent.state.to_vector() for agent in pop.agents]
        assert initial_states != final_states

    def test_coherence_invariant_across_population(self):
        """Population coherence should tend toward HIHO (0.5)."""
        pop = EVOPopulation(num_agents=10)
        # Run multiple steps
        for _ in range(20):
            pop.step()

        # Check average coherence across population
        avg_coherence = sum(
            agent.state.coherence_score() for agent in pop.agents
        ) / len(pop.agents)
        # Should be reasonably high (agents stabilize near HIHO)
        assert avg_coherence > 0.4

    def test_get_agent_by_id(self):
        """Should retrieve agent by ID."""
        pop = EVOPopulation(num_agents=5)
        agent_id = pop.agents[2].agent_id
        retrieved = pop.get_agent(agent_id)
        assert retrieved == pop.agents[2]

    def test_get_agent_nonexistent_returns_none(self):
        """Should return None for nonexistent agent ID."""
        pop = EVOPopulation(num_agents=3)
        assert pop.get_agent("nonexistent-id") is None
