import torch
import torch.optim as optim
import numpy as np
import random
from arc_gym_wrapper import ARCGymEnv
from arc_jepa import ARCWorldModel
from cohezion.swarm.topological_router import TopologicalRouter, TopologicalRegime

class ARCTopologicalNavigator:
    """Navigator that uses Topological Routing and JEPA World Models."""
    def __init__(self, game_id="ls20", device="cpu"):
        self.game_id = game_id
        self.device = device
        self.env = ARCGymEnv(game_id=game_id, render_mode="headless")
        self.model = ARCWorldModel().to(device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=1e-3)
        self.router = TopologicalRouter(min_trajectory_length=5)
        self.surprise_history = []
        
    def run_session(self, num_steps=50):
        print(f"Starting advanced topological navigation on game: {self.game_id}")
        obs, info = self.env.reset()
        
        for i in range(num_steps):
            # 1. Encode current state
            grid_curr = torch.from_numpy(obs).unsqueeze(0).unsqueeze(0).to(self.device)
            with torch.no_grad():
                z_curr_tensor = self.model.encoder(grid_curr)
                z_curr = z_curr_tensor.squeeze(0).cpu().numpy()
            
            # 2. Record trajectory point and analyze topology
            self.router.record_trajectory_point(self.game_id, z_curr)
            topo = self.router.analyze_agent(self.game_id)
            
            # 3. Action Selection (Surprise-Driven vs Exploitation)
            # Evaluate all 7 actions counterfactually
            # We assume a fixed x,y for evaluation or sample a few
            x_eval, y_coord_eval = 32, 32 
            z_preds = self.model.evaluate_actions(grid_curr, x_eval, y_coord_eval) # (7, 256)
            
            action_idx = self._select_action(z_preds, topo)
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
            
            # 6. Online JEPA Update
            action_t = torch.tensor([action_dict["action"]]).to(self.device)
            x_t = torch.tensor([action_dict["x"]]).to(self.device)
            y_t = torch.tensor([action_dict["y"]]).to(self.device)
            
            self.optimizer.zero_grad()
            _, loss = self.model(grid_curr, action_t, x_t, y_t, grid_next)
            loss.backward()
            self.optimizer.step()
            self.model._update_target_encoder(tau=0.01)
            
            if (i + 1) % 10 == 0:
                avg_surprise = np.mean(self.surprise_history[-10:])
                print(f"Step {i+1}/{num_steps}: Regime={topo.regime.value}, Loss={loss.item():.6f}, Avg Surprise={avg_surprise:.6f}")
            
            obs = obs_next
            if terminated or truncated:
                obs, info = self.env.reset()
                
        print("Navigation session complete.")

    def _select_action(self, z_preds, topo):
        """
        Select action based on topological regime.
        - EXPLOIT: Action leading to latent closest to existing clusters.
        - EXPLORE: Action leading to latent furthest from existing clusters (Predicted Surprise).
        - PIVOT: Random action to break the loop.
        """
        if topo.regime == TopologicalRegime.PIVOT:
            return random.randint(0, 6)
            
        # Get historical points for this agent
        history = np.array(self.router._agent_trajectories.get(self.game_id, []))
        if len(history) == 0:
            return random.randint(0, 6)
            
        # Compute distances from predicted latents to historical points
        z_preds_np = z_preds.cpu().numpy()
        
        # Simple novelty score: distance to nearest neighbor in history
        novelty_scores = []
        for zp in z_preds_np:
            dists = np.linalg.norm(history - zp, axis=1)
            novelty_scores.append(np.min(dists))
            
        if topo.regime == TopologicalRegime.EXPLORE:
            # Pick action with HIGHEST novelty (furthest from what we know)
            return int(np.argmax(novelty_scores))
        else:
            # EXPLOIT: Pick action with LOWEST novelty (stay in stable regime)
            return int(np.argmin(novelty_scores))

if __name__ == "__main__":
    nav = ARCTopologicalNavigator()
    nav.run_session()
