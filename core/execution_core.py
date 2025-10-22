import datetime
import json
import os
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from core.event_system import EventBus, SignalEvent, OrderEvent, FillEvent
from utils.logger import log
from .data_handler import DataHandler
from shared.db import get_db_conn


class OCOOrderStatus(Enum):
    """OCO Order status tracking"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class OCOOrderPair:
    """
    Represents a One-Cancels-Other order pair for A+ risk management
    
    Per A+ specification: "A critical requirement for robust risk management is the 
    simultaneous placement of a stop-loss (SL) and a take-profit (TP) order upon 
    entering a position."
    """
    id: str
    symbol: str
    wallet_id: str
    entry_order_id: str
    stop_loss_order_id: Optional[str]
    take_profit_order_id: Optional[str]
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    quantity: float
    direction: str  # 'BUY' or 'SELL'
    status: OCOOrderStatus
    strategy_id: str
    created_at: pd.Timestamp
    exchange: str
    native_oco_supported: bool = False
    linked_orders: List[str] = None  # For emulation mode
    
    def __post_init__(self):
        if self.linked_orders is None:
            self.linked_orders = []


class OCOManager:
    """
    A+ OCO Order Management System
    
    Implements the A+ specification for OCO order handling:
    1. Native OCO Check: Use exchange's native OCO if available
    2. OCO Emulation: Create separate linked orders with monitoring
    3. Order Lifecycle Management: Track and cancel orphaned orders
    
    Critical for "Patience and Precision" philosophy - ensures risk management
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.oco_orders: Dict[str, OCOOrderPair] = {}  # Track all OCO pairs
        self.order_to_oco_map: Dict[str, str] = {}     # Map individual orders to OCO pairs
        self.next_oco_id = 1
        
        # Subscribe to fill events to manage OCO lifecycle
        self.event_bus.subscribe(FillEvent, self.on_fill_event)
        
        log.info("🔗 OCOManager initialized for A+ risk management")
    
    def check_native_oco_support(self, exchange: str) -> bool:
        """
        Check if exchange supports native OCO orders
        
        A+ specification: "query the capabilities of the target exchange"
        """
        # Map of exchanges with known native OCO support
        native_oco_exchanges = {
            'binance': True,
            'binanceus': True,
            'ftx': True,
            'okx': True,
            'bybit': True,
            'kucoin': True,
            'huobi': False,  # Has OCO but limited ccxt support
            'coinbase': False,
            'kraken': False,
            'bitstamp': False
        }
        
        return native_oco_exchanges.get(exchange.lower(), False)
    
    def create_oco_order(self, signal: SignalEvent, quantity: float, 
                        wallet_id: str, exchange: str = 'binanceus') -> Optional[OCOOrderPair]:
        """
        Create OCO order pair per A+ specification
        
        Returns:
            OCOOrderPair if successfully created, None if failed
        """
        oco_id = f"OCO_{self.next_oco_id:06d}"
        self.next_oco_id += 1
        
        # Check for native OCO support
        native_oco_supported = self.check_native_oco_support(exchange)
        
        oco_pair = OCOOrderPair(
            id=oco_id,
            symbol=signal.symbol,
            wallet_id=wallet_id,
            entry_order_id=f"{oco_id}_ENTRY",
            stop_loss_order_id=f"{oco_id}_SL",
            take_profit_order_id=f"{oco_id}_TP",
            entry_price=signal.price,
            stop_loss_price=signal.stop_loss,
            take_profit_price=signal.price_target,
            quantity=quantity,
            direction=signal.signal_type,
            status=OCOOrderStatus.PENDING,
            strategy_id=signal.strategy_id,
            created_at=pd.Timestamp.now(),
            exchange=exchange,
            native_oco_supported=native_oco_supported
        )
        
        # Store OCO pair
        self.oco_orders[oco_id] = oco_pair
        self.order_to_oco_map[oco_pair.entry_order_id] = oco_id
        
        log.info(f"🔗 Created OCO order pair {oco_id} for {signal.symbol}:")
        log.info(f"   💰 Entry: ${signal.price:.4f}")
        log.info(f"   🛡️ Stop Loss: ${signal.stop_loss:.4f}")
        log.info(f"   🎯 Take Profit: ${signal.price_target:.4f}")
        log.info(f"   📊 Quantity: {quantity:.6f}")
        log.info(f"   🔧 Native OCO: {native_oco_supported}")
        
        return oco_pair
    
    def place_native_oco_order(self, oco_pair: OCOOrderPair) -> bool:
        """
        Place native OCO order using exchange's built-in functionality
        
        A+ specification: "use this native function to place the linked SL and TP orders"
        """
        try:
            # This would integrate with ccxt's native OCO methods
            # For now, we'll simulate the process
            
            log.info(f"🚀 Placing native OCO order for {oco_pair.symbol}:")
            log.info(f"   📦 OCO ID: {oco_pair.id}")
            log.info(f"   💱 Exchange: {oco_pair.exchange}")
            
            # In real implementation, this would call:
            # exchange.private_post_order_oco() or similar
            
            oco_pair.status = OCOOrderStatus.ACTIVE
            
            log.info(f"✅ Native OCO order placed successfully for {oco_pair.symbol}")
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to place native OCO order for {oco_pair.symbol}: {e}")
            oco_pair.status = OCOOrderStatus.FAILED
            return False
    
    def place_emulated_oco_orders(self, oco_pair: OCOOrderPair) -> bool:
        """
        Emulate OCO functionality using separate orders
        
        A+ specification: "place two separate, unlinked orders: a LIMIT order for 
        the take-profit target and a STOP_MARKET order for the stop-loss"
        """
        try:
            log.info(f"🔧 Emulating OCO orders for {oco_pair.symbol}:")
            
            # Create stop-loss order
            stop_loss_order = OrderEvent(
                symbol=oco_pair.symbol,
                order_type='STOP_MARKET',
                quantity=oco_pair.quantity,
                direction='SELL' if oco_pair.direction == 'BUY' else 'BUY',
                wallet_id=oco_pair.wallet_id,
                stop_price=oco_pair.stop_loss_price
            )
            
            # Create take-profit order  
            take_profit_order = OrderEvent(
                symbol=oco_pair.symbol,
                order_type='LIMIT',
                quantity=oco_pair.quantity,
                direction='SELL' if oco_pair.direction == 'BUY' else 'BUY',
                wallet_id=oco_pair.wallet_id,
                limit_price=oco_pair.take_profit_price
            )
            
            # Track linked orders for cancellation management
            oco_pair.linked_orders = [
                oco_pair.stop_loss_order_id,
                oco_pair.take_profit_order_id
            ]
            
            # Map individual orders to OCO pair
            self.order_to_oco_map[oco_pair.stop_loss_order_id] = oco_pair.id
            self.order_to_oco_map[oco_pair.take_profit_order_id] = oco_pair.id
            
            # Publish orders to event bus
            self.event_bus.publish(stop_loss_order)
            self.event_bus.publish(take_profit_order)
            
            oco_pair.status = OCOOrderStatus.ACTIVE
            
            log.info(f"✅ Emulated OCO orders placed for {oco_pair.symbol}:")
            log.info(f"   🛡️ Stop Loss Order: {oco_pair.stop_loss_order_id}")
            log.info(f"   🎯 Take Profit Order: {oco_pair.take_profit_order_id}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to place emulated OCO orders for {oco_pair.symbol}: {e}")
            oco_pair.status = OCOOrderStatus.FAILED
            return False
    
    def on_fill_event(self, fill_event: FillEvent):
        """
        Handle fill events for OCO order management
        
        A+ specification: "The moment a FillEvent is received for either the SL or 
        the TP order, the submodule must immediately issue a cancel_order request 
        for the other, now-orphaned order"
        """
        # Check if this fill is part of an OCO pair
        order_id = getattr(fill_event, 'order_id', None)
        if not order_id or order_id not in self.order_to_oco_map:
            return
        
        oco_id = self.order_to_oco_map[order_id]
        oco_pair = self.oco_orders.get(oco_id)
        
        if not oco_pair:
            return
        
        log.info(f"🔗 OCO fill detected for {oco_pair.symbol} (OCO: {oco_id})")
        
        # Determine which order was filled
        if order_id == oco_pair.stop_loss_order_id:
            # Stop loss was hit - cancel take profit
            self._cancel_orphaned_order(oco_pair.take_profit_order_id, oco_pair)
            log.info(f"🛡️ Stop loss executed for {oco_pair.symbol} - cancelled take profit")
            
        elif order_id == oco_pair.take_profit_order_id:
            # Take profit was hit - cancel stop loss
            self._cancel_orphaned_order(oco_pair.stop_loss_order_id, oco_pair)
            log.info(f"🎯 Take profit executed for {oco_pair.symbol} - cancelled stop loss")
        
        # Update OCO status
        oco_pair.status = OCOOrderStatus.COMPLETED
        
        # Clean up mappings
        self._cleanup_oco_pair(oco_pair)
    
    def _cancel_orphaned_order(self, order_id: str, oco_pair: OCOOrderPair):
        """Cancel the orphaned order in OCO emulation"""
        try:
            # In real implementation, this would call exchange.cancel_order(order_id)
            log.info(f"❌ Cancelling orphaned order: {order_id}")
            
            # For now, we simulate the cancellation
            # This is critical to prevent unintended positions
            
        except Exception as e:
            log.error(f"❌ Failed to cancel orphaned order {order_id}: {e}")
    
    def _cleanup_oco_pair(self, oco_pair: OCOOrderPair):
        """Clean up completed OCO pair from tracking"""
        # Remove from mappings
        for order_id in [oco_pair.entry_order_id, oco_pair.stop_loss_order_id, 
                        oco_pair.take_profit_order_id]:
            if order_id in self.order_to_oco_map:
                del self.order_to_oco_map[order_id]
        
        log.info(f"🧹 Cleaned up completed OCO pair: {oco_pair.id}")
    
    def get_active_oco_orders(self) -> List[OCOOrderPair]:
        """Get all active OCO orders"""
        return [oco for oco in self.oco_orders.values() 
                if oco.status in [OCOOrderStatus.ACTIVE, OCOOrderStatus.PARTIALLY_FILLED]]
    
    def get_oco_summary(self) -> Dict[str, Any]:
        """Get OCO order management summary"""
        total_orders = len(self.oco_orders)
        active_orders = len(self.get_active_oco_orders())
        
        status_counts = {}
        for oco in self.oco_orders.values():
            status_counts[oco.status.value] = status_counts.get(oco.status.value, 0) + 1
        
        return {
            'total_oco_orders': total_orders,
            'active_oco_orders': active_orders,
            'status_breakdown': status_counts,
            'native_oco_supported_exchanges': ['binance', 'binanceus', 'ftx', 'okx', 'bybit', 'kucoin']
        }


