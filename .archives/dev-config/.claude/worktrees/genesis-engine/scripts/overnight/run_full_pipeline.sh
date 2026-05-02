#!/usr/bin/env bash
# Full Cohezion Training Pipeline
# ================================
# Orchestrates the complete training cycle:
#   sim → export → VAE train → watcher → debate → RL train → bridge → retrain → compare → synthesize
#
# Usage:
#   scripts/overnight/run_full_pipeline.sh              # demo scale (~45 min)
#   scripts/overnight/run_full_pipeline.sh medium        # medium scale (~8 hours)
#
# Prerequisites:
#   - Ollama running (phi3:mini, gemma3:4b models pulled)
#   - SurrealDB optional (fallback to JSONL)
#   - Rust extension compiled

set -euo pipefail

SCALE="${1:-demo}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DATA_DIR="${ROOT_DIR}/data"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${DATA_DIR}/pipeline_runs/${TIMESTAMP}"
LOG_FILE="${RUN_DIR}/pipeline.log"

# Scale-specific parameters
case "${SCALE}" in
    demo)
        SIM_ARGS="--scale demo --export-npy"
        VAE_EPOCHS=50
        RL_EPISODES=200
        WATCHER_INTERVAL=5
        ;;
    medium)
        SIM_ARGS="--scale medium --export-npy"
        VAE_EPOCHS=100
        RL_EPISODES=500
        WATCHER_INTERVAL=10
        ;;
    overnight)
        SIM_ARGS="--scale overnight --export-npy"
        VAE_EPOCHS=200
        RL_EPISODES=1000
        WATCHER_INTERVAL=10
        ;;
    *)
        echo "Unknown scale: ${SCALE}. Use: demo, medium, overnight"
        exit 1
        ;;
esac

# Setup
mkdir -p "${RUN_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "============================================================"
echo "COHEZION FULL TRAINING PIPELINE"
echo "  Scale:     ${SCALE}"
echo "  Run dir:   ${RUN_DIR}"
echo "  Started:   $(date)"
echo "  PID:       $$"
echo "============================================================"

cd "${ROOT_DIR}"

# Pre-flight checks
echo ""
echo "[PRE-FLIGHT] Checking prerequisites..."

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found"
    exit 1
fi

if ! uv run python -c "import cohezion" 2>/dev/null; then
    echo "ERROR: cohezion package not importable"
    exit 1
fi

OLLAMA_OK=true
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "WARNING: Ollama not reachable. Debate and watcher steps will be skipped."
    OLLAMA_OK=false
fi

echo "[PRE-FLIGHT] OK"

# Step 1: Mass Simulation with NPY export
echo ""
echo "============================================================"
echo "[STEP 1/9] Mass Simulation (${SCALE})"
echo "============================================================"
STEP1_START=$(date +%s)

uv run python mass_sim_driver.py ${SIM_ARGS} --output-dir "${DATA_DIR}/mass_sim/artifacts"

STEP1_END=$(date +%s)
echo "[STEP 1] Complete in $((STEP1_END - STEP1_START))s"

# Verify .npy files exist
NPY_COUNT=$(find "${DATA_DIR}/mass_sim/artifacts" -name "*.npy" | wc -l)
echo "[STEP 1] Exported ${NPY_COUNT} .npy files"
if [ "${NPY_COUNT}" -eq 0 ]; then
    echo "ERROR: No .npy files produced. Aborting."
    exit 1
fi

# Step 2: Train FLUME VAE
echo ""
echo "============================================================"
echo "[STEP 2/9] FLUME VAE Training (${VAE_EPOCHS} epochs)"
echo "============================================================"
STEP2_START=$(date +%s)

CKPT_DIR="${DATA_DIR}/flume/checkpoints"
uv run python scripts/train_vae.py \
    --data-dir "${DATA_DIR}/mass_sim/artifacts" \
    --epochs "${VAE_EPOCHS}" \
    --checkpoint-dir "${CKPT_DIR}" \
    --log-interval 10

STEP2_END=$(date +%s)
echo "[STEP 2] Complete in $((STEP2_END - STEP2_START))s"

# Step 3: VAE Training Watcher (post-hoc analysis)
echo ""
echo "============================================================"
echo "[STEP 3/9] VAE Training Analysis (phi3:mini)"
echo "============================================================"

if [ "${OLLAMA_OK}" = true ]; then
    STEP3_START=$(date +%s)
    uv run python scripts/vae_training_watcher.py \
        --metrics-file "${CKPT_DIR}/training_metrics.jsonl" \
        --output-file "${DATA_DIR}/flume/training_analysis.jsonl" \
        --analysis-interval "${WATCHER_INTERVAL}" \
        --poll-interval 2 || true
    STEP3_END=$(date +%s)
    echo "[STEP 3] Complete in $((STEP3_END - STEP3_START))s"
