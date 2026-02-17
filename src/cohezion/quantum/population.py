"""
Leslie Matrix Population Dynamics
Age-structured population management for 10,000 quantum agents.
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
import logging

from .quantum_state import QuantumAgent

logger = logging.getLogger(__name__)


@dataclass
class DemographicMetrics:
    """Population demographic statistics."""
    total_population: int
    age_distribution: np.ndarray
    avg_age: float
    births_this_epoch: int
    deaths_this_epoch: int
    lambda_dominant: float
   juvenile_count: int
    mature_count: int
    elderly_count: int


class LeslieMatrix:
    """
    Age-structured population projection using Leslie matrix.
    
    60 age classes (epochs):
    - Ages 0-9: Juvenile (no reproduction)
    - Ages 10-50: Mature (reproducing)
    - Ages 51-59: Elderly (declining survival)
    """
    
    def __init__(self, n_age_classes: int = 60):
        self.n = n_age_classes
        
        # Fertility rates (mitosis probability by age)
        self.fertility = np.zeros(n_age_classes)
        ages = np.arange(n_age_classes)
        
        # Zero fertility for juveniles (ages 0-9)
        self.fertility[0:10] = 0.0
        
        # Gaussian fertility curve for mature (ages 10-50), peak at 30
        mature_ages = ages[10:51]
        self.fertility[10:51] = np.exp(-((mature_ages - 30)**2) / 200)
        self.fertility[10:51] /= self.fertility[10:51].sum()
        self.fertility[10:51] *= 0.3  # Scale so max ~0.3
        
        # Zero fertility for elderly (ages 51+)
        self.fertility[51:] = 0.0
        
        # Survival rates (probability to next age class)
        self.survival = np.ones(n_age_classes - 1) * 0.98
        
        # Declining survival after age 40
        self.survival[40:50] *= np.linspace(1.0, 0.7, 10)
        self.survival[50:] = 0.5  # 50% survival for elderly
        
        # Build Leslie matrix L
        self.L = np.zeros((n_age_classes, n_age_classes))
        self.L[0, :] = self.fertility  # First row = births
        self.L[1:, :-1] = np.diag(self.survival)  # Subdiagonal = survival
        
        # Compute eigenvalues and stable distribution
        self._compute_eigen_structure()
        
        logger.info(f"Leslie matrix initialized: λ = {self.lambda_dominant:.4f}")
    
    def _compute_eigen_structure(self):
        """Compute dominant eigenvalue and stable age distribution."""
        eigenvalues, eigenvectors = np.linalg.eig(self.L)
        
        # Find dominant eigenvalue (largest real part)
        idx = np.argmax(eigenvalues.real)
        self.lambda_dominant = eigenvalues[idx].real
        
        # Stable age distribution (dominant eigenvector)
        self.stable_distribution = np.abs(eigenvectors[:, idx].real)
        self.stable_distribution /= self.stable_distribution.sum()
        
        # Ensure non-negative
        self.stable_distribution = np.maximum(self.stable_distribution, 0)
        self.stable_distribution /= self.stable_distribution.sum()
    
    def project(self, population_vector: np.ndarray, n_steps: int = 1) -> np.ndarray:
        """
        Project population forward using Leslie matrix.
        
        Args:
            population_vector: Array of agent counts by age
            n_steps: Number of epochs to project
            
        Returns:
            Future population vector
        """
        result = population_vector.copy()
        
        for _ in range(n_steps):
            result = self.L @ result
        
        return result
    
    def tune_to_stable(self, target_lambda: float = 1.0) -> float:
        """
        Adjust fertility to achieve stable population growth rate.
        
        Args:
            target_lambda: Target growth rate (1.0 = stable)
            
        Returns:
            New lambda after tuning
        """
        if self.lambda_dominant > target_lambda + 0.01:
            # Growing too fast, reduce fertility
            adjustment = 0.95
            logger.info(f"λ = {self.lambda_dominant:.4f} > {target_lambda}, reducing fertility")
        elif self.lambda_dominant < target_lambda - 0.01:
            # Shrinking, increase fertility
            adjustment = 1.05
            logger.info(f"λ = {self.lambda_dominant:.4f} < {target_lambda}, increasing fertility")
        else:
            return self.lambda_dominant  # Already stable
        
        # Adjust fertility (only for reproductive ages)
        self.fertility[10:51] *= adjustment
        
        # Rebuild matrix
        self.L[0, :] = self.fertility
        
        # Recompute eigenstructure
        self._compute_eigen_structure()
        
        return self.lambda_dominant
    
    def get_age_category(self, age: int) -> str:
        """Categorize age into lifecycle stage."""
        if age < 10:
            return "juvenile"
        elif age < 50:
            return "mature"
        else:
            return "elderly"


class AgeStructuredPopulation:
    """
    Manager for 10,000 age-structured quantum agents.
    """
    
    def __init__(self, target_size: int = 10000, device: str = 'cpu'):
        """
        Initialize population with stable age distribution.
        
        Args:
            target_size: Target population size
            device: 'cpu' or 'cuda'
        """
        self.target_size = target_size
        self.device = device
        self.leslie = LeslieMatrix()
        
        # Initialize with stable age distribution
        n_by_age = (self.leslie.stable_distribution * target_size).astype(int)
        
        # Adjust to exactly hit target
        diff = target_size - n_by_age.sum()
        if diff > 0:
            # Add to largest age groups
            largest_indices = np.argsort(n_by_age)[-diff:]
            n_by_age[largest_indices] += 1
        elif diff < 0:
            # Remove from largest age groups
            largest_indices = np.argsort(n_by_age)[diff:]
            n_by_age[largest_indices] -= 1
        
        # Create agents
        self.agents: List[QuantumAgent] = []
        agent_id = 0
        
        for age, count in enumerate(n_by_age):
            for _ in range(count):
                agent = QuantumAgent(agent_id, age=age, device=device)
                self.agents.append(agent)
                agent_id += 1
        
        self.agent_counter = agent_id
        self.births_this_epoch = 0
        self.deaths_this_epoch = 0
        
        logger.info(f"Population initialized: {len(self.agents)} agents")
    
    def update_population(self) -> DemographicMetrics:
        """
        One epoch of population dynamics.
        
        1. Age all agents
        2. Check survival
        3. Handle reproduction
        4. Maintain carrying capacity
        
        Returns:
            DemographicMetrics for this epoch
        """
        self.births_this_epoch = 0
        self.deaths_this_epoch = 0
        
        # Step 1: Age and check survival
        surviving_agents = []
        
        for agent in self.agents:
            agent.age += 1
            
            # Check survival based on Leslie matrix
            if agent.age < self.leslie.n:
                survival_prob = self.leslie.survival[agent.age - 1]
                if np.random.random() < survival_prob:
                    surviving_agents.append(agent)
                else:
                    # Apoptosis
                    self._handle_apoptosis(agent)
                    self.deaths_this_epoch += 1
            else:
                # Max age reached
                self._handle_apoptosis(agent)
                self.deaths_this_epoch += 1
        
        # Step 2: Handle reproduction (mitosis)
        newborns = []
        
        for agent in surviving_agents:
            # Check reproduction conditions
            if (agent.age >= 10 and agent.age <= 50 and
                agent.energy > 2.0 and
                agent.coherence > 0.7):
                
                # Check fertility probability
                fertility_prob = self.leslie.fertility[agent.age]
                if np.random.random() < fertility_prob:
                    # Mitosis!
                    children = self._mitosis(agent)
                    newborns.extend(children)
                    self.births_this_epoch += len(children)
        
        # Step 3: Update agent list
        self.agents = surviving_agents + newborns
        
        # Step 4: Enforce carrying capacity
        if len(self.agents) > self.target_size:
            excess = len(self.agents) - self.target_size
            # Remove oldest agents first
            self.agents.sort(key=lambda a: a.age, reverse=True)
            
            for agent in self.agents[:excess]:
                self._handle_apoptosis(agent)
                self.deaths_this_epoch += 1
            
            self.agents = self.agents[excess:]
        
        # Step 5: Tune Leslie matrix if needed
        current_size = len(self.agents)
        if abs(current_size - self.target_size) > 500:
            self.leslie.tune_to_stable(1.0)
        
        # Return metrics
        return self._compute_metrics()
    
    def _mitosis(self, parent: QuantumAgent) -> List[QuantumAgent]:
        """
        Agent reproduction via 12D state splitting.
        
        Creates 2 child agents with split quantum state.
        
        Args:
            parent: Parent agent
            
        Returns:
            List of child agents (typically 2)
        """
        # Energy cost
        parent.energy /= 2
        
        # Split quantum state
        n_basis = len(parent.quantum_state.amplitudes) // 2
        
        # Child A
        child_a = QuantumAgent(self.agent_counter, age=0, device=self.device)
        child_a.quantum_state.amplitudes[:n_basis] = \
            parent.quantum_state.amplitudes[:n_basis].clone()
        child_a.quantum_state._normalize()
        child_a.energy = parent.energy
        child_a.coherence = parent.coherence * 0.9  # Slight degradation
        self.agent_counter += 1
        
        # Child B
        child_b = QuantumAgent(self.agent_counter, age=0, device=self.device)
        child_b.quantum_state.amplitudes[:n_basis] = \
            parent.quantum_state.amplitudes[n_basis:].clone()
        child_b.quantum_state._normalize()
        child_b.energy = parent.energy
        child_b.coherence = parent.coherence * 0.9
        self.agent_counter += 1
        
        return [child_a, child_b]
    
    def _handle_apoptosis(self, agent: QuantumAgent):
        """
        Graceful agent death with pattern extraction.
        
        Extracts high-quality patterns from agent's journey before death.
        """
        # Only extract if agent had coherent moments
        if agent.coherence > 0.6 or any(p.get('coherence', 0) > 0.6 for p in agent.journey):
            patterns = self._extract_patterns(agent)
            if patterns:
                self._log_patterns_to_vault(agent, patterns)
        
        # Mark as dead
        agent.alive = False
    
    def _extract_patterns(self, agent: QuantumAgent) -> List[Dict]:
        """
        Extract reusable patterns from agent's journey.
        
        Returns high-coherence trajectory segments.
        """
        patterns = []
        
        for point in agent.journey:
            if point.get('coherence', 0) > 0.8:
                patterns.append({
                    'position': point['position'].tolist(),
                    'coherence': point['coherence'],
                    'age': point.get('age', 0),
                    'epoch': point.get('epoch', 0)
                })
        
        return patterns
    
    def _log_patterns_to_vault(self, agent: QuantumAgent, patterns: List[Dict]):
        """Log extracted patterns to vault for future use."""
        try:
            # This will be integrated with vault system
            logger.info(f"Agent {agent.id}: Extracted {len(patterns)} patterns")
        except Exception as e:
            logger.error(f"Failed to log patterns: {e}")
    
    def _compute_metrics(self) -> DemographicMetrics:
        """Compute demographic statistics."""
        ages = [a.age for a in self.agents]
        
        # Age distribution
        age_dist = np.zeros(self.leslie.n)
        for age in ages:
            if age < self.leslie.n:
                age_dist[age] += 1
        
        # Age categories
        juvenile = sum(1 for a in self.agents if a.age < 10)
        mature = sum(1 for a in self.agents if 10 <= a.age < 50)
        elderly = sum(1 for a in self.agents if a.age >= 50)
        
        return DemographicMetrics(
            total_population=len(self.agents),
            age_distribution=age_dist,
            avg_age=np.mean(ages) if ages else 0,
            births_this_epoch=self.births_this_epoch,
            deaths_this_epoch=self.deaths_this_epoch,
            lambda_dominant=self.leslie.lambda_dominant,
            juvenile_count=juvenile,
            mature_count=mature,
            elderly_count=elderly
        )
    
    def get_agent_by_id(self, agent_id: int) -> QuantumAgent:
        """Find agent by ID."""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        raise ValueError(f"Agent {agent_id} not found")
    
    def get_demographics_summary(self) -> str:
        """Get human-readable demographics summary."""
        metrics = self._compute_metrics()
        
        summary = f"""
Population Demographics:
  Total: {metrics.total_population}
  Juvenile (0-9): {metrics.juvenile_count}
  Mature (10-49): {metrics.mature_count}
  Elderly (50+): {metrics.elderly_count}
  Average Age: {metrics.avg_age:.1f}
  
This Epoch:
  Births: {metrics.births_this_epoch}
  Deaths: {metrics.deaths_this_epoch}
  Growth Rate λ: {metrics.lambda_dominant:.4f}
        """
        
        return summary
