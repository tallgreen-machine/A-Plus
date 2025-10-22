import json
import pandas as pd
from strategies.base_strategy import BaseStrategy
from strategies.pattern_library import Tier1Patterns
from core.event_system import SignalEvent
from utils.logger import log

class AuditedPatternStrategy(BaseStrategy):
    """
    A strategy that only acts on patterns that have been pre-vetted
    by the offline PatternAuditor.
    """
    def __init__(self, symbol: str, data: dict):
        super().__init__(symbol, data)
        self.active_patterns_file = 'active_patterns.json'
        self.active_patterns = self._load_active_patterns()
        self.pattern_library = Tier1Patterns(symbol=symbol)
        self.pattern_detection_map = {
            "Liquidity Sweep": self.pattern_library.detect_liquidity_sweep,
            "Fair Value Gap": self.pattern_library.detect_fair_value_gap,
            "Bullish Order Block": self.pattern_library.detect_bullish_order_block,
        }
        log.info(f"AuditedPatternStrategy initialized for {symbol} with {len(self.active_patterns)} active patterns.")

    def _load_active_patterns(self) -> list:
        """Loads the list of validated, profitable patterns from the JSON file."""
        try:
            with open(self.active_patterns_file, 'r') as f:
                patterns = json.load(f)
                # We only need the names of the patterns
                return [p['name'] for p in patterns]
        except FileNotFoundError:
            log.warning(f"'{self.active_patterns_file}' not found. No patterns will be monitored by AuditedPatternStrategy.")
            return []
        except json.JSONDecodeError:
            log.error(f"Error decoding JSON from '{self.active_patterns_file}'.")
            return []

    def check_signal(self):
        """
        Checks for signals from the active, audited patterns.
        """
        if not self.active_patterns:
            return None

        # For this strategy, we'll focus on the lowest available timeframe
        # as patterns are often most relevant on recent price action.
        lowest_tf = sorted(self.data.keys())[0]
        latest_data = self._get_data(lowest_tf)
        
        if latest_data.empty:
            return None

        for pattern_name in self.active_patterns:
            detection_func = self.pattern_detection_map.get(pattern_name)
            
            if not detection_func:
                log.warning(f"No detection function mapped for active pattern: '{pattern_name}'")
                continue

            # The detection function needs the full DataFrame
            occurrences = detection_func(latest_data)
            
            if occurrences:
                # Get the most recent occurrence
                timestamp, price = occurrences[-1]
                
                # Check if this is a new event (e.g., on the last candle)
                last_candle_timestamp = latest_data.index[-1]
                
                # We need to convert the timestamp from the pattern library (which might be a numpy.datetime64)
                # to a pandas Timestamp for comparison.
                if pd.Timestamp(timestamp) == last_candle_timestamp:
                    log.info(f"🚀 Audited pattern detected: {pattern_name} for {self.symbol} at price {price}")
                    
                    # This is a simplified signal. A real implementation would
                    # have more sophisticated logic for stop-loss and take-profit.
                    return SignalEvent(
                        symbol=self.symbol,
                        signal_type='BUY',  # Assuming all patterns are bullish for now
                        strategy_id=f"AUDITED_{pattern_name.upper().replace(' ', '_')}",
                        price=price,
                        confidence=0.8, # High confidence as it's audited
                        price_target=price * 1.03, # 3% take profit
                        stop_loss=price * 0.99, # 1% stop loss
                    )
        return None
