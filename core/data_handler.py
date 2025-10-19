# core/data_handler.py

import ccxt
import pandas as pd
import time
from typing import Dict, List

from core.event_system import EventBus, MarketEvent
from utils.logger import log

class DataHandler:
    """
    Handles all interactions with the exchange to fetch and manage market data.
    Its sole responsibilities are to:
    1. Connect to the exchange.
    2. Fetch OHLCV data for required symbols and timeframes.
    3. Manage an in-memory history of the data.
    4. Publish a MarketEvent to the EventBus upon the close of a new candle.
    """
    def __init__(self, event_bus: EventBus, symbols: List[str], timeframes: List[str], exchange_id: str = 'binance', backtest_mode: bool = False):
        self.event_bus = event_bus
        self.symbols = symbols
        self.timeframes = timeframes
        self.exchange_id = exchange_id
        self.backtest_mode = backtest_mode
        
        self._exchange = self._init_exchange() if not backtest_mode else None
        self._data: Dict[str, pd.DataFrame] = {} # Key: f"{symbol}_{timeframe}"
        self._last_timestamps: Dict[str, int] = {} # Key: f"{symbol}_{timeframe}"

        if not self.backtest_mode:
            self._backfill_history()
        else:
            log.info("DataHandler running in backtest mode. Data will be provided by the backtesting engine.")

    def _init_exchange(self):
        """Initializes the ccxt exchange instance."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            exchange = exchange_class({
                'rateLimit': True,  # Enable built-in rate limiting
            })
            log.info(f"Successfully connected to {self.exchange_id}.")
            return exchange
        except (AttributeError, ccxt.ExchangeError) as e:
            log.error(f"Error initializing exchange {self.exchange_id}: {e}", exc_info=True)
            raise

    def _backfill_history(self):
        """
        Backfills historical data for each symbol and timeframe on startup.
        Follows the logic from section 2.3.3 of the spec.
        """
        log.info("Backfilling historical data...")
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                key = f"{symbol}_{timeframe}"
                log.info(f"  Fetching {key}...")
                try:
                    # Fetch a reasonable amount of history, e.g., 500 candles
                    # In a real system, this would be more robust, handling pagination.
                    ohlcv = self._exchange.fetch_ohlcv(symbol, timeframe, limit=500)
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    self._data[key] = df
                    self._last_timestamps[key] = df.index[-1].value // 10**9 # Store as seconds
                    log.info(f"    -> Fetched {len(df)} candles for {key}. Latest: {df.index[-1]}")
                    time.sleep(self._exchange.rateLimit / 1000) # Respect rate limit
                except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                    log.warning(f"    -> Could not fetch data for {key}: {e}")
        log.info("Historical data backfill complete.")

    def update_data(self):
        """
        Called on each system heartbeat. Fetches the latest candle and publishes
        a MarketEvent if it's new.
        """
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                key = f"{symbol}_{timeframe}"
                try:
                    # Fetch the most recent 2 candles to be safe
                    ohlcv = self._exchange.fetch_ohlcv(symbol, timeframe, limit=2)
                    latest_candle = ohlcv[-1]
                    latest_timestamp = latest_candle[0] // 1000 # Convert ms to seconds
                    
                    last_known_timestamp = self._last_timestamps.get(key, 0)

                    if latest_timestamp > last_known_timestamp:
                        # A new candle has closed
                        log.info(f"New candle detected for {key} at timestamp {latest_timestamp}")
                        
                        # Update DataFrame
                        new_row = pd.DataFrame([latest_candle], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        new_row['timestamp'] = pd.to_datetime(new_row['timestamp'], unit='ms')
                        new_row.set_index('timestamp', inplace=True)
                        
                        # Use concat instead of append
                        self._data[key] = pd.concat([self._data[key], new_row])
                        self._last_timestamps[key] = latest_timestamp

                        # Publish MarketEvent
                        market_event = MarketEvent(
                            symbol=symbol,
                            timeframe=timeframe,
                            data=self._data[key] # Publish the full available history
                        )
                        self.event_bus.publish(market_event)
                except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                    log.warning(f"    -> Could not fetch data for {key}: {e}")

    def on_market_event(self, event: MarketEvent):
        """
        Special method for backtesting. The backtester pushes data to the handler.
        """
        if not self.backtest_mode:
            return
            
        key = f"{event.symbol}_{event.timeframe}"
        
        if key not in self._data or self._data[key].empty:
            self._data[key] = event.data
        else:
            self._data[key] = pd.concat([self._data[key], event.data])

        # Now that data is updated, we can publish it for the SignalLibrary
        # This creates a two-step process in backtesting:
        # 1. Backtrader -> DataHandler (this method)
        # 2. DataHandler -> SignalLibrary (the publish call below)
        
        market_event = MarketEvent(
            symbol=event.symbol,
            timeframe=event.timeframe,
            data=self._data[key] # Publish the full available history
        )
        self.event_bus.publish(market_event)

    def get_latest_data(self, symbol: str, timeframe: str, n: int = 1) -> pd.DataFrame:
        """
        Returns the N most recent bars for a given symbol and timeframe.
        """
        key = f"{symbol}_{timeframe}"
        return self._data.get(key, pd.DataFrame()).tail(n)

    def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Returns the full historical DataFrame for a given symbol and timeframe.
        """
        key = f"{symbol}_{timeframe}"
        return self._data.get(key, pd.DataFrame())
