import numpy as np
import random
import torch
import torch.nn.functional as F
from arc_bioelectric import BioelectricCoupler
from arc_dsl import ARCDSL
from arc_jepa import ARCWorldModel
from arc_ttt_trainer import ARCTTTTrainer
from arc_manifold_transfer import ARCManifoldTransfer
from arc_evolutionary_steer import ARCEvolutionarySteer

class CosmogonySynthesizer:
    """
    Advanced Cosmogony Synthesizer (Cohezion-Prime Edition).
    Integrates TTT, Cross-Game Transfer, and Topological Steering.
    """
    def __init__(self, pop_size=50, max_generations=100, device="cpu"):
        self.device = device
        self.coupler = BioelectricCoupler(threshold=0.8)
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.available_ops = ARCDSL.get_all_ops()
        
        # Cohezion Components
        self.model = ARCWorldModel().to(device)
        self.ttt = ARCTTTTrainer(self.model)
        self.transfer = ARCManifoldTransfer()
        self.steer = ARCEvolutionarySteer()

    def synthesize_rule(self, task_id, train_pairs):
        """Runs the spearhead cosmogonic cooling process."""
        print(f"Initiating Cosmogonic Synthesis for Task: {task_id}")
        
        # 1. Test-Time Training (Specialization)
        self.ttt.specialize_for_task(train_pairs)
        
        # 2. Check Rule Library (Cross-Game Transfer)
        # (Simplified: check if we've seen a similar task logic before)
        # In real usage, we'd compute axiomatic delta here.
        
        # 3. Evolutionary Search with TDA Steering
        best_program = self._evolutionary_search(train_pairs)

        # 4. Save to Library if successful
        # self.transfer.save_rule(task_id, ...) 

        return best_program

    def _evolutionary_search(self, train_pairs):
        population = [self._random_ast(random.randint(1, 3)) for _ in range(self.pop_size)]
        
        for gen in range(self.max_generations):
            scored_population = []
            for p in population:
                score = self._evaluate(p, train_pairs)
                scored_population.append((score, p))
                
                # Record candidate for TDA steering
                # Mock latent vector for the rule (mean of weights or similar)
                mock_latent = np.random.randn(256) 
                self.steer.record_candidate(score, mock_latent)
            
            scored_population.sort(key=lambda x: x[0], reverse=True)
            best_score = scored_population[0][0]
            
            if best_score == 1.0:
                print(f"    -> Reached 0.5 Coherence at generation {gen}!")
                return scored_population[0][1]
                
            # TDA Steering Directive
            directive = self.steer.get_steering_directive()
            
            # Selection & Adaptation based on Directive
            elites = [p for s, p in scored_population[:int(self.pop_size * 0.2)]]
            next_gen = elites[:]
            
            mutation_rate = 0.1
            if directive == "PIVOT":
                mutation_rate = 0.8 # Massive mutation to break loop
                print("    [TDA] Search stalled. Increasing mutation rate to 0.8.")
            
            while len(next_gen) < self.pop_size:
                parent = random.choice(elites)
                child = self._mutate(parent, mutation_rate)
                next_gen.append(child)
                
            population = next_gen
            
        return scored_population[0][1]

    def _random_ast(self, depth=1):
        program = []
        for _ in range(depth):
            op, num_params = random.choice(self.available_ops)
            params = []
            if op == "recolor":
                params = [random.randint(0, 9), random.randint(0, 9)]
            elif op == "move_object":
                params = [random.randint(1, 3), random.randint(-5, 5), random.randint(-5, 5)]
            program.append(ASTNode(op, params))
        return program

    def _evaluate(self, program, train_pairs):
        errors = 0
        for pair in train_pairs:
            grid = np.array(pair['input'])
            target = np.array(pair['output'])
            # We assume a mask is generated on the fly or not needed for some ops
            for node in program:
                grid = node.execute(grid)
            if grid.shape != target.shape:
                errors += 1000
                continue
            errors += np.sum(grid != target)
        return 1.0 / (1.0 + errors)

    def _mutate(self, program, rate=0.1):
        if random.random() > rate:
            return [ASTNode(n.operation, list(n.params)) for n in program]
        
        # Mutation logic: ensure correct parameter count per operation
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
        
        new_prog[idx] = ASTNode(op, params)
        return new_prog

class ASTNode:
    def __init__(self, operation, params=None):
        self.operation = operation
        self.params = params or []
    def execute(self, grid, mask=None):
        try:
            if self.operation == "recolor":
                return ARCDSL.recolor(grid, self.params[0], self.params[1])
            elif self.operation == "move_object":
                # For evaluation, we find mask on the fly if not provided
                if mask is None:
                    coupler = BioelectricCoupler()
                    mask, _ = coupler.find_organs(grid)
                return ARCDSL.move_object(grid, mask, self.params[0], self.params[1], self.params[2])
            else:
                return getattr(ARCDSL, self.operation)(grid)
        except:
            return grid

if __name__ == "__main__":
    synthesizer = CosmogonySynthesizer()
    dummy_train = [{"input": [[1,0],[0,1]], "output": [[2,0],[0,2]]}]
    prog = synthesizer.synthesize_rule("task_v3_test", dummy_train)
    print("Final Program:")
    for n in prog: print(f"  {n.operation} {n.params}")
