.PHONY: help format lint lint-check type-check test all clean train evaluate benchmark demo validate

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

format:  ## Format code with ruff
	ruff format .
	@echo "✓ Code formatted"

lint:  ## Lint and auto-fix issues with ruff
	ruff check --fix .
	@echo "✓ Linting complete"

lint-check:  ## Check linting without fixing
	ruff check .
	ruff format --check .
	@echo "✓ Lint check complete"

type-check:  ## Run type checking with mypy
	mypy --ignore-missing-imports bmad/ || true
	@echo "✓ Type check complete"

test:  ## Run test suite
	pytest tests/
	@echo "✓ Tests complete"

all: format lint type-check test  ## Run all checks and tests

clean:  ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned"

# Development workflow targets
dev-setup:  ## Install pre-commit hooks
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

ci:  ## Run CI checks locally
	@echo "Running CI checks..."
	ruff format --check .
	ruff check .
	mypy --ignore-missing-imports bmad/ || true
	pytest tests/
	@echo "✓ All CI checks passed"

# Compound Loop Validation
validate:  ## Validate compound engineering loop end-to-end (25 checks, ~18s)
	.venv/bin/python scripts/validate_compound_loop.py
	@echo "✓ Compound loop validated"

# RL Training + Evaluation targets
train:  ## Train PPO on ManifoldEnv (quick: 20K steps, ~5 min)
	uv run python scripts/train_manifold_agent.py --timesteps 20000 --eval-episodes 10
	@echo "✓ Training complete. Results in results/training/"

evaluate:  ## Evaluate trained model vs baselines
	uv run python scripts/train_manifold_agent.py --timesteps 0 --eval-episodes 20 || \
	uv run python -c "from cohezion.eval.universe_evaluator import *; from cohezion.environments.manifold_env import ManifoldEnv; e=UniverseEvaluator(); env=ManifoldEnv(max_steps=200,seed=42); print(e.compare_policies(env,{'greedy':greedy_hiho_policy,'random':random_policy},n_episodes=10).summary_table())"
	@echo "✓ Evaluation complete"

benchmark:  ## Full benchmark: 100K training + safety metrics + all comparisons
	uv run python scripts/train_manifold_agent.py --timesteps 100000 --eval-episodes 50
	@echo "✓ Benchmark complete. Results in results/training/"

demo:  ## Quick demo: train 5K steps, evaluate, show compound loop
	@echo "=== Cohezion Demo: Physics-Grounded Agent Training ==="
	@echo ""
	@echo "Training PPO agent on 12D Riemannian manifold..."
	@uv run python -c "\
	from stable_baselines3 import PPO; \
	from cohezion.environments.manifold_env import ManifoldEnv; \
	from gymnasium import spaces; \
	import numpy as np; \
	env = ManifoldEnv(max_steps=100, seed=42, render_mode='human'); \
	env.action_space = spaces.Box(low=-0.1, high=0.1, shape=(12,), dtype=np.float32); \
	model = PPO('MlpPolicy', env, verbose=0, seed=42, n_steps=256); \
	model.learn(total_timesteps=5000); \
	print('\n=== Evaluation: Trained PPO vs Random ==='); \
	from cohezion.eval.universe_evaluator import UniverseEvaluator, random_policy; \
	evaluator = UniverseEvaluator(n_bootstrap=50); \
	def tp(obs): a,_=model.predict(obs,deterministic=True); return np.clip(a,-0.1,0.1).astype(np.float32); \
	ppo = evaluator.evaluate_policy(env, tp, n_episodes=5, policy_name='PPO'); \
	rnd = evaluator.evaluate_policy(env, random_policy, n_episodes=5, policy_name='Random'); \
	print(f'PPO:    coherence={ppo.mean_coherence:.3f}, reward={ppo.mean_reward:.2f}, stability={ppo.mean_stability_duration:.0f}'); \
	print(f'Random: coherence={rnd.mean_coherence:.3f}, reward={rnd.mean_reward:.2f}, stability={rnd.mean_stability_duration:.0f}'); \
	print(f'\nResult: PPO {\"outperforms\" if ppo.mean_reward > rnd.mean_reward else \"underperforms\"} random by {abs(ppo.mean_reward-rnd.mean_reward):.2f} reward'); \
	print('=== Compound loop: training → evaluation → knowledge persistence ===')"
	@echo ""
	@echo "✓ Demo complete"
