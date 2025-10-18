#!/usr/bin/env python3
"""
Stub live trader: loads latest embeddings + config, predicts action, and logs.
Replace with ccxt execution and real features.
"""
from __future__ import annotations

import numpy as np
from stable_baselines3 import PPO
from pathlib import Path

from .trading_env import CryptoTradingEnv


def main():
    symbols = ["BTC/USDT", "ETH/USDT"]
    env = CryptoTradingEnv(symbols=symbols, window=200)
    # Load model relative to this file's directory
    model_path = Path(__file__).resolve().parent / "models" / "ppo_trader"
    model = PPO.load(str(model_path))

    obs, _ = env.reset()
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    print({"action": action.tolist(), "reward": float(reward), "info": info})


if __name__ == "__main__":
    main()
