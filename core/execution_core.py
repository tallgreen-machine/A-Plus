import datetime
import pandas as pd
from core.event_system import EventBus, SignalEvent, OrderEvent, FillEvent
from utils.logger import log
from .data_handler import DataHandler
from shared.db import get_db_conn


class Portfolio:
    """
    Manages the trading account's state, including cash, positions, and equity.
    """
    def __init__(self, initial_cash=100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # { 'symbol': quantity }
        self.holdings = {}   # { 'symbol': { 'quantity': float, 'avg_price': float } }
        self.current_equity = initial_cash
        log.info(f"Portfolio initialized with initial cash: {initial_cash:.2f}")

    def update_on_fill(self, fill_event: FillEvent):
        """
        Updates the portfolio based on a fill event from the exchange.
        """
        # This is a simplified update logic. A real implementation would be more complex.
        if fill_event.direction == 'BUY':
            self.cash -= fill_event.fill_cost
            if fill_event.symbol in self.holdings:
                # Update existing position
                current_qty = self.holdings[fill_event.symbol]['quantity']
                current_avg_price = self.holdings[fill_event.symbol]['avg_price']
                new_total_qty = current_qty + fill_event.quantity
                new_avg_price = ((current_avg_price * current_qty) + (fill_event.price * fill_event.quantity)) / new_total_qty
                
                self.holdings[fill_event.symbol]['quantity'] = new_total_qty
                self.holdings[fill_event.symbol]['avg_price'] = new_avg_price
            else:
                # Add new position
                self.holdings[fill_event.symbol] = {
                    'quantity': fill_event.quantity,
                    'avg_price': fill_event.price
                }
        elif fill_event.direction == 'SELL':
            self.cash += fill_event.fill_cost
            # Logic to reduce or close a position
            if fill_event.symbol in self.holdings:
                self.holdings[fill_event.symbol]['quantity'] -= fill_event.quantity
                if self.holdings[fill_event.symbol]['quantity'] <= 0:
                    del self.holdings[fill_event.symbol]
        
        log.info(f"Portfolio updated on fill: Cash {self.cash:.2f}, Holdings: {self.holdings}")


class SimulatedExchange:
    """
    Simulates a live exchange. It receives orders and produces fill events
    without executing trades on a real exchange. For paper trading.
    """
    def __init__(self, event_bus: EventBus, data_handler: DataHandler):
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.event_bus.subscribe(OrderEvent, self.on_order)
        log.info("SimulatedExchange initialized and subscribed to OrderEvent.")

    def on_order(self, order: OrderEvent):
        """
        Handles an order event, simulates its execution, and publishes a fill event.
        """
        log.info(f"SimulatedExchange received order: {order.direction} {order.quantity} {order.symbol}")

        # Get the latest price to simulate the fill
        # For simplicity, we assume the order is filled at the last close price.
        # A more complex simulation could include slippage and commission.
        latest_bars = self.data_handler.get_latest_data(order.symbol, self.data_handler.timeframes[0], n=1)
        if latest_bars.empty:
            log.error(f"Could not get latest price for {order.symbol} to simulate fill. Order ignored.")
            return

        fill_price = latest_bars['close'].iloc[-1]
        fill_cost = fill_price * order.quantity
        
        fill_event = FillEvent(
            timestamp=pd.Timestamp.now(tz='UTC'),
            symbol=order.symbol,
            exchange='SIMULATED',
            quantity=order.quantity,
            direction=order.direction,
            price=fill_price,
            fill_cost=fill_cost,
            commission=0.0 # TODO: Add commission simulation
        )
        
        self.event_bus.publish(fill_event)
        log.info(f"SimulatedExchange published FillEvent for {order.symbol} at price {fill_price:.2f}")


class ExecutionCore:
    """
    Handles order generation, risk management, and portfolio updates.
    """
    def __init__(self, event_bus: EventBus, portfolio: Portfolio, risk_per_trade=0.01):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.risk_per_trade = risk_per_trade
        self.db_conn = get_db_conn()
        
        self.event_bus.subscribe(SignalEvent, self.on_signal)
        # The portfolio is now updated by the ExecutionCore, which also handles DB logging
        self.event_bus.subscribe(FillEvent, self.on_fill)
        log.info("ExecutionCore initialized and subscribed to SignalEvent and FillEvent.")

    def on_fill(self, fill: FillEvent):
        """Handles a fill event, updates the portfolio, and logs the trade to the DB."""
        log.info(f"ExecutionCore received FillEvent: {fill.direction} {fill.quantity} {fill.symbol} @ {fill.price}")
        
        # 1. Update portfolio state
        self.portfolio.update_on_fill(fill)
        
        # 2. Log trade to database
        self._log_fill_to_db(fill)

    def _log_fill_to_db(self, fill: FillEvent):
        """Saves a trade record to the 'trades' table."""
        if self.db_conn is None:
            log.error("Database connection is not available. Cannot log fill.")
            return
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades (timestamp, symbol, exchange, quantity, direction, price, fill_cost, commission)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        fill.timestamp,
                        fill.symbol,
                        fill.exchange,
                        fill.quantity,
                        fill.direction,
                        fill.price,
                        fill.fill_cost,
                        fill.commission,
                    ),
                )
            # The connection from get_db_conn is in autocommit mode, so this is redundant
            # self.db_conn.commit() 
            log.info(f"Successfully logged trade for {fill.symbol} to database.")
        except Exception as e:
            log.error(f"Database error while logging fill: {e}", exc_info=True)
            # self.db_conn.rollback() # Redundant with autocommit

    def on_signal(self, signal: SignalEvent):
        """
        Handles a signal event and generates an order if appropriate.
        """
        log.info(f"ExecutionCore received signal: {signal.strategy_id} for {signal.symbol}")
        
        # 1. Calculate order size based on risk
        order_quantity = self.calculate_order_size(signal)
        if order_quantity <= 0:
            log.warning(f"Order size is zero or negative ({order_quantity}). No order will be placed.")
            return

        # 2. Create OrderEvent
        order = OrderEvent(
            symbol=signal.symbol,
            order_type='MARKET', # Or 'LIMIT'
            direction=signal.signal_type,
            quantity=order_quantity
        )

        # 3. Publish OrderEvent
        self.event_bus.publish(order)
        log.info(f"ExecutionCore published OrderEvent: {order.direction} {order.quantity:.4f} {order.symbol}")


    def calculate_order_size(self, signal: SignalEvent) -> float:
        """
        Calculates the size of the order based on the portfolio's equity and the signal's risk parameters.
        
        :return: The quantity of the asset to buy/sell.
        """
        if signal.stop_loss is None:
            log.warning("No stop loss defined for signal. Cannot calculate risk-based position size.")
            return 0.0

        # Total amount to risk on this trade
        amount_to_risk = self.portfolio.current_equity * self.risk_per_trade
        
        # Price difference between entry and stop-loss
        risk_per_unit = abs(signal.price - signal.stop_loss)
        if risk_per_unit == 0:
            log.warning("Risk per unit is zero (entry price equals stop loss). Cannot calculate position size.")
            return 0.0

        # Number of units to trade
        quantity = amount_to_risk / risk_per_unit
        
        log.debug(f"Position size calculation: AmountToRisk={amount_to_risk:.2f}, RiskPerUnit={risk_per_unit:.4f}, Quantity={quantity:.4f}")
        return quantity
