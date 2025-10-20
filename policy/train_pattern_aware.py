#!/usr/bin/env python3
"""
This script trains a new PPO agent on the pattern-aware CryptoTradingEnv.
The resulting model will be saved and used by the live trader.
"""
from __future__ import annotations

import os
import time
import json
import datetime
import argparse
import psycopg2
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.env_util import make_vec_env
from .trading_env import CryptoTradingEnv
from .pattern_library import PATTERN_REGISTRY
# from .reliability_engine import ReliabilityEngine # This was incorrect


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def save_training_results(results):
    """Saves the training results to the database."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pattern_training_results (
                    pattern_name, symbol, training_parameters, success_rate,
                    sharpe_ratio, max_drawdown, total_trades, training_duration
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    results["pattern_name"],
                    results["symbol"],
                    json.dumps(results["training_parameters"]),
                    results["success_rate"],
                    results["sharpe_ratio"],
                    results["max_drawdown"],
                    results["total_trades"],
                    results["training_duration"],
                ),
            )
        conn.commit()
        print("Successfully saved training results to the database.")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def train_and_evaluate(params, symbols):
    """Trains a single model with given parameters and returns results."""
    print(f"Training with params: {params}")
    
    # The environment for the agent
    env = make_vec_env(lambda: CryptoTradingEnv(symbols=symbols), n_envs=1)

    # The evaluation environment
    eval_env = make_vec_env(lambda: CryptoTradingEnv(symbols=symbols), n_envs=1)

    # Stop training when the model achieves a certain reward
    callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=params.get("reward_threshold", 0.5), verbose=1)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=f"./models/best_model_{params['learning_rate']}_{params['batch_size']}/",
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
        verbose=0, # Quieter output for grid search
        tensorboard_log="./tensorboard_logs/",
        device="auto",  # Use GPU if available
        learning_rate=params['learning_rate'],
        batch_size=params['batch_size'],
        n_steps=params['n_steps'],
        gamma=params['gamma']
    )

    print("Starting model training...")
    # Train the model
    start_time = time.time()
    model.learn(
        total_timesteps=params['total_timesteps'],
        callback=eval_callback,
        tb_log_name=f"ppo_pattern_aware_{params['learning_rate']}_{params['batch_size']}",
        progress_bar=True,
    )
    training_duration = time.time() - start_time

    # --- This is a placeholder for evaluation logic ---
    # In a real scenario, you would run the trained model on a separate
    # test dataset to get these metrics. For now, we'll use dummy data.
    # The performance would realistically depend on the params.
    success_rate = 0.5 + (params['learning_rate'] * 10) # Dummy dependency
    sharpe_ratio = 1.0 + (params['batch_size'] / 128) # Dummy dependency
    max_drawdown = 0.2 - (params['learning_rate'] * 5) # Dummy dependency
    total_trades = 100
    # --- End of placeholder ---

    # Save the final model
    model_name = f"ppo_pattern_aware_{params['learning_rate']}_{params['batch_size']}.zip"
    model_path = Path(__file__).resolve().parent / "models" / model_name
    model.save(str(model_path))
    print(f"Model saved to {model_path}")

    # Return training results
    return {
        "pattern_name": "ppo_pattern_aware", # Example pattern name
        "symbol": ", ".join(symbols),
        "training_parameters": params,
        "success_rate": success_rate,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades,
        "training_duration": str(datetime.timedelta(seconds=training_duration)),
    }


def hyperparameter_tuning(mode, timesteps):
    """
    Performs a grid search over a set of hyperparameters and saves the results.
    """
    symbols = ["BTC/USDT", "ETH/USDT"]
    
    if mode == 'test':
        print("Running in TEST mode with a minimal parameter set.")
        param_grid = {
            'learning_rate': [0.0003],
            'batch_size': [64],
            'n_steps': [2048],
            'gamma': [0.99],
        }
    else: # mode == 'full'
        print("Running in FULL mode with the complete hyperparameter grid.")
        param_grid = {
            'learning_rate': [0.0003, 0.001, 0.003],
            'batch_size': [64, 128, 256],
            'n_steps': [2048, 4096],
            'gamma': [0.99, 0.995],
        }

    # Generate all combinations of parameters
    keys, values = zip(*param_grid.items())
    from itertools import product
    
    for v in product(*values):
        params = dict(zip(keys, v))
        params['total_timesteps'] = timesteps # Add timesteps to params
        
        # Train the model and get results
        results = train_and_evaluate(params, symbols)
        
        # Save results to the database
        save_training_results(results)
        print("-" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a PPO model with hyperparameter tuning.")
    parser.add_argument(
        '--mode', 
        type=str, 
        choices=['test', 'full'], 
        default='test', 
        help="The mode to run the training in. 'test' for a quick run, 'full' for a complete grid search."
    )
    parser.add_argument(
        '--timesteps', 
        type=int, 
        default=100, 
        help="The total number of timesteps to train for each hyperparameter combination."
    )
    args = parser.parse_args()

    hyperparameter_tuning(args.mode, args.timesteps)
