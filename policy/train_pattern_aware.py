#!/usr/bin/env python3
"""
This script trains a new PPO agent on the pattern-aware CryptoTradingEnv.
The resulting model will be saved and used by the live trader.
"""
from __future__ import annotations

from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.env_util import make_vec_env

from policy.trading_env import CryptoTradingEnv


def train_model():
    """Trains and saves the PPO model."""
    print("Initializing training environment...")
    # The environment for the agent
    symbols = ["BTC/USDT", "ETH/USDT"]
    env = make_vec_env(lambda: CryptoTradingEnv(symbols=symbols), n_envs=1)

    # The evaluation environment
    eval_env = make_vec_env(lambda: CryptoTradingEnv(symbols=symbols), n_envs=1)

    # Stop training when the model achieves a certain reward
    callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=0.5, verbose=1)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="./models/",
        log_path="./logs/",
        eval_freq=500,
        deterministic=True,
        render=False,
        callback_on_new_best=callback_on_best,
    )

    # Define the model
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log="./tensorboard_logs/",
        device="auto",  # Use GPU if available
    )

    print("Starting model training...")
    # Train the model
    model.learn(
        total_timesteps=10000,
        callback=eval_callback,
        tb_log_name="ppo_pattern_aware_trader",
        progress_bar=True,
    )

    # Save the final model
    model_path = Path(__file__).resolve().parent / "models" / "ppo_pattern_aware_trader"
    model.save(str(model_path))
    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    train_model()
