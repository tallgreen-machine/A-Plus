import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3.common.results_plotter import load_results, ts2xy
from utils.logger import log

def plot_results(log_folder: str, title: str = "Learning Curve"):
    """
    Plots the learning curve from a Stable Baselines3 log directory.

    :param log_folder: Path to the log directory.
    :param title: Title for the plot.
    """
    log.info(f"Plotting results from log folder: {log_folder}")
    x, y = ts2xy(load_results(log_folder), "timesteps")

    if len(x) == 0:
        log.warning("No results found to plot. Skipping plot generation.")
        return

    fig = plt.figure(title)
    plt.plot(x, y)
    plt.xlabel("Number of Timesteps")
    plt.ylabel("Rewards")
    plt.title(title)
    
    # Save the plot to a file
    plot_path = f"{log_folder}/learning_curve.png"
    plt.savefig(plot_path)
    log.info(f"Learning curve saved to {plot_path}")
    plt.close(fig)

def evaluate_model(model, env, n_steps=10):
    """
    Evaluates a trained model for a few steps and logs the actions.

    :param model: The trained model to evaluate.
    :param env: The environment to evaluate on.
    :param n_steps: The number of steps to evaluate for.
    """
    log.info(f"Evaluating model for {n_steps} steps...")
    obs, _ = env.reset()
    for i in range(n_steps):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        log.info(f"Step {i+1}: Action: {action}, Reward: {reward:.4f}")
        if terminated or truncated:
            log.info("Episode finished.")
            obs, _ = env.reset()
    log.info("Evaluation complete.")
