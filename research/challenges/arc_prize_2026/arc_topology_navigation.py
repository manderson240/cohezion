import torch
import torch.optim as optim
import numpy as np
import random
from arc_gym_wrapper import ARCGymEnv
from arc_jepa import ARCWorldModel
from arc_axiomatic import ARCAxiomaticProjector, compute_hiho_stability
from cohezion.swarm.topological_router import TopologicalRouter, TopologicalRegime
from cohezion.physics.spinor import SpinorState

class ARCTopologicalNavigator:
    """Navigator that uses Topological Routing, JEPA, and 12D Axiomatic Manifolds."""
    def __init__(self, game_id="ls20", device="cpu"):
        self.game_id = game_id
        self.device = device
        self.env = ARCGymEnv(game_id=game_id, render_mode="headless")
        self.model = ARCWorldModel().to(device)
        self.projector = ARCAxiomaticProjector().to(device)
        self.optimizer = optim.Adam(list(self.model.parameters()) + list(self.projector.parameters()), lr=1e-3)
        self.router = TopologicalRouter(min_trajectory_length=5)
        self.surprise_history = []
        self.stability_history = []
        
        # Cohezion Special: Initialize Logical Spinor (HIHO state)
        self.spinor = SpinorState.hiho()
        
    def run_session(self, num_steps=50):
        print(f"Starting Axiomatic-Topological navigation on game: {self.game_id}")
        obs, info = self.env.reset()
        
        for i in range(num_steps):
            # 1. Encode current state to 256D and 12D
            grid_curr = torch.from_numpy(obs).unsqueeze(0).unsqueeze(0).to(self.device)
            step_norm = i / num_steps
            
            with torch.no_grad():
                z_curr_tensor = self.model.encoder(grid_curr)
                axioms_curr = self.projector(z_curr_tensor, step_normalized=step_norm)
                stability = compute_hiho_stability(axioms_curr)
                self.stability_history.append(stability)
                
                z_curr = z_curr_tensor.squeeze(0).cpu().numpy()
            
            # 2. Record trajectory point and analyze topology
            self.router.record_trajectory_point(self.game_id, z_curr)
            topo = self.router.analyze_agent(self.game_id)
            
            # 3. Action Selection (Axiom-Gated Surprise)
            x_eval, y_coord_eval = 32, 32 
            z_preds = self.model.evaluate_actions(grid_curr, x_eval, y_coord_eval)
            
            # Predict axiomatic states for potential futures
            axioms_preds = self.projector(z_preds, step_normalized=(i+1)/num_steps)
            
            action_idx = self._select_action_axiomatic(z_preds, axioms_preds, topo)
            
            # Update Spinor: Rotate logic based on selected action (simulated precession)
            # This represents the "Logical Spin" of the reasoning agent
            self.spinor = self.spinor.precess(np.pi / 4 * (action_idx + 1))
            
            action_dict = {
                "action": action_idx,
                "x": random.randint(0, 63) if topo.regime == TopologicalRegime.EXPLORE else 32,
                "y": random.randint(0, 63) if topo.regime == TopologicalRegime.EXPLORE else 32
            }
            
            # 4. Step environment
            obs_next, reward, terminated, truncated, info = self.env.step(action_dict)
            grid_next = torch.from_numpy(obs_next).unsqueeze(0).unsqueeze(0).to(self.device)
            
            # 5. Measure Actual Surprise
            actual_surprise = self.model.compute_surprise(z_preds[action_idx].unsqueeze(0), grid_next)
            self.surprise_history.append(actual_surprise)
            
            # 6. Online JEPA Update with Stability Loss
            action_t = torch.tensor([action_dict["action"]]).to(self.device)
            x_t = torch.tensor([action_dict["x"]]).to(self.device)
            y_t = torch.tensor([action_dict["y"]]).to(self.device)
            
            self.optimizer.zero_grad()
            z_pred, jepa_loss = self.model(grid_curr, action_t, x_t, y_t, grid_next)
            
            # Auxiliary Stability Loss: Minimize distance to 0.5 Coherence (HIHO)
            axioms_pred = self.projector(z_pred, step_normalized=(i+1)/num_steps)
            stability_loss = torch.mean((torch.sigmoid(axioms_pred) - 0.5)**2)
            
            total_loss = jepa_loss + 0.1 * stability_loss
            total_loss.backward()
            self.optimizer.step()
            self.model._update_target_encoder(tau=0.01)
            
            if (i + 1) % 10 == 0:
                avg_surp = np.mean(self.surprise_history[-10:])
                avg_stab = np.mean(self.stability_history[-10:])
                print(f"Step {i+1}/{num_steps}: Regime={topo.regime.value}, Loss={total_loss.item():.6f}, Stability={avg_stab:.4f}, Spinor={self.spinor.charge_polarity:.3f}")
            
            obs = obs_next
            if terminated or truncated:
                obs, info = self.env.reset()
                self.spinor = SpinorState.hiho() # Reset to balance on reset
                
        print("Axiomatic-Topological session complete.")

    def _select_action_axiomatic(self, z_preds, axioms_preds, topo):
        """
        Action selection constrained by the 12D Manifold.
        Prioritizes high-stability transitions in EXPLOIT mode,
        and high-information (unstable but coherent) transitions in EXPLORE mode.
        """
        # Calculate predicted stability for all actions
        stabilities = []
        for ax in axioms_preds:
            stabilities.append(compute_hiho_stability(ax.unsqueeze(0)))
        
        # Novelty scores (as before)
        history = np.array(self.router._agent_trajectories.get(self.game_id, []))
        if len(history) == 0:
            return random.randint(0, 6)
            
        z_preds_np = z_preds.cpu().numpy()
        novelty_scores = []
        for zp in z_preds_np:
            dists = np.linalg.norm(history - zp, axis=1)
            novelty_scores.append(np.min(dists))
            
        # Combine Stability and Novelty
        combined_scores = []
        for s, n in zip(stabilities, novelty_scores):
            if topo.regime == TopologicalRegime.EXPLORE:
                # In EXPLORE: We want high novelty but MINIMAL total instability 
                # (explore near the boundary of the manifold)
                score = n * s 
            else:
                # In EXPLOIT: We want high stability (stay in the precipitated region)
                score = s
            combined_scores.append(score)
            
        return int(np.argmax(combined_scores))

if __name__ == "__main__":
    nav = ARCTopologicalNavigator()
    nav.run_session()
