import datetime
import json
import os
import pandas as pd
from core.event_system import EventBus, SignalEvent, OrderEvent, FillEvent
from utils.logger import log
from .data_handler import DataHandler
from shared.db import get_db_conn


class Portfolio:
    """
    Manages the trading account's state for a single wallet, including cash, positions, and equity.
    """
    def __init__(self, wallet_id, initial_cash=100000.0):
        self.wallet_id = wallet_id
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # { 'symbol': quantity }
        self.holdings = {}   # { 'symbol': { 'quantity': float, 'avg_price': float } }
        self.current_equity = initial_cash
        log.info(f"Portfolio for wallet '{self.wallet_id}' initialized with initial cash: {initial_cash:.2f}")

    def update_on_fill(self, fill_event: FillEvent):
        """
        Updates the portfolio based on a fill event from the exchange.
        """
        if fill_event.wallet_id != self.wallet_id:
            return # This fill is not for this portfolio

        if fill_event.direction == 'BUY':
            self.cash -= fill_event.fill_cost
            if fill_event.symbol in self.holdings:
                current_qty = self.holdings[fill_event.symbol]['quantity']
                current_avg_price = self.holdings[fill_event.symbol]['avg_price']
                new_total_qty = current_qty + fill_event.quantity
                new_avg_price = ((current_avg_price * current_qty) + (fill_event.price * fill_event.quantity)) / new_total_qty
                
                self.holdings[fill_event.symbol]['quantity'] = new_total_qty
                self.holdings[fill_event.symbol]['avg_price'] = new_avg_price
            else:
                self.holdings[fill_event.symbol] = {
                    'quantity': fill_event.quantity,
                    'avg_price': fill_event.price
                }
        elif fill_event.direction == 'SELL':
            self.cash += fill_event.fill_cost
            if fill_event.symbol in self.holdings:
                self.holdings[fill_event.symbol]['quantity'] -= fill_event.quantity
                if self.holdings[fill_event.symbol]['quantity'] <= 0:
                    del self.holdings[fill_event.symbol]
        
        log.info(f"Portfolio for wallet '{self.wallet_id}' updated on fill: Cash {self.cash:.2f}, Holdings: {self.holdings}")


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
        log.info(f"SimulatedExchange received order for wallet '{order.wallet_id}': {order.direction} {order.quantity} {order.symbol}")

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
            commission=0.0,
            wallet_id=order.wallet_id
        )
        
        self.event_bus.publish(fill_event)
        log.info(f"SimulatedExchange published FillEvent for wallet '{order.wallet_id}' for {order.symbol} at price {fill_price:.2f}")


class ExecutionCore:
    """
    Handles order generation for multiple wallets, risk management, and portfolio updates.
    """
    def __init__(self, event_bus: EventBus, data_handler: DataHandler, wallets_config_path='config/wallets.json'):
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.wallets = self._load_wallets(wallets_config_path)
        self.portfolios = {w['wallet_id']: Portfolio(wallet_id=w['wallet_id'], initial_cash=w.get('initial_cash', 100000.0)) for w in self.wallets}
        self.db_conn = get_db_conn()

        self.event_bus.subscribe(SignalEvent, self.on_signal)
        self.event_bus.subscribe(FillEvent, self.on_fill)
        log.info(f"ExecutionCore initialized for {len(self.wallets)} wallets.")

    def _load_wallets(self, path):
        """Loads wallet configurations from a JSON file."""
        if not os.path.exists(path):
            log.error(f"Wallets config file not found at '{path}'.")
            return []
        try:
            with open(path, 'r') as f:
                wallets = json.load(f)
            log.info(f"Loaded {len(wallets)} wallets from '{path}'.")
            return wallets
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log.error(f"Error loading or parsing wallets.json: {e}")
            return []

    def on_signal(self, signal: SignalEvent):
        """Handles a signal event by generating orders for all configured wallets."""
        log.info(f"ExecutionCore received signal: {signal.signal_type} {signal.symbol}")

        for wallet_config in self.wallets:
            wallet_id = wallet_config['wallet_id']
            portfolio = self.portfolios.get(wallet_id)

            if not portfolio:
                log.warning(f"No portfolio found for wallet_id: {wallet_id}. Skipping order generation.")
                continue

            # Risk management: calculate order size as a percentage of cash
            trade_allocation = wallet_config.get('trade_allocation', 0.01) # Default to 1%
            
            # Use the price from the signal to calculate quantity
            if signal.price <= 0:
                log.warning(f"Signal price for {signal.symbol} is invalid ({signal.price}). Cannot calculate order size.")
                continue
                
            order_quantity = (portfolio.cash * trade_allocation) / signal.price

            if order_quantity > 0:
                order = OrderEvent(
                    symbol=signal.symbol,
                    order_type='MARKET',
                    quantity=order_quantity,
                    direction=signal.signal_type,
                    wallet_id=wallet_id
                )
                self.event_bus.publish(order)
                log.info(f"Published OrderEvent for wallet '{wallet_id}': {order.direction} {order.quantity:.4f} {order.symbol}")

    def on_fill(self, fill: FillEvent):
        """Handles a fill event by updating the corresponding portfolio and recording the trade."""
        if fill.wallet_id in self.portfolios:
            self.portfolios[fill.wallet_id].update_on_fill(fill)
            self._log_fill_to_db(fill)
        else:
            log.warning(f"Received fill for unknown wallet_id: {fill.wallet_id}")

    def _log_fill_to_db(self, fill: FillEvent):
        """Saves a trade record to the 'trades' table."""
        if self.db_conn is None:
            log.error("Database connection is not available. Cannot log fill.")
            return
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades (timestamp, symbol, exchange, quantity, direction, price, fill_cost, commission, wallet_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        fill.wallet_id,
                    ),
                )
            log.info(f"Successfully logged trade for {fill.symbol} (Wallet: {fill.wallet_id}) to database.")
        except Exception as e:
            log.error(f"Database error while logging fill: {e}", exc_info=True)
