from abc import ABC, abstractmethod
import pandas as pd
from utils.logger import log

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    def __init__(self, symbol: str, data: dict):
        """
        Initializes the strategy.
        
        :param symbol: The symbol to be traded.
        :param data: A dictionary containing historical data for different timeframes.
                     e.g., {'1h': df_1h, '4h': df_4h, '1d': df_1d}
        """
        self.symbol = symbol
        self.data = data

    @abstractmethod
    def check_signal(self):
        """
        The core logic of the strategy. This method must be implemented by subclasses.
        
        It should analyze the data and return a SignalEvent if a trading opportunity
        is identified, otherwise return None.
        """
        pass

    def _get_data(self, timeframe: str) -> pd.DataFrame:
        """
        Helper method to safely retrieve data for a specific timeframe.
        """
        df = self.data.get(timeframe)
        if df is None or df.empty:
            log.warning(f"Data for timeframe '{timeframe}' not available for {self.symbol}.")
            return pd.DataFrame()
        return df
