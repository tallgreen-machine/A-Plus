#!/usr/bin/env python3
"""
Stub PPO training with the CryptoTradingEnv. Replace data-driven returns and proper reward.

Tuned for low-memory (4GB RAM):
- n_steps=256, n_epochs=2, small MLP (64x64), CPU device
- total_timesteps can be overridden via TIMESTEPS env var
"""
import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from pathlib import Path

from .trading_env import CryptoTradingEnv


def make_env():
    symbols = ["BTC/USDT", "ETH/USDT"]
    # Slightly smaller window to reduce observation size
    return CryptoTradingEnv(symbols=symbols, window=150)


def main():
    env = make_vec_env(make_env, n_envs=1)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=256,
        batch_size=64,
        n_epochs=2,
        device="cpu",
        policy_kwargs=dict(net_arch=[64, 64]),
    )
    total_ts = int(os.getenv("TIMESTEPS", "2000"))
    model.learn(total_timesteps=total_ts)
    # Save model relative to this file's directory
    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "ppo_trader"
    model.save(str(model_path))
    print(f"Saved {model_path}.zip")


if __name__ == "__main__":
    main()
