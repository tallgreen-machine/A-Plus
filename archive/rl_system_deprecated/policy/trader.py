# policy/trader.py
import time
import json
from .pattern_library import Tier1Patterns
# from DataFeed import LiveDataFeed # Placeholder for data feed

class SimpleTrader:
    """
    This bot does NOT learn.
    It simply loads the list of 'Tier 1' patterns and executes
    when one is detected. It is patient.
    """
    
    def __init__(self, symbol="BTC/USDT"):
        self.capital = 10000
        self.positions = []
        self.pattern_library = Tier1Patterns(symbol=symbol)
        
        # This file is updated by the ReliabilityEngine
        self.active_patterns_file = 'active_patterns.json'
        self.active_patterns = self.load_active_patterns_from_json() 
        self.pattern_functions = {
            'Liquidity Sweep': self.pattern_library.check_for_liquidity_sweep,
            'Capitulation': self.pattern_library.check_for_capitulation_volume,
            'Funding Extreme': self.pattern_library.check_for_funding_rate_extreme
            # ... maps pattern names to their detection functions
        }
        print(f"Trader loaded for symbol {symbol}. Monitoring for {len(self.active_patterns)} patterns.")

    def load_active_patterns_from_json(self):
        try:
            with open(self.active_patterns_file, 'r') as f:
                # We only need the names of the patterns
                return [p['name'] for p in json.load(f)]
        except FileNotFoundError:
            print("Warning: active_patterns.json not found. No patterns will be monitored.")
            return []

    def has_open_position(self):
        return len(self.positions) > 0

    def manage_position(self):
        # This is a placeholder for a more sophisticated position management logic,
        # which would include checking for stop-loss or take-profit conditions.
        # For now, we'll just print the status.
        for p in self.positions:
            print(f"  -> Managing open position: {p['size']:.4f} {p['symbol']} entered at ${p['entry_price']:.2f}")
            # In a real system, you would fetch the current price and check against exit criteria.


    def run_trading_loop(self):
        """
        The main execution loop.
        1. Fetches the latest data.
        2. Checks for active patterns.
        3. Executes a trade if a pattern is detected.
        4. Manages any open positions.
        """
        print("Starting trading loop...")
        while True:
            if self.has_open_position():
                self.manage_position()
                time.sleep(60) # Check on position every minute
                continue

            # --- This is the core logic ---
            # The pattern library fetches its own data, so we just call the methods
            for pattern_name in self.active_patterns:
                detection_func = self.pattern_functions.get(pattern_name)
                
                if detection_func:
                    result = detection_func()
                    
                    if result:
                        print(f"🚀 PATTERN DETECTED: {result['pattern_name']} with confidence {result['confidence']:.2f}")
                        self.execute_trade(result)
                        break # Only one trade at a time
            
            print(f"({time.strftime('%H:%M:%S')}) No active patterns detected. Waiting for next candle...")
            time.sleep(60) # Wait for next 1-minute candle

    def execute_trade(self, trade_signal):
        # For now, this is a simulation. In a real scenario, this would
        # interact with an exchange API.
        confidence = trade_signal['confidence']
        price = trade_signal['details']['price']
        position_size = self.calculate_position_size(self.capital, confidence, price)
        
        print(f"  -> EXECUTING TRADE: Buying {position_size:.4f} units at ${price:.2f}")
        self.positions.append({
            'entry_price': price,
            'size': position_size,
            'symbol': self.pattern_library.symbol,
            'pattern': trade_signal['pattern_name']
        })
        # In a real system, you'd also set a stop-loss and take-profit here.

    def calculate_position_size(self, capital, confidence, price):
        # Simple position sizing: risk 2% of capital, adjusted by pattern confidence.
        base_risk_amount = capital * 0.02
        adjusted_risk_amount = base_risk_amount * confidence
        return adjusted_risk_amount / price