else
    echo "[STEP 3] Skipped (Ollama not available)"
fi

# Step 4: Hyperparameter Debate
echo ""
echo "============================================================"
echo "[STEP 4/9] Hyperparameter Debate (gemma3:4b x7 personas)"
echo "============================================================"

if [ "${OLLAMA_OK}" = true ]; then
    STEP4_START=$(date +%s)
    uv run python -c "
import asyncio
from cohezion.pipeline.hyperparameter_debate import HyperparameterDebate
params = asyncio.run(HyperparameterDebate().search_rl_params(
    output_path='${DATA_DIR}/rl/hyperparameter_debate.json'
))
print(f'Debate suggested params: {params}')
" || echo "[STEP 4] Debate failed (non-critical, using defaults)"
    STEP4_END=$(date +%s)
    echo "[STEP 4] Complete in $((STEP4_END - STEP4_START))s"
else
    echo "[STEP 4] Skipped (Ollama not available)"
fi

# Step 5: Train RL Policy
echo ""
echo "============================================================"
echo "[STEP 5/9] RL Policy Training (${RL_EPISODES} episodes)"
echo "============================================================"
STEP5_START=$(date +%s)

RL_DIR="${DATA_DIR}/rl/checkpoints"
uv run python scripts/train_rl.py \
    --episodes "${RL_EPISODES}" \
    --output-dir "${RL_DIR}" \
    --log-interval 10 \
    --save-interval 25

STEP5_END=$(date +%s)
echo "[STEP 5] Complete in $((STEP5_END - STEP5_START))s"

# Step 6: Weight Bridge (Policy → FlumePhysics)
echo ""
echo "============================================================"
echo "[STEP 6/9] Weight Bridge: Policy → FlumePhysics"
echo "============================================================"
STEP6_START=$(date +%s)

uv run python -c "
from cohezion.pipeline.weight_bridge import WeightBridge
import json

weights = WeightBridge.policy_to_flume_weights('${RL_DIR}/policy_final.pt')
print('Weight shapes:')
for k, v in weights.items():
    print(f'  {k}: {v.shape} (norm={float(v.sum()**2)**0.5:.4f})')

# Try to validate with Rust engine
try:
    physics = WeightBridge.policy_to_flume_physics('${RL_DIR}/policy_final.pt')
    result = WeightBridge.validate_coherence(physics)
    print(f'Validation: coherence={result[\"mean_coherence\"]:.4f}, valid={result[\"valid\"]}')
except RuntimeError as e:
    print(f'Rust engine unavailable: {e}')
    print('Weight extraction succeeded — Rust validation skipped.')
"

STEP6_END=$(date +%s)
echo "[STEP 6] Complete in $((STEP6_END - STEP6_START))s"

# Step 7: Re-run Simulation with Trained Navigator
echo ""
echo "============================================================"
echo "[STEP 7/9] Simulation with Trained Navigator"
echo "============================================================"
STEP7_START=$(date +%s)

TRAINED_DIR="${DATA_DIR}/mass_sim/trained_artifacts"
mkdir -p "${TRAINED_DIR}"

uv run python -c "
import asyncio
import numpy as np
from cohezion.mass_sim.config import SCALE_TIERS, SimulationConfig
from cohezion.mass_sim.orchestrator import MassSimOrchestrator
from cohezion.pipeline.trained_navigator import TrainedNavigator

# Create navigator from trained policy
nav = TrainedNavigator('${RL_DIR}/policy_final.pt')

# Run demo-scale sim with trained navigator
config = SimulationConfig(
    scale=SCALE_TIERS['demo'],
    export_npy=True,
    persist_to_db=False,
)
from cohezion.mass_sim.batch_runner import BatchSimulationRunner
runner = BatchSimulationRunner(config, trained_navigator=nav)

# Inject trained runner into orchestrator
orchestrator = MassSimOrchestrator(config)
orchestrator.runner = runner
report = asyncio.run(orchestrator.run())

# Save comparison data
import json
summary = report.summary_dict()
with open('${TRAINED_DIR}/trained_summary.json', 'w') as f:
    json.dump(summary, f, indent=2, default=str)
print(f'Trained sim complete: {summary.get(\"insights\", {}).get(\"safety\", {})}')
"

STEP7_END=$(date +%s)
echo "[STEP 7] Complete in $((STEP7_END - STEP7_START))s"

# Step 8: Compare Random vs Trained
echo ""
echo "============================================================"
echo "[STEP 8/9] Compare Random vs Trained Coherence"
echo "============================================================"

uv run python -c "
import json
from pathlib import Path

