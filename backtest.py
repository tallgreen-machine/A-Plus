import matplotlib
matplotlib.use('Agg')

import backtrader as bt
import pandas as pd
from core.event_system import EventBus, MarketEvent, OrderEvent, FillEvent
from core.data_handler import DataHandler
from core.signal_library import SignalLibrary
from core.execution_core import ExecutionCore, Portfolio
from utils.timeframe_utils import TIMEFRAME_MAP, REVERSE_TIMEFRAME_MAP

class PandasData(bt.feeds.PandasData):
    """
    A custom data feed for backtrader that includes the timeframe.
    """
    params = (
        ('timeframe', None),
    )

class SimulatedExchange:
    """
    Simulates the exchange's order matching.
    
    In a real system, this would be a connection to a live exchange API.
    For backtesting, it receives OrderEvents and generates FillEvents.
    """
    def __init__(self, event_bus: EventBus, data_feed: pd.DataFrame):
        self.event_bus = event_bus
        self.data_feed = data_feed
        self.event_bus.subscribe(OrderEvent, self.execute_order)

    def execute_order(self, order: OrderEvent):
        """
        'Fills' an order at the current market price.
        """
        current_price = self.data_feed['close'].iloc[-1] # Use the close of the current bar
        
        fill = FillEvent(
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=current_price,
            fill_cost=current_price * order.quantity,
            commission=0.0 # Simplified
        )
        self.event_bus.publish(fill)
        print(f"[{pd.Timestamp.now()}] SimulatedExchange filled order: {fill.direction} {fill.quantity} {fill.symbol} @ {fill.price}")


class TradingSystem(bt.Strategy):
    """
    The main backtrader strategy that integrates the event-driven system.
    """
    def __init__(self):
        # 1. Initialize the event-driven components
        self.event_bus = EventBus()
        self.symbols = [self.datas[0].p.name]
        self.timeframes = [self.datas[0].p.timeframe]
        self.portfolio = Portfolio(initial_cash=100000.0)
        
        # The DataHandler in a backtest context is driven by the backtrader engine
        # instead of fetching live data.
        self.data_handler = DataHandler(self.event_bus, self.symbols, self.timeframes, backtest_mode=True)
        
        self.signal_library = SignalLibrary(self.event_bus, self.symbols)
        self.execution_core = ExecutionCore(self.event_bus, self.portfolio)
        
        # The SimulatedExchange connects the ExecutionCore to the backtest's data
        self.simulated_exchange = SimulatedExchange(self.event_bus, self.datas[0])

    def next(self):
        """
        This method is called for each bar of data. It's the main loop of the backtest.
        """
        # Create a DataFrame for the current data point
        current_data = {
            'open': self.datas[0].open[0],
            'high': self.datas[0].high[0],
            'low': self.datas[0].low[0],
            'close': self.datas[0].close[0],
            'volume': self.datas[0].volume[0]
        }
        index = [self.datas[0].datetime.datetime(0)]
        df = pd.DataFrame(current_data, index=index)

        # Create and publish a MarketEvent for the current bar
        tf_str = REVERSE_TIMEFRAME_MAP.get((self.datas[0].p.timeframe, self.datas[0].p.compression))
        market_event = MarketEvent(
            symbol=self.datas[0].p.name,
            timeframe=tf_str,
            data=df
        )
        self.data_handler.on_market_event(market_event)

    def stop(self):
        """
        Called at the end of the backtest.
        """
        print("Backtest finished.")
        print(f"Final Portfolio Value: {self.portfolio.cash + self.portfolio.current_equity - self.portfolio.initial_cash:.2f}")


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # --- Data Loading ---
    # In a real scenario, you would load data from a file or database.
    # Here we create some sample data.
    # NOTE: This sample data is not sufficient to trigger the implemented strategies.
    # You would need to load a proper historical dataset.
    
    n_candles = 100
    dates = pd.to_datetime('2023-01-01') + pd.to_timedelta(range(n_candles), 'h') # Hourly data
    
    # Create a pattern that might trigger the VolumeBreakout strategy
    close_prices = [100 + i * 0.1 for i in range(50)] # Uptrend
    close_prices += [105] * 10 # Consolidation
    close_prices += [106, 107, 108, 109, 110] # Breakout
    close_prices += [110 - i * 0.2 for i in range(35)] # Downtrend
    
    volume = [1000] * 60
    volume += [3000, 4000, 5000] # Volume spike
    volume += [1200] * (n_candles - 63)

    data = pd.DataFrame({
        'open': [p - 0.5 for p in close_prices],
        'high': [p + 1 for p in close_prices],
        'low': [p - 1 for p in close_prices],
        'close': close_prices,
        'volume': volume
    }, index=dates)
    data['openinterest'] = 0 # Required by backtrader

    # --- Cerebro Setup ---
    tf, compression = TIMEFRAME_MAP['1h']
    data_feed = PandasData(dataname=data, timeframe=tf, compression=compression, name='BTC/USDT')
    cerebro.adddata(data_feed)
    
    cerebro.addstrategy(TradingSystem)
    cerebro.broker.setcash(100000.0)
    
    print("Starting Portfolio Value: 100000.00")
    cerebro.run()
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
    
    fig = cerebro.plot(style='candlestick', iplot=False)
    fig[0][0].savefig('backtest_plot.png')
