from __future__ import annotations
import numpy as np
import random
import torch
import torch.nn.functional as F
from typing import List, Dict, Any, Optional, Tuple
from arc_bioelectric import BioelectricCoupler
from arc_dsl import ARCDSL
from arc_jepa import ARCWorldModel
from arc_ttt_trainer import ARCTTTTrainer
from arc_manifold_transfer import ARCManifoldTransfer
from arc_evolutionary_steer import ARCEvolutionarySteer
from arc_axiomatic import ARCAxiomaticProjector, compute_hiho_stability

class ASTNode:
    """A node in the Abstract Syntax Tree (AST) representing a transformation program."""
    def __init__(self, operation: str, params: Optional[List[Any]] = None):
        self.operation = operation
        self.params = params or []

    def execute(self, grid: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """Executes the operation on a given grid."""
        try:
            res = grid
            if self.operation == "recolor":
                res = ARCDSL.recolor(grid, self.params[0], self.params[1])
            elif self.operation == "move_object":
                if mask is None:
                    coupler = BioelectricCoupler()
                    mask, _ = coupler.find_organs(grid)
                res = ARCDSL.move_object(grid, mask, self.params[0], self.params[1], self.params[2])
            elif self.operation == "symmetry_fill":
                res = ARCDSL.symmetry_fill(grid, axis=self.params[0])
            elif self.operation == "scale_grid":
                res = ARCDSL.scale_grid(grid, factor=self.params[0])
            elif hasattr(ARCDSL, self.operation):
                res = getattr(ARCDSL, self.operation)(grid)
            
            # Critical: copy to ensure positive strides for torch.from_numpy
            return res.copy()
        except Exception:
            return grid

    def to_summary(self) -> str:
        """Returns a string summary of the operation."""
        return f"{self.operation}({','.join(map(str, self.params))})"

class CosmogonySynthesizer:
    """
    Advanced Cosmogony Synthesizer (Cohezion-Prime Edition).
    Refined with Cross-Game Transfer and Axiomatic Guidance.
    """
    def __init__(self, pop_size: int = 50, max_generations: int = 100, device: str = "cpu"):
        self.device = device
        self.coupler = BioelectricCoupler(threshold=0.8)
        self.projector = ARCAxiomaticProjector()
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.available_ops = ARCDSL.get_all_ops()
        
        # Cohezion Components
        self.model = ARCWorldModel().to(device)
        self.ttt = ARCTTTTrainer(self.model)
        self.transfer = ARCManifoldTransfer()
        self.steer = ARCEvolutionarySteer()

    def synthesize_rule(self, task_id: str, train_pairs: List[Dict[str, Any]]) -> List[ASTNode]:
        """Runs the spearhead cosmogonic cooling process."""
        print(f"Initiating Refined Cosmogonic Synthesis for Task: {task_id}")
        
        # 1. Test-Time Training (Specialization)
        self.ttt.specialize_for_task(train_pairs)
        
        # 2. Manifold Transfer: Search for similar historical rules
        # Compute mean axiomatic delta for this task
        with torch.no_grad():
            deltas = []
            for pair in train_pairs:
                z_in = self.model.encoder(torch.from_numpy(np.array(pair['input'])).unsqueeze(0).unsqueeze(0).float())
                z_out = self.model.encoder(torch.from_numpy(np.array(pair['output'])).unsqueeze(0).unsqueeze(0).float())
                ax_in = self.projector(z_in)
                ax_out = self.projector(z_out)
                deltas.append((ax_out - ax_in).squeeze(0).cpu().numpy())
            mean_delta = np.mean(deltas, axis=0)
            
        seeded_program_summary = self.transfer.find_similar_rule(mean_delta)
        if seeded_program_summary:
            print(f"  [Transfer] Found similar rule precipitate: {seeded_program_summary}")
        
        # 3. Evolutionary Search with TDA Steering
        best_program = self._evolutionary_search(train_pairs, seeded_program_summary)

        # 4. Save to Library if high coherence
        # (Simplified implementation)
        summary = " -> ".join([n.to_summary() for n in best_program])
        self.transfer.save_rule(task_id, mean_delta, summary)

        return best_program

    def _evolutionary_search(self, train_pairs: List[Dict[str, Any]], seed_summary: Optional[str]) -> List[ASTNode]:
        population = [self._random_ast(random.randint(1, 3)) for _ in range(self.pop_size)]
        
        # Seed population with historical match if available
        if seed_summary:
            # (In a real implementation, we would parse the summary back to ASTNodes)
            pass

        for gen in range(self.max_generations):
            scored_population = []
            for p in population:
                score, stability = self._evaluate(p, train_pairs)
                scored_population.append((score, stability, p))
                
                # Record candidate for TDA steering
                mock_latent = np.random.randn(256) 
                self.steer.record_candidate(score, mock_latent)
            
            scored_population.sort(key=lambda x: x[0], reverse=True)
            best_score = scored_population[0][0]
            
            if best_score == 1.0:
                print(f"    -> Reached 0.5 Coherence at generation {gen}!")
                return scored_population[0][2]
                
            directive = self.steer.get_steering_directive()
            elites = [p for s, st, p in scored_population[:int(self.pop_size * 0.2)]]
            next_gen = elites[:]
            
            # Dynamic Mutation Rate based on Manifold Stability
            # Lower stability -> Higher mutation (searching for equilibrium)
            mean_stability = np.mean([s[1] for s in scored_population[:10]])
            base_mutation = 0.1 + (1.0 - mean_stability) * 0.4
            
            if directive == "PIVOT":
                base_mutation = 0.8
                print(f"    [TDA] Search stalled. Triggering PIVOT (Mutation Rate: {base_mutation:.2f})")
            
            while len(next_gen) < self.pop_size:
                parent = random.choice(elites)
                child = self._mutate(parent, base_mutation)
                next_gen.append(child)
                
            population = next_gen
            
        return scored_population[0][2]

    def _random_ast(self, depth: int = 1) -> List[ASTNode]:
        program = []
        for _ in range(depth):
            op, num_params = random.choice(self.available_ops)
            params = []
            if op == "recolor":
                params = [random.randint(0, 9), random.randint(0, 9)]
            elif op == "move_object":
                params = [random.randint(1, 3), random.randint(-5, 5), random.randint(-5, 5)]
            elif op == "symmetry_fill":
                params = [random.choice(['h', 'v'])]
            elif op == "scale_grid":
                params = [random.randint(2, 3)]
            program.append(ASTNode(op, params))
        return program

    def _evaluate(self, program: List[ASTNode], train_pairs: List[Dict[str, Any]]) -> Tuple[float, float]:
        errors = 0
        total_stability = 0
        for pair in train_pairs:
            grid = np.array(pair['input'])
            target = np.array(pair['output'])
            
            for node in program:
                grid = node.execute(grid)
            
            if grid.shape != target.shape:
                errors += 1000
                continue
            
            errors += np.sum(grid != target)
            
            # Measure manifold stability of the result
            with torch.no_grad():
                z = self.model.encoder(torch.from_numpy(grid).unsqueeze(0).unsqueeze(0).float())
                ax = self.projector(z)
                total_stability += compute_hiho_stability(ax)
                
        fitness = 1.0 / (1.0 + errors)
        avg_stability = total_stability / len(train_pairs)
        return fitness, avg_stability

    def _mutate(self, program: List[ASTNode], rate: float) -> List[ASTNode]:
        if random.random() > rate:
            return [ASTNode(n.operation, list(n.params)) for n in program]
        
        new_prog = [ASTNode(n.operation, list(n.params)) for n in program]
        if not new_prog:
            return self._random_ast(1)
            
        idx = random.randint(0, len(new_prog) - 1)
        op, num_params = random.choice(self.available_ops)
        params = []
        if op == "recolor":
            params = [random.randint(0, 9), random.randint(0, 9)]
        elif op == "move_object":
            params = [random.randint(1, 3), random.randint(-5, 5), random.randint(-5, 5)]
        elif op == "symmetry_fill":
            params = [random.choice(['h', 'v'])]
        elif op == "scale_grid":
            params = [random.randint(2, 3)]
            
        new_prog[idx] = ASTNode(op, params)
        return new_prog

    def execute_program(self, program: List[ASTNode], grid: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """Executes the final precipitated program on a test grid."""
        for node in program:
            grid = node.execute(grid, mask)
        return grid

if __name__ == "__main__":
    synthesizer = CosmogonySynthesizer()
    dummy_train = [{"input": [[1,0],[0,1]], "output": [[2,0],[0,2]]}]
    prog = synthesizer.synthesize_rule("task_refined_v4", dummy_train)
    print("\nRefined Program Precipitate:")
    for n in prog:
        print(f"  - {n.operation} {n.params}")
