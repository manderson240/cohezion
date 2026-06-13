.PHONY: help format lint lint-check type-check test all clean train evaluate benchmark demo validate compound-train training-history kernel-status kernel-cycle kernel-loop kernel-loop-dry kernel-report async-guard routing-guard hermes-restore resume

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

coherence-check:  ## Enforce 12D manifold integrity in data artifacts
	uv run python src/cohezion/scripts/coherence_inspector.py
	@echo "✓ Manifold integrity verified"

type-check:  ## Run type checking with mypy
	uv run mypy src/cohezion --ignore-missing-imports --no-strict-optional --exclude 'mcp-builder'
	@echo "✓ Type check complete"

test:  ## Run test suite
	uv run pytest tests/
	@echo "✓ Tests complete"

resume:  ## Re-verify the Anthropic Universes living resume (docs/anthropic-universes-fit.md)
	uv run python scripts/resume_verify.py --receipt
	@echo "✓ Resume receipt refreshed: docs/resume_receipt.json"

test-fast:  ## Run fast unit tests only (<1s each, no live services)
	PYTHONPATH=src:scripts/ci uv run pytest tests/unit tests/ouroboros tests/mycelium tests/integrations tests/mcp tests/scripts --import-mode=append --tb=short -q -p no:warnings
	@echo "✓ Fast tests complete"

frontier-digest:  ## Generate today's frontier digest
	uv run python scripts/ci/frontier_digest.py

test-integration:  ## Run integration tests (require live services)
	uv run pytest tests/ -m integration -v
	@echo "✓ Integration tests complete"

test-smoke:  ## Run quick smoke tests (minimal subset)
	uv run pytest tests/unit --import-mode=append -q --tb=line -p no:warnings 2>/dev/null || echo "⚠ Smoke tests failed"

all: format lint type-check test agent-guard mcp-guard kg-guard data-mesh-guard health-guard async-guard routing-guard a2a-guard bmad-guard  ## Run all checks, tests, and guards

agent-guard: ## Synchronize specialist agent definitions across all platform directories
	uv run python src/cohezion/swarm/scripts/agent_guard.py
	@echo "✓ Agent Guard: Specialists synchronized"

a2a-guard: ## Synchronize A2A protocol agent cards (.well-known/agent.json)
	uv run python src/cohezion/swarm/scripts/a2a_guard.py
	@echo "✓ A2A Guard: Agent cards synchronized"

omega-distiller: ## Distill knowledge from KEY_LEARNINGS.md into executable skills
	uv run python src/cohezion/knowledge_graph/scripts/omega_distiller.py
	@echo "✓ OMEGA Distiller: Skills refined"

data-mesh-guard: ## Monitor Data Mesh registry for SLA and quality violations
	uv run python src/cohezion/data_mesh/scripts/data_mesh_guard.py
	@echo "✓ Data Mesh Guard: SLAs verified"

github-scout: ## Start the GitHub Issue polling daemon (Asynchronous Workforce)
	uv run python src/cohezion/swarm/scripts/github_scout.py

health-guard: ## Run autonomic health checks and trajectory drift detection
	uv run python src/cohezion/healing/scripts/trajectory_guard.py &
	@echo "✓ Health Guard: Background monitoring active"

autoresearch-daemon: ## Start the Autonomous Overnight Literature Review
	uv run python src/cohezion/research/scripts/autoresearch_daemon.py

mcp-guard: ## Run MCP Registry Guard to sync configs and check for latency anti-patterns
	uv run python src/cohezion/mcp/scripts/mcp_guard.py
	@echo "✓ MCP Guard checks passed"

kg-guard: ## Scan for high-coherence completed journeys and precipitate knowledge
	uv run python src/cohezion/knowledge_graph/scripts/kg_guard.py
	@echo "✓ Knowledge Graph Guard checks complete"

async-guard: ## Scan for synchronous I/O anti-patterns in async subsystems
	uv run python src/cohezion/scripts/async_guard.py
	@echo "✓ Async Guard: No blocking I/O anti-patterns found"

routing-guard: ## Synchronize model routing and provider configurations across all platforms
	uv run python src/cohezion/swarm/scripts/routing_guard.py
	@echo "✓ Routing Guard: Model configurations synchronized"

skill-guard: ## Validate all skills have proper metadata and FLUME compatibility
	@uv run python src/cohezion/scripts/skill_validator.py
	@echo "✓ Skill Guard: All skills validated"

bmad-guard: ## Enforce BMAD multi-session coordination and artifact integrity
	uv run python src/cohezion/governance/scripts/bmad_guard.py
	@echo "✓ BMAD Guard: Phase locks, symlinks, catalog integrity verified"
