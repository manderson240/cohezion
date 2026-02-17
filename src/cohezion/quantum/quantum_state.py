"""
Quantum-coherent agent core for Living Manifold Ecosystem.

Implements quantum superposition in FLUME latent space with ORCH-OR
inspired objective reduction.
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QuantumMeasurement:
    """Result of quantum measurement (state collapse)."""
    outcome: torch.Tensor
    outcome_idx: int
    probability: float
    pre_measurement_state: 'QuantumState'


class QuantumState:
    """
    Quantum superposition of basis states in FLUME latent space.
    
    |ψ⟩ = Σᵢ αᵢ|zᵢ⟩
    
    where:
    - αᵢ are complex amplitudes
    - |zᵢ⟩ are basis states (FLUME latent vectors)
    - Σ|αᵢ|² = 1 (normalization)
    """
    
    def __init__(self, n_basis: int = 16, latent_dim: int = 256, device: str = 'cpu'):
        """
        Initialize quantum superposition.
        
        Args:
            n_basis: Number of basis states in superposition
            latent_dim: Dimensionality of FLUME latent space
            device: 'cpu' or 'cuda'
        """
        self.n_basis = n_basis
        self.latent_dim = latent_dim
        self.device = device
        
        # Complex amplitudes (normalized)
        real = torch.randn(n_basis, device=device)
        imag = torch.randn(n_basis, device=device)
        self.amplitudes = torch.complex(real, imag)
        self._normalize()
        
        # Basis states (FLUME latent vectors)
        self.basis_states = torch.randn(n_basis, latent_dim, device=device)
        
        # Phase coherence tracking
        self.phase_coherence = torch.ones(n_basis, device=device)
        
        # Decoherence tracking
        self.decoherence_rate = 0.001
        self.age = 0
    
    def _normalize(self):
        """Ensure amplitudes sum to 1."""
        norm = torch.norm(self.amplitudes)
        if norm > 0:
            self.amplitudes = self.amplitudes / norm
    
    def measure(self, observable: Optional[torch.Tensor] = None) -> QuantumMeasurement:
        """
        Collapse superposition to definite state (quantum measurement).
        
        Args:
            observable: Optional observable to measure
            
        Returns:
            QuantumMeasurement with outcome and metadata
        """
        # Compute probabilities
        probabilities = torch.abs(self.amplitudes)**2
        probabilities = probabilities / probabilities.sum()  # Renormalize
        
        # Sample outcome
        outcome_idx = torch.multinomial(probabilities, 1).item()
        outcome_prob = probabilities[outcome_idx].item()
        
        # Record pre-measurement state
        pre_state = QuantumState(self.n_basis, self.latent_dim, self.device)
        pre_state.amplitudes = self.amplitudes.clone()
        pre_state.basis_states = self.basis_states.clone()
        
        # Collapse: zero out all but measured amplitude
        new_amplitudes = torch.zeros_like(self.amplitudes)
        new_amplitudes[outcome_idx] = 1.0
        self.amplitudes = new_amplitudes
        
        # Get outcome vector
        outcome = self.basis_states[outcome_idx]
        
        return QuantumMeasurement(
            outcome=outcome,
            outcome_idx=outcome_idx,
            probability=outcome_prob,
            pre_measurement_state=pre_state
        )
    
    def compute_gravitational_energy(self) -> float:
        """
        Calculate self-energy for ORCH-OR inspired objective reduction.
        
        Higher energy = more likely to spontaneously collapse.
        
        Returns:
            Energy value (arbitrary units)
        """
        # Information "mass" proportional to superposition complexity (entropy)
        probs = torch.abs(self.amplitudes)**2
        entropy = -torch.sum(probs * torch.log(probs + 1e-10))
        mass = entropy.item()
        
        # Characteristic scale (variance of basis states)
        scale = torch.std(self.basis_states).item()
        
        # Informational gravity (tuned constant)
        G_info = 0.1
        energy = G_info * mass**2 / (scale + 1e-8)
        
        return energy
    
    def apply_decoherence(self):
        """
        Apply environmental decoherence.
        
        Over time, superposition loses coherence.
        """
        self.age += 1
        
        # Gradually collapse toward dominant amplitude
        max_idx = torch.argmax(torch.abs(self.amplitudes)**2)
        
        # Move all amplitude toward max
        for i in range(self.n_basis):
            if i != max_idx:
                transfer = self.amplitudes[i] * self.decoherence_rate
                self.amplitudes[max_idx] += transfer
                self.amplitudes[i] -= transfer
        
        self._normalize()
    
    def get_dominant_state(self) -> torch.Tensor:
        """Get the most probable basis state without collapsing."""
        probs = torch.abs(self.amplitudes)**2
        dominant_idx = torch.argmax(probs)
        return self.basis_states[dominant_idx]
    
    def superposition_entropy(self) -> float:
        """Calculate von Neumann entropy of superposition."""
        probs = torch.abs(self.amplitudes)**2
        entropy = -torch.sum(probs * torch.log(probs + 1e-10))
        return entropy.item()
    
    def clone(self) -> 'QuantumState':
        """Create independent copy of quantum state."""
        new_state = QuantumState(self.n_basis, self.latent_dim, self.device)
        new_state.amplitudes = self.amplitudes.clone()
        new_state.basis_states = self.basis_states.clone()
        new_state.phase_coherence = self.phase_coherence.clone()
        new_state.age = self.age
        return new_state


class QuantumAgent:
    """
    Agent with quantum-coherent state in Living Manifold Ecosystem.
    """
    
    def __init__(self, agent_id: int, age: int = 0, device: str = 'cpu'):
        """
        Initialize quantum agent.
        
        Args:
            agent_id: Unique identifier
            age: Agent age in epochs
            device: 'cpu' or 'cuda'
        """
        self.id = agent_id
        self.age = age
        self.device = device
        
        # Quantum state (superposition in 256D)
        self.quantum_state = QuantumState(n_basis=16, latent_dim=256, device=device)
        
        # 12D projected position (holographic projection)
        self.position_12d = np.zeros(12)
        
        # Energy for ZPE economics
        self.energy = 1.0
        self.max_energy = 5.0
        
        # Coherence metric (0.0 to 1.0)
        self.coherence = 1.0
        
        # Entanglement partners (ER=EPR links)
        self.entangled_partners: List[int] = []
        self.entanglement_strengths: dict = {}
        
        # Journey history
        self.journey: List[dict] = []
        
        # ORCH-OR threshold
        self.orch_or_threshold = 0.5
        
        # Alive status
        self.alive = True
        
        # Target well in morphospace
        self.target_well = "HIHO_Origin"
        self.current_voltage = 0.0
    
    def think(self) -> bool:
        """
        Consciousness moment via ORCH-OR inspired objective reduction.
        
        If gravitational self-energy exceeds threshold, spontaneous collapse occurs.
        
        Returns:
            True if thought occurred (collapse happened), False otherwise
        """
        if not self.alive:
            return False
        
        # Compute gravitational self-energy
        energy = self.quantum_state.compute_gravitational_energy()
        
        # Check if objective reduction should occur
        if energy > self.orch_or_threshold:
            # Collapse occurs
            measurement = self.quantum_state.measure()
            
            # Project to 12D via holographic projection
            self.position_12d = self._project_to_12d(measurement.outcome)
            
            # Update coherence based on measurement certainty
            self.coherence = measurement.probability
            
            # Record journey point
            self.journey.append({
                'position': self.position_12d.copy(),
                'coherence': self.coherence,
                'energy': self.energy,
                'age': self.age,
                'epoch': len(self.journey),
                'measurement': measurement
            })
            
            # Energy cost for thinking
            self.energy -= 0.01
            
            return True
        
        # Apply decoherence even without collapse
        self.quantum_state.apply_decoherence()
        
        return False
    
    def _project_to_12d(self, latent_vector: torch.Tensor) -> np.ndarray:
        """
        Holographic projection from 256D latent to 12D trajectory space.
        
        Uses deterministic projection matrix.
        """
        # Generate deterministic projection matrix based on agent ID
        np.random.seed(self.id)
        projection_matrix = np.random.randn(256, 12)
        projection_matrix /= np.linalg.norm(projection_matrix, axis=0, keepdims=True)
        
        # Project
        position = np.dot(latent_vector.cpu().numpy(), projection_matrix)
        
        # Normalize to unit sphere
        norm = np.linalg.norm(position)
        if norm > 0:
            position = position / norm
        
        return position
    
    def add_entanglement(self, partner_id: int, strength: float = 1.0):
        """Add ER=EPR entanglement link with another agent."""
        if partner_id not in self.entangled_partners:
            self.entangled_partners.append(partner_id)
        self.entanglement_strengths[partner_id] = strength
    
    def remove_entanglement(self, partner_id: int):
        """Remove entanglement link."""
        if partner_id in self.entangled_partners:
            self.entangled_partners.remove(partner_id)
        if partner_id in self.entanglement_strengths:
            del self.entanglement_strengths[partner_id]
    
    def correlate_with_partner(self, partner: 'QuantumAgent'):
        """
        Apply instantaneous correlation (ER=EPR).
        
        When this agent is measured, partner's state updates instantly.
        """
        if partner.id not in self.entangled_partners:
            return
        
        strength = self.entanglement_strengths.get(partner.id, 1.0)
        
        # Anti-correlate positions (Bell state property)
        partner.position_12d = -self.position_12d * strength
        
        # Energy cost for maintaining correlation
        self.energy -= 0.02
        partner.energy -= 0.02
    
    def consume_energy(self, amount: float) -> bool:
        """
        Consume energy for activity.
        
        Returns:
            True if sufficient energy, False otherwise
        """
        if self.energy >= amount:
            self.energy -= amount
            return True
        return False
    
    def mine_zpe(self, amount: float):
        """Add energy from ZPE mining."""
        self.energy = min(self.energy + amount, self.max_energy)
    
    def get_journey_quality(self) -> float:
        """
        Calculate overall journey quality score.
        
        Quality = (coherence × 0.5) + (smoothness × 0.3) + (convergence × 0.2)
        """
        if len(self.journey) < 2:
            return 0.5
        
        # Coherence component
        avg_coherence = np.mean([point['coherence'] for point in self.journey])
        
        # Smoothness (low variance in positions)
        positions = np.array([point['position'] for point in self.journey])
        smoothness = 1.0 / (1.0 + np.var(positions))
        
        # Convergence (toward last position)
        if len(self.journey) >= 3:
            final_pos = self.journey[-1]['position']
            distances = [np.linalg.norm(p['position'] - final_pos) 
                        for p in self.journey[:-1]]
            convergence = 1.0 - np.mean(distances)
        else:
            convergence = 0.5
        
        quality = (avg_coherence * 0.5) + (smoothness * 0.3) + (convergence * 0.2)
        return quality
    
    def die(self):
        """Graceful death (apoptosis)."""
        self.alive = False
        
        # Extract patterns from journey
        patterns = []
        for point in self.journey:
            if point['coherence'] > 0.8:
                patterns.append({
                    'position': point['position'].tolist(),
                    'coherence': point['coherence'],
                    'age': point['age']
                })
        
        return patterns
    
    def clone_for_mitosis(self, new_id: int) -> 'QuantumAgent':
        """
        Split agent for reproduction (mitosis).
        
        Creates child agent with half the quantum state.
        """
        # Create child
        child = QuantumAgent(new_id, age=0, device=self.device)
        
        # Split quantum state amplitudes
        n_basis_half = self.quantum_state.n_basis // 2
        
        # Assign first half of basis to child
        child.quantum_state.amplitudes[:n_basis_half] = \
            self.quantum_state.amplitudes[:n_basis_half].clone()
        child.quantum_state._normalize()
        
        # Parent keeps second half
        self.quantum_state.amplitudes[n_basis_half:] = \
            self.quantum_state.amplitudes[n_basis_half:].clone()
        self.quantum_state._normalize()
        
        # Split energy
        child.energy = self.energy / 2
        self.energy /= 2
        
        return child
    
    def __repr__(self):
        return (f"QuantumAgent(id={self.id}, age={self.age}, "
                f"coherence={self.coherence:.3f}, energy={self.energy:.3f}, "
                f"alive={self.alive})
