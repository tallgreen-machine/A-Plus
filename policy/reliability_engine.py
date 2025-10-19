# policy/reliability_engine.py
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import pandas as pd
import psycopg2
from strategies.pattern_library import Tier1Patterns
from shared.db import get_db_conn

class PatternAuditor:
    """
    CRITICAL: This module runs offline to ensure our patterns 
    still work. This is our defense against alpha decay.
    """
    
    def __init__(self):
        self.db_conn = get_db_conn()
        self.active_patterns_file = 'active_patterns.json'
        # Define the universe of patterns to check
        self.tier1_patterns = ['Liquidity Sweep', 'Fair Value Gap', 'Bullish Order Block'] # Add more as they are implemented

    def fetch_full_history(self, symbol="BTCUSD"):
        """Fetches all historical data for a symbol."""
        query = "SELECT * FROM market_data WHERE symbol = %s ORDER BY ts ASC;"
        df = pd.read_sql(query, self.db_conn, params=(symbol,))
        print(f"Found {len(df)} total historical records.")
        # Ensure numeric columns are of a numeric type, coercing errors
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows where numeric conversion failed, as they are unusable.
        df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
        
        return df

    def _simulate_trade(self, entry_price, future_data):
        """
        Simulates a trade with a fixed take-profit and stop-loss.
        Returns the exit price, exit time, and PnL.
        """
        take_profit_price = entry_price * 1.02
        stop_loss_price = entry_price * 0.99

        for _, row in future_data.iterrows():
            # Check for take profit
            if row['high'] >= take_profit_price:
                return take_profit_price, row['ts'], 2.0

            # Check for stop loss
            if row['low'] <= stop_loss_price:
                return stop_loss_price, row['ts'], -1.0
        
        # If neither TP nor SL is hit, we exit at the end of the period
        last_row = future_data.iloc[-1]
        exit_price = last_row['close']
        pnl = (exit_price / entry_price - 1) * 100
        return exit_price, last_row['ts'], pnl

    def _save_backtest_result(self, pattern_name, symbol, entry_time, entry_price, exit_time, exit_price, pnl_percentage, trade_type):
        """Saves the result of a single backtested trade to the database."""
        with self.db_conn.cursor() as cursor:
            query = """
                INSERT INTO backtest_results 
                (pattern_name, symbol, entry_time, entry_price, exit_time, exit_price, pnl_percentage, trade_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            try:
                # Explicitly cast numpy types to standard Python floats for psycopg2
                params = (
                    pattern_name,
                    symbol,
                    entry_time,
                    float(entry_price),
                    exit_time,
                    float(exit_price),
                    float(pnl_percentage),
                    trade_type
                )
                cursor.execute(query, params)
                self.db_conn.commit()
            except Exception as e:
                print(f"Error saving backtest result: {e}")
                self.db_conn.rollback()

    def _calculate_metrics(self, pattern_name):
        """
        Calculates performance metrics for a pattern from the backtest_results table.
        """
        query = "SELECT pnl_percentage FROM backtest_results WHERE pattern_name = %s;"
        df = pd.read_sql(query, self.db_conn, params=(pattern_name,))
        
        if df.empty:
            return None

        pnl_values = df['pnl_percentage']
    
    def audit_pattern(self, pattern_name, symbol="BTCUSD"):
        """
        Audits a single pattern by fetching data, detecting occurrences,
        and simulating trades.
        """
        print(f"Auditing pattern: {pattern_name}...")
        print(f"Fetching full history for {symbol}...")
        full_history = self.fetch_full_history(symbol)
        
        if full_history.empty:
            print(f"No historical data found for {symbol}. Skipping pattern {pattern_name}.")
            return

        # Dynamically get the detection method from Tier1Patterns
        patterns_instance = Tier1Patterns(symbol=symbol)
        detection_method_name = f"detect_{pattern_name.lower().replace(' ', '_')}"
        detection_method = getattr(patterns_instance, detection_method_name, None)

        if not detection_method:
            print(f"Detection method {detection_method_name} not found in Tier1Patterns. Skipping.")
            return

        # The detection method is an instance method, so we call it on the instance
        occurrences_list = detection_method(full_history)
        
        if not occurrences_list:
            print(f"No occurrences of {pattern_name} found. Skipping.")
            return
            
        # Convert list of tuples to a DataFrame for simulation
        occurrences = pd.DataFrame(occurrences_list, columns=['ts', 'close']).set_index('ts')
        print(f"Detected {len(occurrences)} occurrences of {pattern_name}.")

        if occurrences.empty:
            print(f"No occurrences of {pattern_name} found. Skipping.")
            return

        for index, occurrence in occurrences.iterrows():
            entry_price = occurrence['close']
            entry_time = index
            
            # Get data for 24 hours following the occurrence for simulation
            future_data = full_history[full_history['ts'] > entry_time].head(24)
            
            if not future_data.empty:
                exit_price, exit_time, pnl = self._simulate_trade(entry_price, future_data)
                self._save_backtest_result(pattern_name, symbol, entry_time, entry_price, exit_time, exit_price, pnl, 'LONG')

    def run_weekly_audit(self):
        """
        Main method to run the weekly audit of all Tier 1 patterns.
        """
        print("Starting weekly pattern audit...")
        with self.db_conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE backtest_results RESTART IDENTITY;")
            self.db_conn.commit()
            print("Cleared old backtest_results.")

        for pattern in self.tier1_patterns:
            self.audit_pattern(pattern)

        # After auditing, determine which patterns are reliable
        self.update_active_patterns()
        print("Weekly pattern audit complete.")

    def update_active_patterns(self):
        """
        Analyzes backtest results and updates the active_patterns.json file
        with patterns that meet the reliability criteria.
        """
        active_patterns = {}
        for pattern in self.tier1_patterns:
            metrics = self._calculate_metrics(pattern)
            if metrics and metrics['win_rate'] >= 0.6 and metrics['total_trades'] >= 10:
                active_patterns[pattern] = {
                    'win_rate': metrics['win_rate'],
                    'avg_pnl': metrics['avg_pnl'],
                    'total_trades': metrics['total_trades']
                }
        
        with open(self.active_patterns_file, 'w') as f:
            json.dump(active_patterns, f, indent=4)
        print(f"Active patterns saved to {self.active_patterns_file}")


if __name__ == "__main__":
    auditor = PatternAuditor()
    auditor.run_weekly_audit()

    def _simulate_trade(self, entry_price, future_data):
        """
        Simulates a trade with a fixed take-profit and stop-loss.
        Returns the exit price, exit time, and PnL.
        """
        take_profit_price = entry_price * 1.02
        stop_loss_price = entry_price * 0.99

        for _, row in future_data.iterrows():
            # Check for take profit
            if row['high'] >= take_profit_price:
                return take_profit_price, row['ts'], 2.0

            # Check for stop loss
            if row['low'] <= stop_loss_price:
                return stop_loss_price, row['ts'], -1.0
        
        # If neither TP nor SL is hit, we exit at the end of the period
        last_row = future_data.iloc[-1]
        exit_price = last_row['close']
        pnl = (exit_price / entry_price - 1) * 100
        return exit_price, last_row['ts'], pnl

    def _save_backtest_result(self, pattern_name, symbol, entry_time, entry_price, exit_time, exit_price, pnl_percentage, trade_type):
        """Saves the result of a single backtested trade to the database."""
        with self.db_conn.cursor() as cursor:
            query = """
                INSERT INTO backtest_results 
                (pattern_name, symbol, entry_time, entry_price, exit_time, exit_price, pnl_percentage, trade_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            try:
                # Explicitly cast numpy types to standard Python floats for psycopg2
                params = (
                    pattern_name,
                    symbol,
                    entry_time,
                    float(entry_price),
                    exit_time,
                    float(exit_price),
                    float(pnl_percentage),
                    trade_type
                )
                cursor.execute(query, params)
                self.db_conn.commit()
            except Exception as e:
                print(f"Error saving backtest result: {e}")
                self.db_conn.rollback()

    def _calculate_metrics(self, pattern_name):
        """
        Calculates performance metrics for a pattern from the backtest_results table.
        """
        query = "SELECT pnl_percentage FROM backtest_results WHERE pattern_name = %s;"
        df = pd.read_sql(query, self.db_conn, params=(pattern_name,))
        
        if df.empty:
            return None

        pnl_values = df['pnl_percentage']
        
        # Net Profit/Loss
        net_pnl = pnl_values.sum()

        # Profit Factor
        gross_profit = pnl_values[pnl_values > 0].sum()
        gross_loss = abs(pnl_values[pnl_values < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Max Drawdown
        cumulative_pnl = (1 + pnl_values / 100).cumprod()
        peak = cumulative_pnl.expanding(min_periods=1).max()
        drawdown = (cumulative_pnl - peak) / peak
        max_drawdown = abs(drawdown.min()) * 100

        return {
            "net_pnl_percentage": net_pnl,
            "profit_factor": profit_factor,
            "max_drawdown_percentage": max_drawdown,
            "win_rate": (pnl_values > 0).mean(),
            "total_trades": len(pnl_values)
        }

    def run_weekly_audit(self):
        """
        Re-tests all active patterns against the last 5 years of data
        to see if their performance characteristics have changed.
        """
        print("Starting weekly pattern audit...")
        active_patterns = []

        # Clear previous backtest results for a clean slate
        with self.db_conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE backtest_results RESTART IDENTITY;")
            self.db_conn.commit()
            print("Cleared old backtest_results.")

        for pattern_name in self.tier1_patterns:
            print(f"Auditing pattern: {pattern_name}...")
            
            # Instantiate the pattern library for the specific pattern
            patterns = Tier1Patterns()
            
            # Fetch the full history for the symbol the pattern uses
            symbol = patterns.symbol
            print(f"Fetching full history for {symbol}...")
            full_history = self.fetch_full_history(symbol)
            print(f"Found {len(full_history)} total historical records.")

            # Detect all occurrences of the pattern in the history
            if pattern_name == 'Liquidity Sweep':
                occurrences = patterns.detect_liquidity_sweep(full_history)
            elif pattern_name == 'Fair Value Gap':
                occurrences = patterns.detect_fair_value_gap(full_history)
            elif pattern_name == 'Bullish Order Block':
                occurrences = patterns.detect_bullish_order_block(full_history)
            else:
                print(f"Warning: No detection method for pattern '{pattern_name}'. Skipping.")
                continue
            
            print(f"Detected {len(occurrences)} occurrences of {pattern_name}.")

            if not occurrences:
                print(f"No occurrences of {pattern_name} found. Skipping.")
                continue

            # Backtest each occurrence
            for i, (ts, price) in enumerate(occurrences):
                print(f"  Backtesting occurrence #{i+1} at {ts} with entry price {price}")
                # Get the data *after* the pattern was detected
                future_data = full_history[full_history['ts'] > ts]
                
                if future_data.empty:
                    print(f"    -> No future data available to simulate trade. Skipping.")
                    continue

                # Simulate the trade
                exit_price, exit_time, pnl = self._simulate_trade(price, future_data)
                print(f"    -> Trade simulated. Exit at {exit_time} with price {exit_price}. PnL: {pnl:.2f}%")

                # Save the result
                self._save_backtest_result(pattern_name, symbol, ts, price, exit_time, exit_price, pnl, 'long')

            # Calculate and print metrics
            metrics = self._calculate_metrics(pattern_name)
            
            if metrics:
                print(f"  - Found {metrics['total_trades']} occurrences.")
                print(f"  - Win Rate: {metrics['win_rate'] * 100:.2f}%")
                print(f"  - Net P/L: {metrics['net_pnl_percentage']:.2f}%")
                
                profit_factor_display = "inf" if metrics['profit_factor'] is None else f"{metrics['profit_factor']:.2f}"
                print(f"  - Profit Factor: {profit_factor_display}")

                print(f"  - Max Drawdown: {metrics['max_drawdown_percentage']:.2f}%")

                # Activation criteria: positive PnL and high profit factor
                if metrics['net_pnl_percentage'] > 0 and (metrics['profit_factor'] is None or metrics['profit_factor'] > 1.2):
                    active_patterns.append({
                        'name': pattern_name,
                        'metrics': metrics
                    })

        print("Weekly pattern audit complete.")
        # Save the results to a file
        with open(self.active_patterns_file, 'w') as f:
            json.dump(active_patterns, f, indent=2)
        print(f"Active patterns saved to {self.active_patterns_file}")

if __name__ == "__main__":
    auditor = PatternAuditor()
    auditor.run_weekly_audit()
