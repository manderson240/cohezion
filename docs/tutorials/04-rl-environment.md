# RL Environment Tutorial: ManifoldEnv and SwarmEnv

Train reinforcement learning agents in a physics-grounded 12D Riemannian manifold.

## ManifoldEnv — Single Agent

### Basic Usage

```python
import gymnasium as gym

# Using gymnasium registration
env = gym.make("Cohezion/ManifoldEnv-v0")
obs, info = env.reset()

print(f"Observation: {obs.shape}")  # (19,) = 12D state + 3D Bloch + 4D fiber
print(f"Action space: {env.action_space}")  # Box(-0.5, 0.5, (12,))
print(f"Coherence: {info['coherence']:.4f}")
print(f"HIHO deviation: {info['hiho_deviation']:.4f}")
```

### Observation Space (19D)

| Dims | Name | Range | Source |
|------|------|-------|--------|
| 0-11 | 12D axiomatic state | [-1.5, 2.0] | Lagrangian dynamics |
| 12-14 | Bloch vector (r_x, r_y, r_z) | [-1, 1] | SU(2) spinor |
| 15-18 | Fiber base (4 fabric norms) | [0, inf) | Fiber bundle projection |

### Action Space (12D continuous)

Each action dimension is a velocity perturbation in [-0.5, 0.5].

### Reward Function

```
reward = coherence_gain * 1.0    # Approaching HIHO
       - |energy| * 0.1          # Energy efficiency
       + 0.1 if at HIHO          # Stability bonus
```

### Info Dict

Every step returns rich physics data:
- `coherence`, `hiho_deviation`, `hiho_streak`
- `charge_polarity`, `spin_rotation`, `spin_precession`
- `yang_mills_action`, `is_hiho`
- `potential_energy`, `kinetic_energy`
- `episode_reward`, `trajectory_length`

### Training with Stable-Baselines3

```python
from stable_baselines3 import PPO
from cohezion.environments import ManifoldEnv

env = ManifoldEnv(max_steps=500, damping=0.1)
model = PPO("MlpPolicy", env, verbose=1, n_steps=256)
model.learn(total_timesteps=50_000)

# Evaluate
obs, info = env.reset()
for _ in range(500):
    action, _ = model.predict(obs)
    obs, reward, done, truncated, info = env.step(action)
    if done:
        print(f"HIHO reached! coherence={info['coherence']:.4f}")
        break
```

### Environment Parameters

```python
ManifoldEnv(
    dim=12,                    # Manifold dimension
    max_steps=500,             # Episode length
    dt=0.01,                   # Physics timestep
    damping=0.1,               # Viscous damping
    hiho_threshold=0.01,       # HIHO convergence threshold
    hiho_stability_window=10,  # Steps at HIHO before termination
    reward_coherence_weight=1.0,
    reward_energy_weight=0.1,
    seed=42,                   # Reproducibility
)
```

## SwarmEnv — Multi-Agent

### Basic Usage

```python
from cohezion.environments import SwarmEnv

env = SwarmEnv(n_agents=4, coupling_strength=0.1)
observations, infos = env.reset()

for step in range(500):
    # Each agent acts independently
    actions = {
        agent: env._rng.uniform(-0.1, 0.1, 12).astype("float32")
        for agent in env.agents
    }
    observations, rewards, terminateds, truncateds, infos = env.step(actions)

    if any(terminateds.values()):
        print(f"All agents at HIHO at step {step}!")
        break
```

### Gauge Field Coupling

Agents interact through gauge field coupling — one agent's motion generates curvature that affects other agents' dynamics. The coupling field is the mean deviation from HIHO across all agents:

```
coupling_field = mean(position_i - 0.5) for all agents i
velocity_i += coupling_field * coupling_strength
```

Agents near HIHO contribute less coupling (flat connection). Agents far from HIHO create stronger fields.

### Cooperative Objective

```
reward_i = 0.5 * individual_coherence + 0.5 * collective_coherence
```

The collective term means agents are incentivized to help each other converge.

### Environment Parameters

```python
SwarmEnv(
    n_agents=4,            # Number of agents
    dim=12,                # Manifold dimension
    max_steps=500,         # Episode length
    coupling_strength=0.1, # Gauge coupling between agents
    seed=42,
)
```

## Analyzing Trajectories

### Extract Trajectory

```python
env = ManifoldEnv()
env.reset()
for _ in range(100):
    env.step(env.action_space.sample())

trajectory = env.get_trajectory()  # (101, 12) array
print(f"Trajectory shape: {trajectory.shape}")
```

### Apply TDA

```python
from cohezion.compound.topological_persistence import trajectory_persistence_summary

summary = trajectory_persistence_summary(list(trajectory))
print(f"H0 clusters: {summary['n_clusters']}")
print(f"H1 loops: {summary['n_loops']}")
print(f"Persistence entropy: {summary['persistence_entropy_h0']:.4f}")
```

### Compute Surprise

```python
from cohezion.world_model.jepa_world_model import JEPAWorldModel

model = JEPAWorldModel()
# ... train model ...

for t in range(len(trajectory) - 1):
    state = trajectory[t]
    action = trajectory[t+1] - trajectory[t]
    surprise = model.surprise_score(state, action, trajectory[t+1])
    if surprise > 1.0:
        print(f"Step {t}: HIGH SURPRISE ({surprise:.4f})")
```
