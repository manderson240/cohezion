# Genesis Environment Generation

## Agent Skill: Generate AI Training Environments

**Category**: AI Training Infrastructure  
**Scope**: RL Environment Generation  
**Compatibility**: Claude Code, Gemini CLI, Cursor, Antigravity  
**Author**: Cohezion Research Team  

---

## Mission

When asked to create training environments for reinforcement learning, automatically generate Gymnasium-compatible environments using the Genesis Engine physics framework.

This skill bridges natural language task descriptions to production-ready Python code with proper safety constraints, reward shaping, and HIHO (High Integration High Order) stability principles.

---

## Quick Reference

**Activation Patterns**:
- "Create a training environment for..."
- "Generate an RL environment where..."
- "Build a Gymnasium env that..."
- "Make a physics simulation for..."

**Default Output**: Python class inheriting from `gymnasium.Env`

---

## Workflow

### Phase 1: Parse Specification
1. Extract domain (robotics, web, game, reasoning)
2. Identify state/action dimensions
3. Determine success criteria
4. Flag safety constraints

### Phase 2: Generate Code
1. Create class structure with type hints
2. Define observation/action spaces
3. Implement physics (Lagrangian if applicable)
4. Add HIHO coherence tracking
5. Include reward shaping

### Phase 3: Validate
1. Syntax check via AST
2. gymnasium API compliance
3. Security scan (no forbidden patterns)
4. Test instantiation

---

## Golden Rules

### 1. Always Include HIHO Tracking
```python
self._coherence = 0.5  # Target equilibrium
def _compute_coherence(self) -> float:
    return 1.0 - abs(self._state.mean() - 0.5) * 2
```

### 2. Physics-First for Continuous Domains
Use Lagrangian dynamics when action space is continuous:
```python
from cohezion.physics.lagrangian import LagrangianDynamics
self._dynamics = LagrangianDynamics(metric, potential)
```

### 3. Safety Constraints Mandatory
Always check for and implement safety constraints:
```python
if self._unsafe_condition():
    return obs, -10.0, True, False, {"violation": "safety"}
```

### 4. Render Modes
Always implement at least rgb_array:
```python
metadata = {"render_modes": ["rgb_array", "human"]}
```

---

## Output Template

```python
import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Any, Tuple
from cohezion.physics.lagrangian import LagrangianDynamics
from cohezion.physics.riemannian_metric import fabric_block_metric

class {ClassName}Env(gym.Env):
    """
    {Description}
    
    State: {StateDescription}
    Actions: {ActionDescription}
    Reward: {RewardDescription}
    """
    
    metadata = {"render_modes": ["rgb_array", "human"]}
    
    def __init__(self, render_mode: str | None = None):
        super().__init__()
        self.render_mode = render_mode
        
        # State/action spaces
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=({StateDim},), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=({ActionDim},), dtype=np.float32
        )
        
        # Physics (if continuous)
        if {UsePhysics}:
            self._metric = fabric_block_metric({StateDim})
            self._dynamics = LagrangianDynamics(self._metric)
        
        # State
        self._state: np.ndarray | None = None
        self._step_count = 0
        
    def reset(self, seed: int | None = None, options: dict | None = None) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self._step_count = 0
        self._state = self.np_random.uniform(-0.5, 0.5, size=({StateDim},))
        return self._get_obs(), {}
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        self._step_count += 1
        
        # Apply physics or simple dynamics
        if hasattr(self, '_dynamics'):
            self._state = self._dynamics.step(self._state, action)
        else:
            self._state += action * 0.01  # Simple dynamics
            self._state = np.clip(self._state, -1.0, 1.0)
        
        # Compute reward
        coherence = self._compute_coherence()
        reward = {RewardFormula}
        
        # Check termination
        terminated = {TerminationCondition}
        truncated = self._step_count >= {MaxSteps}
        
        return self._get_obs(), reward, terminated, truncated, {
            "coherence": coherence,
            "step": self._step_count,
        }
    
    def _get_obs(self) -> np.ndarray:
        return self._state.astype(np.float32)
    
    def _compute_coherence(self) -> float:
        """HIHO coherence metric."""
        return 1.0 - abs(self._state.mean() - 0.5) * 2
    
    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            return np.zeros((64, 64, 3), dtype=np.uint8)  # Placeholder
        return None
```

---

## Examples

### Example 1: Simple Navigation
```python
# Generated from: "Create a 2D navigation environment"

class Navigation2DEnv(gym.Env):
    """Navigate to target in 2D space."""
    
    def __init__(self, render_mode=None):
        super().__init__()
        self.observation_space = spaces.Box(-1, 1, (4,), dtype=np.float32)  # x,y,vx,vy
        self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)  # ax, ay
        # ... (full implementation following template)
```

### Example 2: Web Agent
```python
# Generated from: "Build a web browsing environment"

class WebAgentEnv(gym.Env):
    """Interact with web pages via actions."""
    
    def __init__(self, render_mode=None):
        super().__init__()
        self.observation_space = spaces.Box(0, 255, (224, 224, 3), dtype=np.uint8)  # Screenshot
        self.action_space = spaces.Discrete(10)  # click, scroll, type, etc.
```

---

## Validation Script

```bash
# Run before returning generated code to user
python scripts/validate_env.py --env-code {FILE}
```

Expected output:
```
✓ Syntax valid
✓ gymnasium API compliant
✓ HIHO coherence tracking present
✓ No security violations
✓ Renders without error
```

---

## Resources

- [Genesis Engine Physics](/resources/physics.md)
- [HIHO Stability Principle](/resources/hiho.md)
- [Safety Constraints Checklist](/resources/safety.md)

---

## Authoring Notes

**Priority**: Physics-grounded > hand-crafted  
**Consistency**: Always use Gymnasium API, never Gym  
**Safety**: Block eval, exec, os.system, subprocess  
**Testing**: Generated code must instantiate and run 3 steps  

---

**License**: Apache-2.0  
**Last Updated**: 2026-04-08
