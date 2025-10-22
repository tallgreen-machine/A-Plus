#!/usr/bin/env python3
"""
This script trains a new PPO agent on the pattern-aware CryptoTradingEnv.
The resulting mo    # Ensure n_steps is not greater than total_timesteps, and is at least 1
    n_steps = min(params['n_steps'], params['total_timesteps'])
    if n_steps == 0:
        n_steps = 1

    model = PPO(
        "MlpPolicy",
        train_env,
        verbose=0, # Quieter output for grid search
        tensorboard_log="./tensorboard_logs/",
        device="auto",  # Use GPU if available
        learning_rate=params['learning_rate'],
        batch_size=params['batch_size'],
        n_steps=n_steps,
        gamma=params['gamma']
    ) saved and used by the live trader.
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
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold, CallbackList
from .callbacks import ProgressLoggingCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor
from .trading_env import CryptoTradingEnv
from .pattern_library import PATTERN_REGISTRY
from .validate import plot_results, evaluate_model
# from .reliability_engine import ReliabilityEngine # This was incorrect
from utils.logger import log # Import logger


def get_db_connection():
    """Establishes and returns a database connection."""
    log.info("Attempting to connect to the database...")
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        log.info("Database connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        log.error(f"Error connecting to the database: {e}")
        return None

def save_training_results(results):
    """Saves the training results to the database."""
    log.info("Saving training results to the database...")
    conn = get_db_connection()
    if conn is None:
        log.error("Could not save training results, no database connection.")
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
        log.info("Successfully saved training results to the database.")
    except psycopg2.Error as e:
        log.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def train_and_evaluate(params, symbols):
    """Trains a single model with given parameters and returns results."""
    log.info(f"Training with params: {params}")
    log_folder = "./logs/"
    
    # The environment for the agent
    log.info("Creating training environment...")
    train_env = CryptoTradingEnv(symbols=symbols, total_timesteps=params['total_timesteps'])
    train_env = Monitor(train_env, log_folder)
    check_env(train_env)  # Check the environment
    log.info("Training environment created.")

    # The evaluation environment
    log.info("Creating evaluation environment...")
    eval_env = CryptoTradingEnv(symbols=symbols, total_timesteps=params['total_timesteps'])
    eval_env = Monitor(eval_env, log_folder)
    check_env(eval_env) # Check the environment
    log.info("Evaluation environment created.")

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
    progress_callback = ProgressLoggingCallback()
    callback_list = CallbackList([eval_callback, progress_callback])

    # Define the model
    log.info("Defining the PPO model...")
    
    # Ensure n_steps is not greater than total_timesteps, and is at least 1
    n_steps = min(params['n_steps'], params['total_timesteps'])
    if n_steps == 0:
        n_steps = 1

    model = PPO(
        "MlpPolicy",
        train_env,
        verbose=0, # Quieter output for grid search
        tensorboard_log="./tensorboard_logs/",
        device="auto",  # Use GPU if available
        learning_rate=params['learning_rate'],
        batch_size=params['batch_size'],
        n_steps=n_steps,
        gamma=params['gamma']
    )
    log.info("PPO model defined.")

    log.info("Starting model training...")
    # Train the model
    start_time = time.time()
    model.learn(
        total_timesteps=params['total_timesteps'],
        callback=callback_list,
        tb_log_name=f"ppo_pattern_aware_{params['learning_rate']}_{params['batch_size']}",
        progress_bar=False, # Disable SB3 progress bar
    )
    training_duration = time.time() - start_time
    log.info(f"Model training completed in {training_duration:.2f} seconds.")

    # --- Validation ---
    log_folder = "./logs/"
    plot_results(log_folder, title=f"PPO Learning Curve {params['learning_rate']}_{params['batch_size']}")
    evaluate_model(model, eval_env, n_steps=10)
    # --- End Validation ---

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
    log.info(f"Saving model to {model_path}...")
    model.save(str(model_path))
    log.info("Model saved.")

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
    log.info(f"Starting hyperparameter tuning in '{mode}' mode with {timesteps} timesteps.")
    symbols = ["BTC/USDT", "ETH/USDT"]
    
    if mode == 'test':
        log.info("Running in TEST mode with a minimal parameter set.")
        param_grid = {
            'learning_rate': [0.0003],
            'batch_size': [64],
            'n_steps': [2048],
            'gamma': [0.99],
        }
    else: # mode == 'full'
        log.info("Running in FULL mode with the complete hyperparameter grid.")
        param_grid = {
            'learning_rate': [0.0003, 0.001, 0.003],
            'batch_size': [64, 128, 256],
            'n_steps': [2048, 4096],
            'gamma': [0.99, 0.995],
        }

    # Generate all combinations of parameters
    keys, values = zip(*param_grid.items())
    from itertools import product
    
    param_combinations = list(product(*values))
    log.info(f"Generated {len(param_combinations)} parameter combinations for grid search.")

    for i, v in enumerate(param_combinations):
        params = dict(zip(keys, v))
        params['total_timesteps'] = timesteps # Add timesteps to params
        
        log.info(f"Grid search step {i+1}/{len(param_combinations)}: {params}")
        # Train the model and get results
        results = train_and_evaluate(params, symbols)
        
        # Save results to the database
        save_training_results(results)
        log.info("-" * 80)
    
    log.info("Hyperparameter tuning finished.")

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
    
    log.info("Script started.")
    hyperparameter_tuning(args.mode, args.timesteps)
    log.info("Script finished.")
