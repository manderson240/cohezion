import gymnasium as gym
from gymnasium import spaces
import numpy as np
import arc_agi
from arcengine import GameAction, GameState

class ARCGymEnv(gym.Env):
    """Gymnasium wrapper for ARC-AGI-3 Interactive Environment."""
    def __init__(self, game_id="ls20", render_mode="terminal"):
        super().__init__()
        self.arcade = arc_agi.Arcade()
        self.game_id = game_id
        self.render_mode = render_mode
        self.env = None
        
        # Grid: max 64x64, values 0-15
        self.observation_space = spaces.Box(low=0, high=15, shape=(64, 64), dtype=np.uint8)
        
        # Action space: 7 actions (ACTION1-ACTION7)
        self.action_space = spaces.Dict({
            "action": spaces.Discrete(7),
            "x": spaces.Discrete(64),
            "y": spaces.Discrete(64)
        })

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.env = self.arcade.make(self.game_id, render_mode=self.render_mode)
        res = self.env.reset()
        return self._process_obs(res), self._process_info(res)

    def step(self, action):
        actions = [
            GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3,
            GameAction.ACTION4, GameAction.ACTION5, GameAction.ACTION6,
            GameAction.ACTION7
        ]
        
        # Handle both dict and integer actions (for random sampling)
        if isinstance(action, (int, np.integer)):
            game_action = actions[action % 7]
            action_data = {"x": 32, "y": 32} # Default to center for ACTION6 if not provided
        else:
            game_action = actions[action["action"]]
            action_data = {"x": int(action.get("x", 32)), "y": int(action.get("y", 32))}
        
        res = self.env.step(game_action, data=action_data)
        
        obs = self._process_obs(res)
        reward = 1.0 if res.state == GameState.WIN else 0.0
        terminated = res.state in [GameState.WIN, GameState.GAME_OVER]
        truncated = False
        info = self._process_info(res)
        
        return obs, reward, terminated, truncated, info

    def _process_obs(self, res):
        if not res.frame or len(res.frame) == 0:
            return np.zeros((64, 64), dtype=np.uint8)
            
        grid = np.array(res.frame[0], dtype=np.uint8)
        h, w = grid.shape
        padded_grid = np.zeros((64, 64), dtype=np.uint8)
        padded_grid[:min(h, 64), :min(w, 64)] = grid[:64, :64]
        return padded_grid

    def _process_info(self, res):
        return {
            "state": str(res.state),
            "game_id": res.game_id,
            "levels_completed": res.levels_completed,
            "win_levels": res.win_levels
        }

    def render(self):
        if self.env:
            self.env.render()

    def close(self):
        if self.env:
            self.env.close()