# Load latest random simulation summary
random_dir = Path('${DATA_DIR}/mass_sim/artifacts')
random_files = sorted(random_dir.glob('*_final.json'))
random_summary = {}
if random_files:
    with open(random_files[-1]) as f:
        random_summary = json.load(f)

# Load trained simulation summary
trained_path = Path('${DATA_DIR}/mass_sim/trained_artifacts/trained_summary.json')
trained_summary = {}
if trained_path.exists():
    with open(trained_path) as f:
        trained_summary = json.load(f)

print('=== COHERENCE COMPARISON ===')
r_safety = random_summary.get('insights', {}).get('safety', {})
t_safety = trained_summary.get('insights', {}).get('safety', {})

r_coh = r_safety.get('mean_final_coherence', 'N/A')
t_coh = t_safety.get('mean_final_coherence', 'N/A')
r_bounds = r_safety.get('mean_final_within_bounds', 'N/A')
t_bounds = t_safety.get('mean_final_within_bounds', 'N/A')

print(f'  Random navigator:  coherence={r_coh}, within_bounds={r_bounds}')
print(f'  Trained navigator: coherence={t_coh}, within_bounds={t_bounds}')

if isinstance(r_coh, (int, float)) and isinstance(t_coh, (int, float)):
    if t_coh > r_coh:
        print(f'  Result: TRAINED WINS (+{t_coh - r_coh:.4f} coherence)')
    else:
        print(f'  Result: Random still better (delta={r_coh - t_coh:.4f})')

# Save comparison
comparison = {
    'random': {'coherence': r_coh, 'within_bounds': r_bounds},
    'trained': {'coherence': t_coh, 'within_bounds': t_bounds},
}
with open('${RUN_DIR}/comparison.json', 'w') as f:
    json.dump(comparison, f, indent=2, default=str)
"

# Step 9: Deep Analysis (deepseek-r1:70b)
echo ""
echo "============================================================"
echo "[STEP 9/9] Deep Analysis (deepseek-r1:70b)"
echo "============================================================"

if [ "${OLLAMA_OK}" = true ]; then
    STEP9_START=$(date +%s)
    uv run python -c "
import httpx
import json
from pathlib import Path

# Gather summary data
comparison = {}
comp_path = Path('${RUN_DIR}/comparison.json')
if comp_path.exists():
    with open(comp_path) as f:
        comparison = json.load(f)

prompt = f'''COHEZION Training Pipeline Analysis:

A complete training pipeline was run:
1. Mass simulation generated training data
2. FLUME VAE was trained to encode/decode latent vectors
3. REINFORCE RL policy was trained on FlumeNav-v0 (256D, Hamiltonian dynamics)
4. Trained policy weights were transferred to the simulation engine
5. Simulation was re-run with trained weights

Results comparison:
- Random navigator: {comparison.get('random', 'N/A')}
- Trained navigator: {comparison.get('trained', 'N/A')}

Analyze:
1. Did the training pipeline produce meaningful improvement?
2. What drove improvement (or lack thereof)?
3. What should the next iteration focus on?
4. Are there signs the pipeline can scale to medium/overnight runs?
'''

try:
    client = httpx.Client(timeout=300.0)
    resp = client.post(
        'http://localhost:11434/api/generate',
        json={
            'model': 'deepseek-r1:70b',
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.3, 'num_predict': 512},
        },
    )
    resp.raise_for_status()
    analysis = resp.json().get('response', '')

    # Save
    with open('${RUN_DIR}/deep_analysis.md', 'w') as f:
        f.write('# Deep Analysis (deepseek-r1:70b)\n\n')
        f.write(analysis)
    print(f'Deep analysis written ({len(analysis)} chars)')
    print(analysis[:500])
except Exception as e:
    print(f'Deep analysis skipped: {e}')
" || echo "[STEP 9] Deep analysis failed (non-critical)"
    STEP9_END=$(date +%s)
    echo "[STEP 9] Complete in $((STEP9_END - STEP9_START))s"
else
    echo "[STEP 9] Skipped (Ollama not available)"
fi

# Summary
echo ""
echo "============================================================"
echo "PIPELINE COMPLETE"
echo "  Scale:   ${SCALE}"
echo "  Run dir: ${RUN_DIR}"
echo "  Ended:   $(date)"
echo "============================================================"
echo ""
echo "Artifacts:"
echo "  Simulation data:    ${DATA_DIR}/mass_sim/artifacts/"
echo "  VAE checkpoints:    ${CKPT_DIR}/"
echo "  RL checkpoints:     ${RL_DIR}/"
echo "  Training analysis:  ${DATA_DIR}/flume/training_analysis.jsonl"
echo "  Comparison:         ${RUN_DIR}/comparison.json"
echo "  Deep analysis:      ${RUN_DIR}/deep_analysis.md"
echo "  Pipeline log:       ${LOG_FILE}"