telemetry-dashboard: ## Show compound loop telemetry dashboard
	@uv run python src/cohezion/scripts/telemetry_dashboard.py

root-guard: ## Check repository root health (items < 50)
	@python src/cohezion/governance/scripts/root_health_guard.py

archaeology: ## Run root archaeology filing (review before committing)
	@echo "📋 Root Archaeology"
	@echo "Review: src/cohezion/skills/root-archaeology.md"
	@echo "Then: make root-guard"

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

ci: coherence-check async-guard routing-guard a2a-guard agent-guard mcp-guard kg-guard data-mesh-guard health-guard ## Run CI checks locally
	@echo "Running CI checks..."
	ruff format --check .
	ruff check .
	mypy --ignore-missing-imports bmad/ || true
	pytest tests/
	uv run python src/cohezion/swarm/scripts/agent_guard.py
	uv run python src/cohezion/mcp/scripts/mcp_guard.py
	uv run python src/cohezion/knowledge_graph/scripts/kg_guard.py
	uv run python src/cohezion/scripts/async_guard.py
	uv run python src/cohezion/swarm/scripts/routing_guard.py
	uv run python src/cohezion/swarm/scripts/a2a_guard.py
	uv run python src/cohezion/data_mesh/scripts/data_mesh_guard.py
	uv run python src/cohezion/healing/scripts/trajectory_guard.py
	@echo "✓ All CI checks passed"
# Compound Loop Validation
validate:  ## Validate compound engineering loop end-to-end (25 checks, ~18s)
	.venv/bin/python scripts/validate_compound_loop.py
	@echo "✓ Compound loop validated"

# Compound Training Cycle (train → evaluate → persist → compare → refine)
compound-train:  ## Run compound training cycle (SAC dense 100K, auto-persist to SurrealDB)
	.venv/bin/python scripts/compound_training_cycle.py --algo SAC --steps 100000
	@echo "✓ Compound training cycle complete"

training-history:  ## Show training run history from SurrealDB
	@.venv/bin/python scripts/compound_training_cycle.py --history

# Kernel Optimization (Luma AMD Speedrun)
kernel-status:  ## Show Luma kernel optimization status (GEMM/MLA/MoE)
	@.venv/bin/python scripts/compound_kernel_cycle.py --kernel all --history

kernel-cycle:  ## Run compound kernel optimization cycle
	.venv/bin/python scripts/compound_kernel_cycle.py --kernel all --benchmark

kernel-loop:  ## Start continuous kernel benchmark loop (5-min cycles)
	.venv/bin/python scripts/kernel_learning_loop.py --kernel all --interval 300

kernel-loop-dry:  ## Dry-run kernel learning loop (no popcorn, records to SurrealDB)
	.venv/bin/python scripts/kernel_learning_loop.py --kernel all --dry-run --max-iterations 3

kernel-report:  ## Generate kernel status report
	@.venv/bin/python scripts/generate_status_report.py

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

hermes-restore:  ## Restore ~/.hermes/config.yaml from committed baseline (idempotent)
	@if [ ! -f docs/ops/hermes-config-baseline-2026-06-03.yaml ]; then \
		echo "ERROR: docs/ops/hermes-config-baseline-2026-06-03.yaml not found"; exit 1; \
	fi
	@if [ ! -f $(HOME)/.hermes/config.yaml ]; then \
		echo "No existing ~/.hermes/config.yaml; installing fresh baseline"; \
	else \
		cp $(HOME)/.hermes/config.yaml $(HOME)/.hermes/config.yaml.bak-pre-restore-$$(date +%Y%m%d-%H%M%S); \
		echo "Existing config backed up to config.yaml.bak-pre-restore-*"; \
	fi
	cp docs/ops/hermes-config-baseline-2026-06-03.yaml $(HOME)/.hermes/config.yaml
	chmod 600 $(HOME)/.hermes/config.yaml
	@echo "✓ Hermes config restored from baseline (and chmod 600 set)"

hermes-baseline:  ## Snapshot current ~/.hermes/config.yaml as the new committed baseline
	@if [ ! -f $(HOME)/.hermes/config.yaml ]; then \
		echo "ERROR: no ~/.hermes/config.yaml to snapshot"; exit 1; \
	fi
	cp $(HOME)/.hermes/config.yaml docs/ops/hermes-config-baseline-2026-06-03.yaml
	chmod 644 docs/ops/hermes-config-baseline-2026-06-03.yaml
	@echo "✓ New baseline written to docs/ops/hermes-config-baseline-2026-06-03.yaml"

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
