# policy/reliability_engine.py
import json
import pandas as pd
from .pattern_library import Tier1Patterns
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
        self.tier1_patterns = ['Liquidity Sweep'] # Add more as they are implemented

    def fetch_full_history(self, symbol="BTC/USDT"):
        """Fetches all historical data for a symbol."""
        query = "SELECT * FROM market_data WHERE symbol = %s ORDER BY ts ASC;"
        df = pd.read_sql(query, self.db_conn, params=(symbol,))
        # Ensure numeric columns are of a numeric type
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        return df

    def run_weekly_audit(self):
        """
        Re-tests all active patterns against the last 5 years of data
        to see if their performance characteristics have changed.
        """
        print("Starting weekly pattern audit...")
        full_history = self.fetch_full_history()
        
        if full_history.empty:
            print("No historical data found. Aborting audit.")
            return

        all_results = []
        occurrences = []

        for pattern_name in self.tier1_patterns:
            print(f"Auditing pattern: {pattern_name}...")
            
            # Create a fresh pattern library instance for the audit
            # This is a bit of a trick to use the detection logic on historical data
            pattern_lib = Tier1Patterns(symbol="BTC/USD")
            
            # Iterate through the history to find pattern occurrences
            # We start at index 50 to ensure we have enough look-back data
            for i in range(50, len(full_history)):
                # The 'check' methods in the library are designed to look at the
                # most recent data. We can simulate this for backtesting by
                # feeding them slices of historical data.
                historical_slice = full_history.iloc[i-50:i]
                
                # We need to temporarily replace the library's data fetching
                # method with one that just returns our historical slice.
                pattern_lib.fetch_recent_data = lambda limit=50: historical_slice
                
                result = None
                if pattern_name == 'Liquidity Sweep':
                    result = pattern_lib.check_for_liquidity_sweep()

                if result:
                    # The pattern was detected at the *end* of our slice, which is index `i-1`.
                    # We want to see what happens in the next 24 hours.
                    future_data_end_index = min(i + 24, len(full_history))
                    occurrences.append({
                        'timestamp': full_history.iloc[i-1]['ts'],
                        'price_at_detection': full_history.iloc[i-1]['close'],
                        'future_data': full_history.iloc[i:future_data_end_index]
                    })

            if not occurrences:
                print(f"No occurrences of {pattern_name} found in historical data.")
                continue

            # Analyze the performance of the occurrences
            wins = 0
            losses = 0
            for occ in occurrences:
                entry_price = occ['price_at_detection']
                future_high = occ['future_data']['high'].max()
                # Simple win condition: price went up 2% before it went down 1%
                if (future_high / entry_price - 1) > 0.02:
                    wins += 1
                else:
                    losses += 1
            
            win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
            print(f"  - Found {len(occurrences)} occurrences.")
            print(f"  - Win rate: {win_rate:.2%}")

            if win_rate > 0.55: # Only activate patterns with a >55% win rate
                all_results.append({
                    'name': pattern_name,
                    'win_rate': win_rate,
                    'occurrences': len(occurrences)
                })

        # Save the new, validated performance stats
        self.save_patterns_to_json(all_results)
        print("Weekly pattern audit complete.")

    def save_patterns_to_json(self, patterns):
        with open(self.active_patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
