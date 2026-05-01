#!/usr/bin/env python3
"""
AGI Overnight Experience v2.0 - With Active Manager Agent
Prevents stuck states through course correction and external monitoring
"""

import json
import os
import sys
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import numpy as np


sys.path.insert(0, 'src')

EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
TARGET = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
if TARGET <= NOW:
    TARGET += timedelta(days=1)

# ==================== MANAGER AGENT (External Monitor) ====================

class ManagerAgent:
    """
    External agent that monitors the worker and prevents stuck states.
    Can restart, reconfigure, or intervene when progress stalls.
    """

    def __init__(self):
        self.last_progress = None
        self.progress_history = deque(maxlen=100)
        self.stuck_threshold = 0.001  # Minimum change to count as progress
        self.interventions = []
        self.checkpoint_file = 'manager_checkpoint.json'

    def is_stuck(self, current_metrics):
        """Detect if system is stuck (repeating same state)."""
        if len(self.progress_history) < 10:
            return False

        # Check variance in last 10 samples
        recent = list(self.progress_history)[-10:]
        variances = {
            'coherence': np.var([r['coherence'] for r in recent]),
            'cycle_rate': np.var([r['cycles_per_min'] for r in recent]),
            'memory_growth': np.var([r['memory_count'] for r in recent])
        }

        # Stuck if all variances are near zero
        stuck = all(v < self.stuck_threshold for v in variances.values())

        if stuck:
            print("\n[MANAGER ALERT] STUCK STATE DETECTED!")
            print(f"  Coherence variance: {variances['coherence']:.6f}")
            print(f"  Cycle rate variance: {variances['cycle_rate']:.6f}")

        return stuck

    def intervene(self, worker):
        """Take corrective action when stuck."""
        print("[MANAGER] Intervening...")

        # Strategy: Random perturbation to break attractor
        intervention = {
            'timestamp': datetime.now(EST).isoformat(),
            'type': 'perturbation',
            'action': 'Random state perturbation'
        }

        # Add noise to break symmetry
        worker.perturb_state(scale=0.5)

        # Increase learning temporarily
        worker.world_model.lr *= 2.0

        # Reduce step size to explore
        worker.dt *= 0.5

        self.interventions.append(intervention)

        with open(f'intervention_{datetime.now().strftime("%H%M%S")}.json', 'w') as f:
            json.dump(intervention, f)

        print(f"[MANAGER] Intervention complete. New LR: {worker.world_model.lr:.6f}")

    def check_progress(self, worker, elapsed_min):
        """Periodic check by manager agent."""
        metrics = {
            'timestamp': datetime.now(EST).isoformat(),
            'elapsed_min': elapsed_min,
            'coherence': worker.physics.compute_coherence(worker.state_12d),
            'cycles_per_min': worker.iteration / max(elapsed_min, 0.1),
            'memory_count': len(worker.vault.memories),
            'intervention_count': len(self.interventions)
        }

        self.progress_history.append(metrics)

        # Check if stuck
        if self.is_stuck(metrics):
            self.intervene(worker)
            return 'INTERVENED'

        return 'OK'

    def report_status(self):
        """Generate manager report."""
        return {
            'monitor_duration': len(self.progress_history) * 15,  # 15 min intervals
            'interventions': len(self.interventions),
            'stuck_events': len([i for i in self.interventions if i['type'] == 'stuck_reset']),
            'current_variance': {
                'coherence': np.var([r['coherence'] for r in self.progress_history]) if self.progress_history else 0
            }
        }


# ==================== WORKER AGENT (The AGI Experience) ====================

class ExperienceVault:
    """Long-term experiential memory."""
    def __init__(self):
        self.db_path = 'vault/experience.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.memories = []
        self.load_historical()

    def load_historical(self):
        if os.path.exists(f'{self.db_path}.jsonl'):
            with open(f'{self.db_path}.jsonl') as f:
                for line in f:
                    if line.strip():
                        self.memories.append(json.loads(line))

    def store(self, exp):
        self.memories.append({'timestamp': datetime.now(EST).isoformat(), **exp})
        with open(f'{self.db_path}.jsonl', 'a') as f:
            f.write(json.dumps(self.memories[-1]) + '\n')

    def retrieve_similar(self, state):
        if not self.memories:
            return []
        return sorted(self.memories, key=lambda m: abs(m.get('coherence', 0.5) - state.get('coherence', 0.5)))[:5]

class TriunePhysics:
    """12D manifold with Percival Triune."""
    def __init__(self):
        self.fabric_coupling = np.array([1.0, 1.0, 1.0, 0.7, 0.7, 0.7, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3])

    def evolve_12d(self, state, dt):
        decay = 0.9 ** 50
        return state * decay + 0.5 * (1 - decay) * self.fabric_coupling * dt * 100

    def compute_coherence(self, state):
        return float(np.mean(np.abs(state - 0.5)))

