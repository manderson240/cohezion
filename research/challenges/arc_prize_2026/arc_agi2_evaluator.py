import json
import os
import torch
import numpy as np
from arc_jepa import ARCWorldModel, ARCGameEncoder


class ARCAGI2Evaluator:
    """Evaluator for ARC-AGI-2 (static) using JEPA-based reasoning."""

    def __init__(self, data_dir="data/arc-agi-2-repo/data/training", device="cpu"):
        self.data_dir = data_dir
        self.device = device
        self.encoder = ARCGameEncoder().to(device)
        # We can use the encoder to compare input/output embeddings

    def load_task(self, task_id):
        path = os.path.join(self.data_dir, f"{task_id}.json")
        with open(path, "r") as f:
            return json.load(f)

    def solve_task(self, task_id):
        task = self.load_task(task_id)
        print(f"Solving task: {task_id}")

        # 1. Encode all training pairs
        train_embeddings = []
        for pair in task["train"]:
            inp = self._preprocess(pair["input"])
            out = self._preprocess(pair["output"])
            with torch.no_grad():
                z_inp = self.encoder(inp)
                z_out = self.encoder(out)
            train_embeddings.append((z_inp, z_out))

        # 2. Find transformation (placeholder for Phase 4 logic)
        # In a real JEPA solution, we would find an action that maps z_inp to z_out
        print(f"  Encoded {len(train_embeddings)} training pairs.")

        # 3. Predict test output
        test_input = self._preprocess(task["test"][0]["input"])
        with torch.no_grad():
            z_test_inp = self.encoder(test_input)
            # For now, just return input as prediction (0% accuracy baseline)
            z_test_out = z_test_inp

        return task["test"][0]["input"]  # Dummy return

    def _preprocess(self, grid):
        grid = np.array(grid, dtype=np.uint8)
        h, w = grid.shape
        padded = np.zeros((1, 1, 64, 64), dtype=np.uint8)
        padded[0, 0, : min(h, 64), : min(w, 64)] = grid[:64, :64]
        return torch.from_numpy(padded).to(self.device)


if __name__ == "__main__":
    evaluator = ARCAGI2Evaluator()
    # Test on the first task in training
    task_files = os.listdir("data/arc-agi-2-repo/data/training")
    if task_files:
        task_id = task_files[0].split(".")[0]
        evaluator.solve_task(task_id)