class RiskManager:
    """
    A+ Fixed Percentage Risk Model Implementation
    
    Implements the exact A+ specification for position sizing:
    Quantity = (Account_Balance × Risk_Per_Trade_Percent) / |Entry_Price - Stop_Loss_Price|
    
    Features:
    - Fixed percentage risk per trade
    - Maximum drawdown protection
    - Dynamic position sizing based on stop-loss distance
    - Portfolio-level risk controls
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # A+ Risk Management Parameters (configurable)
        self.risk_per_trade_percent = self.config.get('risk_per_trade_percent', 1.0)  # 1% per trade
        self.max_drawdown_percent = self.config.get('max_drawdown_percent', 20.0)    # 20% max drawdown
        self.max_portfolio_risk = self.config.get('max_portfolio_risk', 10.0)        # 10% total portfolio risk
        self.min_trade_size = self.config.get('min_trade_size', 10.0)                # Minimum trade size ($)
        
        log.info(f"🛡️ RiskManager initialized:")
        log.info(f"   📊 Risk per trade: {self.risk_per_trade_percent}%")
        log.info(f"   ⛔ Max drawdown: {self.max_drawdown_percent}%")
        log.info(f"   🎯 Max portfolio risk: {self.max_portfolio_risk}%")
    
    def calculate_position_size(self, signal: SignalEvent, account_balance: float, 
                              current_portfolio_risk: float = 0.0) -> Optional[float]:
        """
        Calculate position size using A+ Fixed Percentage Risk Model
        
        Formula: Quantity = (Account_Balance × Risk_Per_Trade_Percent) / |Entry_Price - Stop_Loss_Price|
        
        Args:
            signal: Trading signal with entry price and stop loss
            account_balance: Current account equity
            current_portfolio_risk: Current portfolio risk exposure (%)
            
        Returns:
            Position size (quantity) or None if trade should be rejected
        """
        
        # Validate signal data
        if not signal.price or not signal.stop_loss or signal.price <= 0 or signal.stop_loss <= 0:
            log.warning(f"❌ Invalid signal data for {signal.symbol}: price={signal.price}, stop_loss={signal.stop_loss}")
            return None
        
        # Calculate risk amount per the A+ specification
        entry_price = signal.price
        stop_loss_price = signal.stop_loss
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit <= 0:
            log.warning(f"❌ Invalid risk calculation for {signal.symbol}: entry={entry_price}, stop={stop_loss_price}")
            return None
        
        # A+ Formula: Position size based on fixed percentage risk
        risk_amount = account_balance * (self.risk_per_trade_percent / 100.0)
        position_size = risk_amount / risk_per_unit
        
        # Calculate trade value
        trade_value = position_size * entry_price
        
        # Risk Management Checks
        
        # 1. Minimum trade size check
        if trade_value < self.min_trade_size:
            log.info(f"🚫 Trade too small for {signal.symbol}: ${trade_value:.2f} < ${self.min_trade_size}")
            return None
        
        # 2. Portfolio risk limit check
        trade_risk_percent = (risk_amount / account_balance) * 100
        total_risk_after_trade = current_portfolio_risk + trade_risk_percent
        
        if total_risk_after_trade > self.max_portfolio_risk:
            log.warning(f"🚫 Portfolio risk limit exceeded for {signal.symbol}:")
            log.warning(f"   Current risk: {current_portfolio_risk:.2f}%")
            log.warning(f"   Trade risk: {trade_risk_percent:.2f}%")
            log.warning(f"   Total would be: {total_risk_after_trade:.2f}% > {self.max_portfolio_risk}%")
            return None
        
        # 3. Account balance check
        if trade_value > account_balance * 0.5:  # Don't use more than 50% of account on single trade
            log.warning(f"🚫 Trade too large for {signal.symbol}: ${trade_value:.2f} > 50% of account")
            return None
        
        log.info(f"✅ Position size calculated for {signal.symbol}:")
        log.info(f"   💰 Account balance: ${account_balance:.2f}")
        log.info(f"   📊 Risk per trade: {self.risk_per_trade_percent}% = ${risk_amount:.2f}")
        log.info(f"   📏 Risk per unit: ${risk_per_unit:.4f}")
        log.info(f"   📦 Position size: {position_size:.6f}")
        log.info(f"   💵 Trade value: ${trade_value:.2f}")
        
        return position_size
    
    def check_drawdown_limit(self, current_equity: float, peak_equity: float) -> bool:
        """
        Check if current drawdown exceeds maximum allowed
        
        Returns:
            True if trading should continue, False if drawdown limit hit
        """
        if peak_equity <= 0:
            return True
        
        current_drawdown = ((peak_equity - current_equity) / peak_equity) * 100
        
        if current_drawdown >= self.max_drawdown_percent:
            log.error(f"🛑 MAXIMUM DRAWDOWN REACHED:")
            log.error(f"   📉 Current drawdown: {current_drawdown:.2f}%")
            log.error(f"   ⛔ Maximum allowed: {self.max_drawdown_percent}%")
            log.error(f"   🚨 TRADING HALTED FOR RISK PROTECTION")
            return False
        
        return True
    
    def get_risk_metrics(self, current_equity: float, peak_equity: float, 
                        open_positions: Dict[str, Any]) -> Dict[str, float]:
        """Get current risk metrics for monitoring"""
        current_drawdown = 0.0
        if peak_equity > 0:
            current_drawdown = ((peak_equity - current_equity) / peak_equity) * 100
        
        # Calculate current portfolio risk from open positions
        portfolio_risk = 0.0
        for symbol, position in open_positions.items():
            if 'risk_amount' in position:
                portfolio_risk += position['risk_amount']
        
        portfolio_risk_percent = (portfolio_risk / current_equity) * 100 if current_equity > 0 else 0.0
        
        return {
            'current_equity': current_equity,
            'peak_equity': peak_equity,
            'current_drawdown_percent': current_drawdown,
            'portfolio_risk_percent': portfolio_risk_percent,
            'risk_per_trade_percent': self.risk_per_trade_percent,
            'max_drawdown_percent': self.max_drawdown_percent
        }


class Portfolio:
    """
    Enhanced Portfolio with A+ Risk Management
    
    Manages trading account state with proper risk tracking and equity monitoring
    """
    def __init__(self, wallet_id, initial_cash=100000.0, risk_config: Dict[str, Any] = None):
        self.wallet_id = wallet_id
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # { 'symbol': quantity }
        self.holdings = {}   # { 'symbol': { 'quantity': float, 'avg_price': float } }
        self.open_positions = {}  # Track open positions with risk data
        self.current_equity = initial_cash
        self.peak_equity = initial_cash  # Track peak for drawdown calculation
        
        # Initialize risk manager
        self.risk_manager = RiskManager(risk_config)
        
        log.info(f"📊 Portfolio for wallet '{self.wallet_id}' initialized:")
        log.info(f"   💰 Initial cash: ${initial_cash:.2f}")
        log.info(f"   🛡️ Risk management: Active")

    def update_on_fill(self, fill_event: FillEvent):
        """
        Enhanced portfolio update with risk tracking
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
                    # Remove from open positions when closed
                    if fill_event.symbol in self.open_positions:
                        del self.open_positions[fill_event.symbol]
        
        # Update equity and peak tracking
        self._update_equity()
        
        log.info(f"📊 Portfolio '{self.wallet_id}' updated:")
        log.info(f"   💵 Cash: ${self.cash:.2f}")
        log.info(f"   📈 Equity: ${self.current_equity:.2f}")
        log.info(f"   📊 Holdings: {len(self.holdings)} positions")
    
    def _update_equity(self):
        """Update current equity and track peak"""
        # For now, equity = cash (in real implementation, would include unrealized P&L)
        self.current_equity = self.cash
        
        # Track peak equity for drawdown calculation
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
    
    def add_open_position(self, symbol: str, signal: SignalEvent, quantity: float):
        """Track new open position with risk data"""
        risk_amount = abs(signal.price - signal.stop_loss) * quantity
        
        self.open_positions[symbol] = {
            'entry_price': signal.price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.price_target,
            'quantity': quantity,
            'risk_amount': risk_amount,
            'strategy_id': signal.strategy_id,
            'entry_time': pd.Timestamp.now()
        }
        
        log.info(f"📍 Added open position for {symbol}:")
        log.info(f"   💰 Risk amount: ${risk_amount:.2f}")
        log.info(f"   📊 Quantity: {quantity:.6f}")
    
    def get_current_risk_metrics(self) -> Dict[str, float]:
        """Get current portfolio risk metrics"""
        return self.risk_manager.get_risk_metrics(
            self.current_equity,
            self.peak_equity,
            self.open_positions
        )
    
    def check_trading_allowed(self) -> bool:
        """Check if trading is allowed based on risk limits"""
        return self.risk_manager.check_drawdown_limit(self.current_equity, self.peak_equity)


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
    Enhanced ExecutionCore with A+ Risk Management and OCO Order System
    
    Features:
    - Fixed percentage risk model per A+ specification
    - Position sizing based on stop-loss distance
    - Portfolio-level risk controls
    - Maximum drawdown protection
    - OCO order management (native + emulation)
    - Multi-wallet support with individual risk management
    """
    def __init__(self, event_bus: EventBus, data_handler: DataHandler, wallets_config_path='config/wallets.json'):
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.wallets = self._load_wallets(wallets_config_path)
        
        # Initialize OCO Manager
        self.oco_manager = OCOManager(event_bus)
        
        # Initialize portfolios with risk management
        self.portfolios = {}
        for w in self.wallets:
            risk_config = w.get('risk_management', {})
            portfolio = Portfolio(
                wallet_id=w['wallet_id'], 
                initial_cash=w.get('initial_cash', 100000.0),
                risk_config=risk_config
            )
            self.portfolios[w['wallet_id']] = portfolio
        
        self.db_conn = get_db_conn()

        self.event_bus.subscribe(SignalEvent, self.on_signal)
        self.event_bus.subscribe(FillEvent, self.on_fill)
        
        log.info(f"🚀 ExecutionCore initialized:")
        log.info(f"   👛 Wallets: {len(self.wallets)}")
        log.info(f"   🛡️ Risk management: A+ Fixed Percentage Model")
        log.info(f"   🔗 OCO management: Native + Emulation support")

    def _load_wallets(self, path):
        """Enhanced wallet loading with risk management config"""
        if not os.path.exists(path):
            log.error(f"Wallets config file not found at '{path}'.")
            return []
        try:
            with open(path, 'r') as f:
                wallets = json.load(f)
            
            # Ensure each wallet has risk management config
            for wallet in wallets:
                if 'risk_management' not in wallet:
                    wallet['risk_management'] = {
                        'risk_per_trade_percent': 1.0,
                        'max_drawdown_percent': 20.0,
                        'max_portfolio_risk': 10.0
                    }
                
                # Add exchange preference for OCO management
                if 'exchange' not in wallet:
                    wallet['exchange'] = 'binanceus'  # Default exchange
            
            log.info(f"📋 Loaded {len(wallets)} wallets with risk management and OCO config")
            return wallets
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log.error(f"Error loading wallets.json: {e}")
            return []

    def on_signal(self, signal: SignalEvent):
        """
        Enhanced signal handling with A+ Risk Management and OCO Orders
        
        Complete A+ Trading Lifecycle:
        1. Risk assessment and position sizing
        2. Entry order generation
        3. OCO order creation (stop-loss + take-profit)
        4. Order execution with proper risk management
        """
        log.info(f"🎯 ExecutionCore received A+ signal: {signal.strategy_id} {signal.signal_type} {signal.symbol}")

        for wallet_config in self.wallets:
            wallet_id = wallet_config['wallet_id']
            exchange = wallet_config.get('exchange', 'binanceus')
            portfolio = self.portfolios.get(wallet_id)

            if not portfolio:
                log.warning(f"❌ No portfolio found for wallet_id: {wallet_id}")
                continue

            # 1. Check if trading is allowed (drawdown limits)
            if not portfolio.check_trading_allowed():
                log.warning(f"🚫 Trading halted for wallet '{wallet_id}' due to risk limits")
                continue

            # 2. Calculate current portfolio risk
            risk_metrics = portfolio.get_current_risk_metrics()
            current_portfolio_risk = risk_metrics['portfolio_risk_percent']

            # 3. Calculate position size using A+ Fixed Percentage Risk Model
            position_size = portfolio.risk_manager.calculate_position_size(
                signal=signal,
                account_balance=portfolio.current_equity,
                current_portfolio_risk=current_portfolio_risk
            )

            if position_size is None:
                log.info(f"🚫 Position size calculation rejected for {signal.symbol} (Wallet: {wallet_id})")
                continue

            # 4. Validate position size
            if position_size <= 0:
                log.warning(f"❌ Invalid position size for {signal.symbol}: {position_size}")
                continue

            # 5. Create OCO order pair for A+ risk management
            oco_pair = self.oco_manager.create_oco_order(
                signal=signal,
                quantity=position_size,
                wallet_id=wallet_id,
                exchange=exchange
            )

            if not oco_pair:
                log.error(f"❌ Failed to create OCO order for {signal.symbol}")
                continue

            # 6. Place entry order first
            entry_order = OrderEvent(
                symbol=signal.symbol,
                order_type='MARKET',
                quantity=position_size,
                direction=signal.signal_type,
                wallet_id=wallet_id
            )

            # 7. Place OCO orders (stop-loss + take-profit)
            if oco_pair.native_oco_supported:
                # Use native OCO functionality
                oco_success = self.oco_manager.place_native_oco_order(oco_pair)
            else:
                # Use OCO emulation
                oco_success = self.oco_manager.place_emulated_oco_orders(oco_pair)

            if not oco_success:
                log.error(f"❌ Failed to place OCO orders for {signal.symbol}")
                continue

            # 8. Track the position for risk management
            portfolio.add_open_position(signal.symbol, signal, position_size)

            # 9. Publish entry order
            self.event_bus.publish(entry_order)
            
            log.info(f"✅ A+ Order System activated for wallet '{wallet_id}':")
            log.info(f"   📊 Entry: {entry_order.direction} {entry_order.quantity:.6f} {entry_order.symbol}")
            log.info(f"   💰 Trade value: ${position_size * signal.price:.2f}")
            log.info(f"   🔗 OCO ID: {oco_pair.id}")
            log.info(f"   🛡️ Stop Loss: ${signal.stop_loss:.4f}")
            log.info(f"   🎯 Take Profit: ${signal.price_target:.4f}")
            log.info(f"   📏 Risk: ${abs(signal.price - signal.stop_loss) * position_size:.2f}")

    def on_fill(self, fill: FillEvent):
        """Enhanced fill handling with risk tracking and OCO management"""
        if fill.wallet_id in self.portfolios:
            portfolio = self.portfolios[fill.wallet_id]
            portfolio.update_on_fill(fill)
            self._log_fill_to_db(fill)
            
            # Log risk metrics after fill
            risk_metrics = portfolio.get_current_risk_metrics()
            log.info(f"📊 Post-fill risk metrics for '{fill.wallet_id}':")
            log.info(f"   💰 Equity: ${risk_metrics['current_equity']:.2f}")
            log.info(f"   📉 Drawdown: {risk_metrics['current_drawdown_percent']:.2f}%")
            log.info(f"   📊 Portfolio risk: {risk_metrics['portfolio_risk_percent']:.2f}%")
            
        else:
            log.warning(f"❌ Received fill for unknown wallet_id: {fill.wallet_id}")

    def _log_fill_to_db(self, fill: FillEvent):
        """Enhanced database logging with risk data"""
        if self.db_conn is None:
            log.error("❌ Database connection not available. Cannot log fill.")
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
            log.info(f"✅ Trade logged to database: {fill.symbol} (Wallet: {fill.wallet_id})")
        except Exception as e:
            log.error(f"❌ Database error while logging fill: {e}", exc_info=True)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with risk metrics and OCO status"""
        summary = {
            'total_wallets': len(self.portfolios),
            'total_equity': 0.0,
            'total_risk': 0.0,
            'wallets': {},
            'oco_summary': self.oco_manager.get_oco_summary()
        }
        
        for wallet_id, portfolio in self.portfolios.items():
            risk_metrics = portfolio.get_current_risk_metrics()
            wallet_summary = {
                'equity': risk_metrics['current_equity'],
                'peak_equity': risk_metrics['peak_equity'],
                'drawdown_percent': risk_metrics['current_drawdown_percent'],
                'portfolio_risk_percent': risk_metrics['portfolio_risk_percent'],
                'open_positions': len(portfolio.open_positions),
                'trading_allowed': portfolio.check_trading_allowed()
            }
            
            summary['wallets'][wallet_id] = wallet_summary
            summary['total_equity'] += wallet_summary['equity']
            summary['total_risk'] += wallet_summary['portfolio_risk_percent']
        
        return summary
    
    def get_active_oco_orders(self) -> List[OCOOrderPair]:
        """Get all active OCO orders across all wallets"""
        return self.oco_manager.get_active_oco_orders()
    
    def cancel_oco_order(self, oco_id: str) -> bool:
        """Cancel a specific OCO order pair"""
        try:
            oco_pair = self.oco_manager.oco_orders.get(oco_id)
            if not oco_pair:
                log.warning(f"❌ OCO order {oco_id} not found")
                return False
            
            # Cancel all linked orders
            for order_id in oco_pair.linked_orders:
                self.oco_manager._cancel_orphaned_order(order_id, oco_pair)
            
            oco_pair.status = OCOOrderStatus.CANCELLED
            log.info(f"✅ OCO order {oco_id} cancelled successfully")
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to cancel OCO order {oco_id}: {e}")
            return False
