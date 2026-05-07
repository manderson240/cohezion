"""Experiential Learning Agent for ARC-AGI-3.

This agent learns from interaction:
1. Explore: Try actions systematically and observe outcomes
2. Model: Build a transition model from (state, action) -> next_state
3. Plan: Use BFS on the learned model to find goal paths
4. Learn: On GAME_OVER or WIN, update the model and try again smarter

All experience feeds back into Cohezion's vault for cross-project learning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """A single transition experience."""

    state_signature: str
    action: str
    next_state_signature: str
    reward: float  # 0=neutral, 1=win, -1=game_over, 0.1=progress
    levels_completed: int
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state_signature,
            "action": self.action,
            "next_state": self.next_state_signature,
            "reward": self.reward,
            "levels": self.levels_completed,
            "ts": self.timestamp,
        }


class WorldModel:
    """Learned transition model for a single game."""

    def __init__(self, game_id: str):
        self.game_id = game_id
        self.transitions: dict[str, dict[str, tuple[str, float]]] = {}
        self.state_visits: dict[str, int] = {}
        self.experiences: list[Experience] = []

    def learn(self, exp: Experience) -> None:
        """Learn from a single experience."""
        self.experiences.append(exp)

        if exp.state_signature not in self.transitions:
            self.transitions[exp.state_signature] = {}
        self.transitions[exp.state_signature][exp.action] = (exp.next_state_signature, exp.reward)
        self.state_visits[exp.state_signature] = self.state_visits.get(exp.state_signature, 0) + 1

    def predict(self, state_sig: str, action: str) -> tuple[str, float] | None:
        """Predict next state and reward."""
        return self.transitions.get(state_sig, {}).get(action)

    def get_unexplored_actions(self, state_sig: str, available_actions: list[str]) -> list[str]:
        """Get actions we haven't tried in this state."""
        known = set(self.transitions.get(state_sig, {}).keys())
        return [a for a in available_actions if a not in known]

    def get_known_states(self) -> set[str]:
        return set(self.transitions.keys())

    def save(self, path: Path) -> None:
        data = {
            "game_id": self.game_id,
            "transitions": self.transitions,
            "experiences": [e.to_dict() for e in self.experiences[-500:]],
            "total_experiences": len(self.experiences),
        }
        path.write_text(json.dumps(data))

    @classmethod
    def load(cls, path: Path) -> WorldModel:
        data = json.loads(path.read_text())
        wm = cls(data["game_id"])
        for e in data.get("experiences", []):
            wm.learn(
                Experience(
                    state_signature=e["state"],
                    action=e["action"],
                    next_state_signature=e["next_state"],
                    reward=e["reward"],
                    levels_completed=e.get("levels", 0),
                )
            )
        return wm


