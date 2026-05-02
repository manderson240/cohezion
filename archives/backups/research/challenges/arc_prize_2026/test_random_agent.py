from arc_gym_wrapper import ARCGymEnv


def run_random_agent(game_id="ls20", num_episodes=5):
    print(f"Testing random agent on game: {game_id}")
    env = ARCGymEnv(game_id=game_id, render_mode="headless")

    total_rewards = 0
    for episode in range(num_episodes):
        obs, info = env.reset()
        terminated = False
        truncated = False
        episode_reward = 0
        steps = 0

        while not (terminated or truncated) and steps < 100:
            # Sample random action
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            steps += 1

        total_rewards += episode_reward
        print(
            f"Episode {episode + 1}: Reward = {episode_reward}, Steps = {steps}, Final State = {info['state']}"
        )

    print(f"Average Reward: {total_rewards / num_episodes}")
    env.close()


if __name__ == "__main__":
    run_random_agent()
