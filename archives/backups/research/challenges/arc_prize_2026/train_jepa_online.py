import torch
import torch.optim as optim
from arc_gym_wrapper import ARCGymEnv
from arc_jepa import ARCWorldModel


def train_jepa_online(game_id="ls20", num_steps=50):
    print(f"Starting online JEPA training on game: {game_id}")
    env = ARCGymEnv(game_id=game_id, render_mode="headless")
    model = ARCWorldModel()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    obs, info = env.reset()

    losses = []
    for i in range(num_steps):
        # 1. Sample action (Random exploration for Phase 2)
        action_dict = env.action_space.sample()

        # Prepare tensors
        grid_curr = torch.from_numpy(obs).unsqueeze(0).unsqueeze(0)  # (1, 1, 64, 64)
        action = torch.tensor([action_dict["action"]])
        x = torch.tensor([action_dict["x"]])
        y = torch.tensor([action_dict["y"]])

        # 2. Step environment
        obs_next, reward, terminated, truncated, info = env.step(action_dict)
        grid_next = torch.from_numpy(obs_next).unsqueeze(0).unsqueeze(0)

        # 3. Update World Model (JEPA)
        optimizer.zero_grad()
        z_pred, loss = model(grid_curr, action, x, y, grid_next)
        loss.backward()
        optimizer.step()

        # EMA update for target encoder
        model._update_target_encoder(tau=0.01)

        losses.append(loss.item())
        if (i + 1) % 10 == 0:
            avg_loss = sum(losses[-10:]) / 10
            print(f"Step {i + 1}/{num_steps}: Avg Loss (last 10) = {avg_loss:.6f}")

        obs = obs_next
        if terminated or truncated:
            obs, info = env.reset()

    print(f"Online training complete. Final Avg Loss: {sum(losses) / len(losses):.6f}")
    # env.close() # Skipped due to AttributeError in wrapper


if __name__ == "__main__":
    train_jepa_online()