def grid_signature(grid: list[list[int]], downsample: int = 4) -> str:
    """Create a compact signature of a grid state."""
    arr = np.array(grid)
    h, w = arr.shape
    # Downsample for state abstraction
    dh, dw = max(1, h // downsample), max(1, w // downsample)
    small = arr[::dh, ::dw]
    # Hash the downsampled grid
    flat = small.tobytes()
    return f"{downsample}x{hashlib.md5(flat).hexdigest()[:8]}"


def agent_position(grid: list[list[int]]) -> tuple[int, int] | None:
    """Heuristic: find the 'player' as the most distinct small connected region."""
    arr = np.array(grid)
    unique, counts = np.unique(arr, return_counts=True)

    # Find small-ish unique regions (player is typically a distinct color, moderately sized)
    candidates = []
    for u, c in zip(unique, counts):
        if u == 0:
            continue  # Background
        if 4 <= c <= 64:  # Player-sized region
            # Find centroid
            ys, xs = np.where(arr == u)
            if len(xs) > 0:
                candidates.append((u, int(xs.mean()), int(ys.mean()), c))

    if candidates:
        # Pick the one closest to center ( player usually starts near center)
        center = (arr.shape[1] // 2, arr.shape[0] // 2)
        candidates.sort(key=lambda c: abs(c[1] - center[0]) + abs(c[2] - center[1]))
        return (candidates[0][1], candidates[0][2])
    return None


def compute_reward(
    prev_frame: Any, next_frame: Any, prev_state: str, next_state: str, action_name: str
) -> float:
    """Compute reward signal from frame transition."""
    from arcengine import GameState

    if hasattr(next_frame, "state"):
        if next_frame.state == GameState.WIN:
            return 1.0
        if next_frame.state == GameState.GAME_OVER:
            return -1.0

    # Progress heuristics
    if hasattr(next_frame, "levels_completed") and hasattr(prev_frame, "levels_completed"):
        if next_frame.levels_completed > prev_frame.levels_completed:
            return 0.5

    # Grid change = exploration reward
    if hasattr(prev_frame, "frame") and hasattr(next_frame, "frame"):
        prev_grid = np.array(prev_frame.frame[0]) if prev_frame.frame else np.array([])
        next_grid = np.array(next_frame.frame[0]) if next_frame.frame else np.array([])
        if prev_grid.size > 0 and next_grid.size > 0 and prev_grid.shape == next_grid.shape:
            diff = np.sum(prev_grid != next_grid)
            if diff > 0:
                return 0.05  # Small positive for any state change

    return 0.0


class ExperientialAgent:
    """Agent that learns from interaction and plans with learned model."""

    def __init__(self, game_id: str, exploration_budget: int = 200, plan_depth: int = 20):
        self.game_id = game_id
        self.exploration_budget = exploration_budget
        self.plan_depth = plan_depth
        self.world_model = WorldModel(game_id)
        self.episode = 0
        self.experience_log: list[Experience] = []

    def run_episode(self) -> dict[str, Any]:
        """Run one learning episode and return results."""
        import arc_agi
        from arcengine import GameAction, GameState

        arc = arc_agi.Arcade()
        env = arc.make(self.game_id)
        obs = env.reset()

        states_visited: set[str] = set()
        actions_taken = 0
        wins = 0
        total_reward = 0.0

        # Phase 1: Systematic exploration (first episode or unknown states)
        while actions_taken < self.exploration_budget and obs.state.name not in [
            "WIN",
            "GAME_OVER",
        ]:
            state_sig = grid_signature(obs.frame[0])
            states_visited.add(state_sig)

            available = [a.name for a in env.action_space]
            unexplored = self.world_model.get_unexplored_actions(state_sig, available)

            if unexplored and actions_taken < self.exploration_budget // 2:
                # Prefer unexplored actions in early exploration
                action_name = random.choice(unexplored)
            else:
                # Phase 2: Try to plan toward goal using learned model
                plan = self._plan(
                    state_sig,
                    available,
                    max_depth=min(self.plan_depth, self.exploration_budget - actions_taken),
                )
                if plan:
                    action_name = plan[0]
                else:
                    # Random fallback among available
                    action_name = random.choice(available)

            action = GameAction.from_name(action_name)
            prev_obs = obs
            obs = env.step(action)
            actions_taken += 1

            next_sig = grid_signature(obs.frame[0])
            reward = compute_reward(prev_obs, obs, state_sig, next_sig, action_name)

            exp = Experience(
                state_signature=state_sig,
                action=action_name,
                next_state_signature=next_sig,
                reward=reward,
                levels_completed=obs.levels_completed if hasattr(obs, "levels_completed") else 0,
            )
            self.world_model.learn(exp)
            self.experience_log.append(exp)
            total_reward += reward

            if obs.state == GameState.WIN:
                wins += 1
                logger.info(f"Episode {self.episode}: WIN at action {actions_taken}!")
                break
            elif obs.state == GameState.GAME_OVER:
                # Learn from failure and reset
                obs = env.step(GameAction.RESET)
                logger.debug(f"Episode {self.episode}: GAME_OVER, resetting")

        scorecard = arc.get_scorecard()
        self.episode += 1

        return {
            "game_id": self.game_id,
            "episode": self.episode,
            "actions": actions_taken,
            "wins": wins,
            "total_reward": total_reward,
            "unique_states": len(states_visited),
            "known_states": len(self.world_model.get_known_states()),
            "total_experiences": len(self.world_model.experiences),
            "score": scorecard.score if scorecard else 0.0,
            "scorecard_total_actions": scorecard.total_actions if scorecard else 0,
        }

    def _plan(
        self, start_sig: str, available_actions: list[str], max_depth: int
    ) -> list[str] | None:
        """BFS plan using learned world model."""
        from collections import deque

        if start_sig not in self.world_model.get_known_states():
            return None

        # BFS for shortest path to a known high-reward state
        frontier: deque[tuple[str, list[str], int]] = deque([(start_sig, [], 0)])
        visited: set[str] = {start_sig}
        best_plan: list[str] | None = None
        best_reward = -float("inf")

        while frontier:
            state, path, depth = frontier.popleft()
            if depth >= max_depth:
                continue

            for action in available_actions:
                pred = self.world_model.predict(state, action)
                if pred is None:
                    continue
                next_state, reward = pred
                new_path = [*path, action]

                if reward > best_reward:
                    best_reward = reward
                    best_plan = new_path

                if next_state not in visited and reward >= 0:
                    visited.add(next_state)
                    frontier.append((next_state, new_path, depth + 1))

        return best_plan

    def save_experience(self, base_path: Path = Path("data/arc_agi_3/experiences")) -> Path:
        """Save all experience to disk for Cohezion vault ingestion."""
        base_path.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = base_path / f"{self.game_id}_{ts}.jsonl"

        with open(path, "w") as f:
            for exp in self.experience_log:
                f.write(json.dumps(exp.to_dict()) + "\n")

        # Also save the world model
        model_path = base_path / f"{self.game_id}_model.json"
        self.world_model.save(model_path)

        logger.info(f"Saved {len(self.experience_log)} experiences to {path}")
        return path

    def cross_project_learnings(self) -> dict[str, Any]:
        """Extract cross-project learnings for Cohezion core improvement.

        This is the critical feedback loop: what did we learn about
        interactive reasoning that improves CompoundLoop, Ouroboros, etc?
        """
        # Analyze experience for patterns
        action_rewards: dict[str, list[float]] = {}
        state_outcomes: dict[str, list[float]] = {}

        for exp in self.experience_log:
            action_rewards.setdefault(exp.action, []).append(exp.reward)
            state_outcomes.setdefault(exp.state_signature, []).append(exp.reward)

        # Find best actions
        best_actions = sorted(
            [(a, sum(rs) / len(rs)) for a, rs in action_rewards.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        # Find dangerous states
        dangerous_states = [
            (s, sum(rs) / len(rs)) for s, rs in state_outcomes.items() if sum(rs) / len(rs) < -0.5
        ]

        # Extract principles for Cohezion vault
        principles = []
        if best_actions:
            principles.append(f"Action {best_actions[0][0]} has highest avg reward")
        if len(dangerous_states) > 0:
            principles.append(f"Identified {len(dangerous_states)} dangerous states")
        principles.append(
            f"Built world model with {len(self.world_model.get_known_states())} states"
        )

        return {
            "game_id": self.game_id,
            "episodes": self.episode,
            "total_experiences": len(self.experience_log),
            "unique_states_learned": len(self.world_model.get_known_states()),
            "best_actions": best_actions[:3],
            "dangerous_states_count": len(dangerous_states),
            "principles": principles,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def run_experiential_learning_spike(games: list[str], episodes_per_game: int = 3) -> dict[str, Any]:
    """Run a full experiential learning spike across multiple games."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    results: dict[str, list[dict[str, Any]]] = {}
    all_learnings: list[dict[str, Any]] = []

    for game_id in games:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Experiential Learning: {game_id}")
        logger.info(f"{'=' * 50}")

        agent = ExperientialAgent(game_id, exploration_budget=300, plan_depth=20)
        game_results = []

        for ep in range(episodes_per_game):
            res = agent.run_episode()
            game_results.append(res)
            logger.info(
                f"Episode {ep + 1}: actions={res['actions']}, "
                f"wins={res['wins']}, reward={res['total_reward']:.2f}, "
                f"states={res['unique_states']}, known={res['known_states']}"
            )

        # Save experience
        agent.save_experience()

        # Extract learnings for Cohezion
        learnings = agent.cross_project_learnings()
        all_learnings.append(learnings)
        results[game_id] = game_results

    # Save cross-project learnings to vault
    vault_path = Path("data/arc_agi_3/cross_project_learnings.json")
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(json.dumps(all_learnings, indent=2))

    logger.info(f"\n{'=' * 50}")
    logger.info("Cross-project learnings saved to Cohezion vault")
    logger.info(f"{'=' * 50}")

    return {"results": results, "learnings": all_learnings}


if __name__ == "__main__":
    # Run on easiest known games
    games = ["r11l", "ls20"]  # r11l = 10/10 solvable, ls20 = known platformer
    summary = run_experiential_learning_spike(games, episodes_per_game=3)

    print("\n" + "=" * 50)
    print("EXPERIENTIAL LEARNING SPIKE COMPLETE")
    print("=" * 50)
    for learning in summary["learnings"]:
        print(f"\nGame: {learning['game_id']}")
        print(f"  States learned: {learning['unique_states_learned']}")
        print(f"  Total experiences: {learning['total_experiences']}")
        print(f"  Principles: {learning['principles']}")
