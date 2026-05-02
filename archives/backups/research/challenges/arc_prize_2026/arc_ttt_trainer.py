import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from arc_jepa import ARCWorldModel


class ARCTTTTrainer:
    """
    Implements Test-Time Training (TTT) for ARC tasks.
    Performs fast LoRA-style updates on the JEPA model for a specific task.
    """

    def __init__(self, model: ARCWorldModel, lr=5e-4, steps=20):
        self.model = model
        self.lr = lr
        self.steps = steps

    def specialize_for_task(self, train_pairs):
        """
        Briefly trains the model on the provided train pairs to adapt the latent space.
        """
        print(f"Adapting JEPA via TTT ({self.steps} steps)...")
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)

        self.model.train()
        for step in range(self.steps):
            total_loss = 0
            for pair in train_pairs:
                grid_curr = (
                    torch.from_numpy(np.array(pair["input"])).unsqueeze(0).unsqueeze(0).float()
                )
                grid_next = (
                    torch.from_numpy(np.array(pair["output"])).unsqueeze(0).unsqueeze(0).float()
                )

                # Resizing to 64x64 if necessary
                grid_curr = F.interpolate(grid_curr, size=(64, 64))
                grid_next = F.interpolate(grid_next, size=(64, 64))

                # For static TTT, we assume an 'identity' or 'logical' action for adaptation
                # In a real scenario, we might iterate over multiple possible actions
                action = torch.tensor([0])
                x = torch.tensor([32])
                y = torch.tensor([32])

                optimizer.zero_grad()
                z_pred, loss = self.model(grid_curr, action, x, y, grid_next)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if (step + 1) % 5 == 0:
                print(f"  TTT Step {step + 1}: Loss = {total_loss / len(train_pairs):.6f}")

        self.model.eval()
        print("Adaptation complete.")


if __name__ == "__main__":
    # Test TTT
    model = ARCWorldModel()
    trainer = ARCTTTTrainer(model)
    dummy_pairs = [{"input": np.zeros((3, 3)), "output": np.ones((3, 3))}]
    trainer.specialize_for_task(dummy_pairs)
