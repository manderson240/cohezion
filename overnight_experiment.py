#!/usr/bin/env python3
"""
Overnight Continuous Learning Experiment
Runs until 7 AM EST, continuously training JEPA world model
generating dream rollouts, and logging metrics.

Start: Late evening April 26, 2026
Stop: 7:00 AM EST April 27, 2026 (~7-8 hours)
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np


# Optional system monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

sys.path.insert(0, 'src')

# Target end time: 7 AM EST (UTC-5)
EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
TARGET_END = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
if TARGET_END <= NOW:
    TARGET_END = TARGET_END + timedelta(days=1)  # Tomorrow 7 AM

print('='*70)
print('OVERNIGHT CONTINUOUS LEARNING EXPERIMENT')
print('='*70)
print('Start:', NOW.strftime('%Y-%m-%d %H:%M:%S %Z'))
print('End:  ', TARGET_END.strftime('%Y-%m-%d %H:%M:%S %Z'))
print('Duration:', str(TARGET_END - NOW))
print('='*70)
print()

# Import our systems
from cohezion.inference.tri_compute_orchestrator import TriComputeOrchestrator
from cohezion.physics.riemannian_metric import hiho_metric
from cohezion.world_model.jepa_world_model import generate_synthetic_training_data
from cohezion.world_model.jepa_world_model_persistent import JEPAWorldModelPersistent


# Initialize systems
print('[Initializing Systems]')
model = JEPAWorldModelPersistent(
    db_connection=None,  # Local mode for overnight
    state_dim=12,
    action_dim=12,
    embed_dim=64,  # Reasonable size
    lr=1e-4
)

hiho = hiho_metric(dim=12, sigma=0.3)

orch = TriComputeOrchestrator()

# Metrics tracking
metrics_log = []
interval_seconds = 900  # 15 minutes between logs
start_time = time.time()
ext_log_time = start_time + interval_seconds

iteration = 0
epoch = 0

print(f'[Starting Training Loop - {interval_seconds}s intervals]')
print()

try:
    while True:
        # Check if we should stop (7 AM EST)
        current_time_est = datetime.now(EST)
        if current_time_est >= TARGET_END:
            print()
            print('='*70)
            print('TARGET TIME REACHED: 7 AM EST')
            print('='*70)
            break

        # Training iteration
        iteration += 1

        # Generate training data
        data = generate_synthetic_training_data(
            n_samples=50,
            state_dim=12
        )

        # Train with persistence
        train_metrics = model.train_epoch_with_persistence(
            data,
            batch_size=16
        )
        epoch += 1

        # Generate dream rollout every 10 epochs
        if epoch % 10 == 0:
            dream = model.dream_rollout(n_steps=20, temperature=0.7)

            # Compute dream quality metrics
            imagined_steps = len([d for d in dream if d.get('imagined', False)])
            dream_quality = imagined_steps / len(dream) if dream else 0
        else:
            dream_quality = None

        # Compute HIHO geodesic (geometric validation)
        if epoch % 20 == 0:
            x0 = np.full(12, 0.5) + np.random.randn(12) * 0.1
            v0 = np.random.randn(12) * 0.05
            t, traj = hiho.geodesic(x0, v0, t_span=(0, 1), n_steps=10)
            geodesic_converged = np.linalg.norm(traj[-1] - 0.5) < np.linalg.norm(traj[0] - 0.5)
        else:
            geodesic_converged = None

        # Log interval check
        if time.time() >= next_log_time:
            elapsed = (time.time() - start_time) / 60  # minutes

            # System health
            if HAS_PSUTIL:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
            else:
                cpu_percent = 0
                memory_percent = 0

            # Model metrics
            train_loss = train_metrics.get('total_loss', 0)

            # Create log entry
            log_entry = {
                'timestamp': current_time_est.isoformat(),
                'elapsed_minutes': round(elapsed, 2),
                'epoch': epoch,
                'iteration': iteration,
                'train_loss': round(train_loss, 4),
                'dream_quality': dream_quality,
                'geodesic_converged': geodesic_converged,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'trajectories_stored': len(model.trajectory_buffer) +
                    (len(model.db._trajectories) if hasattr(model.db, '_trajectories') else 0)
            }

            metrics_log.append(log_entry)

            # Print progress
            print(f"[{current_time_est.strftime('%H:%M:%S')}] "
                  f"Epoch {epoch} | Loss: {train_loss:.4f} | "
                  f"Dream: {dream_quality:.2% if dream_quality else 'N/A'} | "
                  f"CPU: {cpu_percent}% | Mem: {memory_percent}% | "
                  f"Elapsed: {elapsed:.1f}min")

            # Write checkpoint
            checkpoint = {
                'experiment': 'overnight_learning',
                'start_time': NOW.isoformat(),
                'current_time': current_time_est.isoformat(),
                'target_end': TARGET_END.isoformat(),
                'epoch': epoch,
                'metrics_log': metrics_log
            }

            with open('overnight_checkpoint.json', 'w') as f:
                json.dump(checkpoint, f, indent=2)

            # Schedule next log
            next_log_time = time.time() + interval_seconds

        # Small delay to prevent CPU spinning
        time.sleep(0.1)

except KeyboardInterrupt:
    print()
    print('Interrupted by user')

except Exception as e:
    print()
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

finally:
    # Final summary
    total_elapsed = (time.time() - start_time) / 60

    print()
    print('='*70)
    print('EXPERIMENT COMPLETE')
    print('='*70)
    print(f'Total Duration: {total_elapsed:.1f} minutes')
    print(f'Total Epochs: {epoch}')
    print(f'Total Iterations: {iteration}')
    print(f'Log Entries: {len(metrics_log)}')

    final_loss = 0
    if metrics_log:
        final_loss = metrics_log[-1].get('train_loss', 0)
        avg_loss = np.mean([m['train_loss'] for m in metrics_log if 'train_loss' in m])
        print(f'Final Loss: {final_loss:.4f}')
        print(f'Avg Loss: {avg_loss:.4f}')

        # Save final results
        results = {
            'experiment': 'overnight_learning',
            'status': 'complete',
            'start_time': NOW.isoformat(),
            'end_time': datetime.now(EST).isoformat(),
            'target_end': TARGET_END.isoformat(),
            'total_epochs': epoch,
            'total_iterations': iteration,
            'total_duration_minutes': total_elapsed,
            'final_metrics': {
                'train_loss': final_loss,
                'avg_train_loss': avg_loss,
                'total_log_entries': len(metrics_log)
            },
            'metrics_log': metrics_log
        }

        with open('overnight_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print()
        print('Results saved to: overnight_results.json')

    print('='*70)

    # Print for autoresearch
    print()
    print(f'METRIC training_duration={total_elapsed:.0f}')
    print(f'ASI final_loss={final_loss:.4f} total_epochs={epoch}')