class SimpleWorldModel:
    """JEPA-like predictive model."""
    def __init__(self, dim=12):
        self.dim = dim
        self.weights = np.random.randn(dim, dim) * 0.001
        self.lr = 1e-3

    def predict(self, state):
        return np.tanh(self.weights @ state)

    def learn(self, state, target):
        pred = self.predict(state)
        err = target - pred
        self.weights += self.lr * np.outer(err, state)
        return float(np.mean(err**2))

class AGIExperienceWorker:
    """The main AGI learning worker (monitored by Manager)."""

    def __init__(self):
        self.vault = ExperienceVault()
        self.physics = TriunePhysics()
        self.world_model = SimpleWorldModel()
        self.state_12d = np.random.randn(12) * 0.3 + 0.5
        self.iteration = 0
        self.dt = 0.1
        self.metrics = []
        self.last_intervention_time = 0

    def perturb_state(self, scale=0.5):
        """Add noise to break stuck attractors."""
        self.state_12d += np.random.randn(12) * scale
        print(f"[WORKER] State perturbed by {scale:.3f}")

    def experience_cycle(self):
        """One learning cycle."""
        self.iteration += 1

        # Store experience before evolution
        exp = {
            'coherence': self.physics.compute_coherence(self.state_12d),
            'state': self.state_12d.tolist()
        }
        self.vault.store(exp)

        # World model prediction
        pred = self.world_model.predict(self.state_12d)

        # Physics evolution
        next_state = self.physics.evolve_12d(self.state_12d, self.dt)

        # Learn from prediction error
        loss = self.world_model.learn(self.state_12d, next_state)

        # Update state
        self.state_12d = next_state

        return {
            'coherence': exp['coherence'],
            'loss': loss,
            'memories': len(self.vault.memories)
        }

    def run_with_manager(self):
        """Run with external manager monitoring."""
        print('='*70)
        print('AGI OVERNIGHT v2.0: MANAGER-WORKER ARCHITECTURE')
        print('='*70)
        print('Start:', datetime.now(EST).strftime('%Y-%m-%d %H:%M:%S'))
        print('Target:', TARGET.strftime('%Y-%m-%d %H:%M:%S'))
        print()

        # Create manager agent
        manager = ManagerAgent()
        print('[Manager Agent Initialized]')
        print('  Will intervene if stuck detected')
        print('  Checking every ~15 minutes')
        print()

        start = time.time()
        next_manager_check = start + 900
        next_log = start + 60  # Log every minute

        try:
            while datetime.now(EST) < TARGET:
                # Worker: Experience cycle
                metrics = self.experience_cycle()

                # Manager: Periodic check
                if time.time() >= next_manager_check:
                    elapsed = (time.time() - start) / 60
                    status = manager.check_progress(self, elapsed)

                    if status == 'INTERVENED':
                        self.last_intervention_time = elapsed

                    next_manager_check = time.time() + 900

                # Log output
                if time.time() >= next_log:
                    elapsed = (time.time() - start) / 60
                    ts = datetime.now(EST).strftime('%H:%M:%S')
                    print(f"[{ts}] Cycle:{self.iteration:,} | Coh:{metrics['coherence']:.4f} | "
                          f"Loss:{metrics['loss']:.4f} | Mem:{metrics['memories']:,} | "
                          f"Int:{len(manager.interventions)} | {elapsed:.1f}min")

                    self.metrics.append({'time': elapsed, **metrics})
                    next_log = time.time() + 60

                time.sleep(0.001)

        except KeyboardInterrupt:
            print('\nInterrupted by user')

        finally:
            duration = (time.time() - start) / 60

            # Final report
            print()
            print('='*70)
            print('AGI OVERNIGHT COMPLETE')
            print('='*70)
            print(f'Duration: {duration:.1f} minutes')
            print(f'Total cycles: {self.iteration:,}')
            print(f'Memories stored: {len(self.vault.memories):,}')
            print(f'Manager interventions: {len(manager.interventions)}')
            print(f'Final coherence: {metrics["coherence"]:.4f}')

            # Manager report
            mgr_report = manager.report_status()
            print('\nManager Report:')
            print(f'  Variance (coherence): {mgr_report["current_variance"]["coherence"]:.6f}')
            print(f'  Interventions: {mgr_report["interventions"]}')

            with open('agi_v2_results.json', 'w') as f:
                json.dump({
                    'duration': duration,
                    'cycles': self.iteration,
                    'memories': len(self.vault.memories),
                    'interventions': len(manager.interventions),
                    'manager_report': mgr_report,
                    'final_coherence': metrics['coherence']
                }, f)

            return duration, self.iteration

# ==================== RUN ====================

if __name__ == '__main__':
    worker = AGIExperienceWorker()
    duration, cycles = worker.run_with_manager()
    print(f'\nMETRIC duration={duration:.0f} cycles={cycles}')
