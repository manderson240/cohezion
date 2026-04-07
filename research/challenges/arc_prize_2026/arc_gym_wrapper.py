from __future__ import annotations
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import arc_agi
from arcengine import GameAction, GameState
from typing import Any, Dict, Optional, Tuple, Union

class ARCGymEnv(gym.Env):
    """Gymnasium wrapper for ARC-AGI-3 Interactive Environment."""
    def __init__(self, game_id: str = "ls20", render_mode: str = "terminal"):
        """
        Initializes the environment.
        
        Args:
            game_id: The ID of the ARC task to load.
            render_mode: Rendering mode (terminal, headless, etc).
        """
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

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Resets the environment.
        
        Args:
            seed: Random seed.
            options: Additional options.
            
        Returns:
            Tuple of (initial observation, info dict).
        """
        super().reset(seed=seed)
        self.env = self.arcade.make(self.game_id, render_mode=self.render_mode)
        res = self.env.reset()
        return self._process_obs(res), self._process_info(res)

    def step(self, action: Union[int, Dict[str, Any]]) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Performs a step in the environment.
        
        Args:
            action: The action to perform (integer or dict).
            
        Returns:
            Tuple of (observation, reward, terminated, truncated, info).
        """
        actions = [
            GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3,
            GameAction.ACTION4, GameAction.ACTION5, GameAction.ACTION6,
            GameAction.ACTION7
        ]
        
        # Handle both dict and integer actions (for random sampling)
        if isinstance(action, (int, np.integer)):
            game_action = actions[action % 7]
            action_data = {"x": 32, "y": 32} # Default to center
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

    def _process_obs(self, res: Any) -> np.ndarray:
        """Extracts and pads the grid from the raw result."""
        if not res.frame or len(res.frame) == 0:
            return np.zeros((64, 64), dtype=np.uint8)
            
        grid = np.array(res.frame[0], dtype=np.uint8)
        h, w = grid.shape
        padded_grid = np.zeros((64, 64), dtype=np.uint8)
        padded_grid[:min(h, 64), :min(w, 64)] = grid[:64, :64]
        return padded_grid

    def _process_info(self, res: Any) -> Dict[str, Any]:
        """Extracts metadata for the info dict."""
        return {
            "state": str(res.state),
            "game_id": res.game_id,
            "levels_completed": res.levels_completed,
            "win_levels": res.win_levels
        }

    def render(self):
        """Renders the environment."""
        if self.env:
            self.env.render()

    def close(self):
        """Safely closes the environment."""
        if self.env and hasattr(self.env, 'close'):
            self.env.close()
