"""
BacktestEngine - Trade Simulation and Performance Metrics

Simulates strategy execution on historical data and calculates
comprehensive performance metrics for parameter optimization.

Key Features:
- Realistic trade execution (slippage, fees)
- Walk-forward compatible
- 15+ performance metrics
- Circuit breaker simulation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

log = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single trade record."""
    entry_time: int          # Unix timestamp ms
    entry_price: float
    exit_time: int
    exit_price: float
    side: str                # 'LONG' or 'SHORT'
    size: float              # Position size (quote currency)
    pnl: float               # Profit/Loss (absolute)
    pnl_pct: float           # Profit/Loss (percentage)
    holding_periods: int     # Number of candles held
    exit_reason: str         # 'TP', 'SL', 'MAX_HOLD', 'SIGNAL'


@dataclass
class BacktestResult:
    """Complete backtest results."""
    trades: List[Trade]
    metrics: Dict[str, float]
    equity_curve: pd.DataFrame
    parameters: Dict[str, Any]


class BacktestEngine:
    """
    Backtesting engine for strategy parameter optimization.
    
    Simulates realistic trading:
    - Execution fees (0.1% default)
    - Slippage (0.05% default)
    - Stop-loss and take-profit
    - Maximum holding periods
    
    Example:
        engine = BacktestEngine(
            initial_capital=10000,
            fee_rate=0.001,
            slippage_rate=0.0005
        )
        
        result = engine.run_backtest(
            data=df,
            strategy_instance=LiquiditySweepStrategy(params)
        )
        
        print(f"Sharpe: {result.metrics['sharpe_ratio']:.2f}")
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.001,        # 0.1%
        slippage_rate: float = 0.0005,  # 0.05%
        risk_per_trade: float = 0.02    # 2% of capital per trade
    ):
        """
        Initialize BacktestEngine.
        
        Args:
            initial_capital: Starting capital (quote currency)
            fee_rate: Trading fee (0.001 = 0.1%)
            slippage_rate: Slippage estimate (0.0005 = 0.05%)
            risk_per_trade: Risk per trade as fraction of capital
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.risk_per_trade = risk_per_trade
        
        log.info(
            f"BacktestEngine initialized: "
            f"${initial_capital:.0f} capital, "
            f"{fee_rate*100:.2f}% fees, "
            f"{slippage_rate*100:.3f}% slippage"
        )
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_instance: Any,
        position_size_pct: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> BacktestResult:
        """
        Run backtest simulation.
        
        Args:
            data: OHLCV DataFrame with indicators
                  Required columns: timestamp, open, high, low, close, volume, atr
            strategy_instance: Strategy object with generate_signals() method
            position_size_pct: Position sizing multiplier (1.0 = full risk_per_trade)
            progress_callback: Optional callback(current, total, stage)
                             Called periodically during backtest phases
        
        Returns:
            BacktestResult with trades, metrics, equity curve
        """
        import time
        backtest_start = time.time()
        
        log.info(f"Running backtest: {len(data)} candles")
        
        # Validate data
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'atr']
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Generate signals from strategy
        signal_start = time.time()
        signals = strategy_instance.generate_signals(data, progress_callback=progress_callback)
        signal_time = time.time() - signal_start
        log.info(f"⏱️  Signal generation took {signal_time:.2f}s ({len(data)} candles)")
        
        # Simulate trades
        trade_start = time.time()
        trades = self._simulate_trades(
            data=data,
            signals=signals,
            strategy_params=strategy_instance.params,
            position_size_pct=position_size_pct
        )
        trade_time = time.time() - trade_start
        log.info(f"⏱️  Trade simulation took {trade_time:.2f}s")
        
        # Calculate metrics
        metrics_start = time.time()
        metrics = self._calculate_metrics(trades, data)
        metrics_time = time.time() - metrics_start
        log.info(f"⏱️  Metrics calculation took {metrics_time:.2f}s")
        
        # Generate equity curve
        equity_start = time.time()
        equity_curve = self._generate_equity_curve(trades, data)
        equity_time = time.time() - equity_start
        log.info(f"⏱️  Equity curve generation took {equity_time:.2f}s")
        
        total_time = time.time() - backtest_start
        
        log.info(
            f"✅ Backtest complete: {len(trades)} trades, "
            f"Sharpe {metrics.get('sharpe_ratio', 0):.2f}, "
            f"Total time: {total_time:.2f}s "
            f"(signals: {signal_time/total_time*100:.1f}%, "
            f"trades: {trade_time/total_time*100:.1f}%, "
            f"metrics: {metrics_time/total_time*100:.1f}%, "
            f"equity: {equity_time/total_time*100:.1f}%)"
        )
        
        return BacktestResult(
            trades=trades,
            metrics=metrics,
            equity_curve=equity_curve,
            parameters=strategy_instance.params
        )
    
    def _simulate_trades(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_params: Dict[str, Any],
        position_size_pct: float
    ) -> List[Trade]:
        """
        Simulate trade execution based on signals.
        
        Args:
            data: OHLCV data
            signals: DataFrame with columns: timestamp, signal, stop_loss, take_profit
            strategy_params: Strategy parameters (for max_holding_periods)
            position_size_pct: Position size multiplier
        
        Returns:
            List of executed trades
        """
        trades = []
        current_position = None
        
        # Merge signals with data
        df = data.copy()
        df = df.merge(signals, on='timestamp', how='left')
        df['signal'].fillna('HOLD', inplace=True)
        
        max_holding = strategy_params.get('max_holding_periods', 50)
        
        for idx, row in df.iterrows():
            timestamp = int(row['timestamp'])
            
            # Check if we have an open position
            if current_position is not None:
                holding_periods = idx - current_position['entry_idx']
                
                # Check exit conditions
                exit_price = None
                exit_reason = None
                
                # Different exit logic for LONG vs SHORT positions
                if current_position['side'] == 'LONG':
                    # LONG: Stop-loss below entry, Take-profit above entry
                    
                    # 1. Stop-loss hit (price drops to or below SL)
                    if row['low'] <= current_position['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'SL'
                    
                    # 2. Take-profit hit (price rises to or above TP)
                    elif row['high'] >= current_position['take_profit']:
                        exit_price = current_position['take_profit']
                        exit_reason = 'TP'
                
                else:  # SHORT position
                    # SHORT: Stop-loss above entry, Take-profit below entry
                    
                    # 1. Stop-loss hit (price rises to or above SL)
                    if row['high'] >= current_position['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'SL'
                    
                    # 2. Take-profit hit (price drops to or below TP)
                    elif row['low'] <= current_position['take_profit']:
                        exit_price = current_position['take_profit']
                        exit_reason = 'TP'
                
                # 3. Maximum holding period (applies to both LONG and SHORT)
                if exit_price is None and holding_periods >= max_holding:
                    exit_price = row['close']
                    exit_reason = 'MAX_HOLD'
                
                # 4. Opposite signal (applies to both LONG and SHORT)
                if exit_price is None and row['signal'] in ['BUY', 'SELL']:
                    if (row['signal'] == 'SELL' and current_position['side'] == 'LONG') or \
                       (row['signal'] == 'BUY' and current_position['side'] == 'SHORT'):
                        exit_price = row['close']
                        exit_reason = 'SIGNAL'
                
                # Execute exit
                if exit_price is not None:
                    trade = self._execute_exit(
                        position=current_position,
                        exit_time=timestamp,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        holding_periods=holding_periods
                    )
                    trades.append(trade)
                    current_position = None
            
            # Check for new entry signal
            if current_position is None and row['signal'] in ['BUY', 'SELL']:
                current_position = self._execute_entry(
                    entry_idx=idx,
                    entry_time=timestamp,
                    entry_price=row['close'],
                    side='LONG' if row['signal'] == 'BUY' else 'SHORT',
                    stop_loss=row.get('stop_loss', 0),
                    take_profit=row.get('take_profit', 0),
                    atr=row['atr'],
                    position_size_pct=position_size_pct
                )
        
        # Close any remaining position at end of data
        if current_position is not None:
            last_row = df.iloc[-1]
            holding_periods = len(df) - 1 - current_position['entry_idx']
            trade = self._execute_exit(
                position=current_position,
                exit_time=int(last_row['timestamp']),
                exit_price=last_row['close'],
                exit_reason='END_OF_DATA',
                holding_periods=holding_periods
            )
            trades.append(trade)
        
        return trades
    
    def _execute_entry(
        self,
        entry_idx: int,
        entry_time: int,
        entry_price: float,
        side: str,
        stop_loss: float,
        take_profit: float,
        atr: float,
        position_size_pct: float
    ) -> Dict[str, Any]:
        """
        Execute trade entry.
        
        Calculates position size based on risk and ATR-based stop-loss.
        """
        # Apply slippage to entry
        slippage_mult = 1 + self.slippage_rate if side == 'LONG' else 1 - self.slippage_rate
        entry_price_adj = entry_price * slippage_mult
        
        # Calculate position size based on risk
        # Risk = capital * risk_per_trade * position_size_pct
        risk_amount = self.initial_capital * self.risk_per_trade * position_size_pct
        
        # Position size = risk_amount / stop_loss_distance
        # CRITICAL: Use entry_price (not entry_price_adj) because stop_loss and take_profit
        # are calculated from the signal's entry_price. Using entry_price_adj creates a mismatch
        # where position sizing doesn't match actual SL/TP levels, causing systematic losses.
        sl_distance = abs(entry_price - stop_loss) / entry_price
        if sl_distance == 0:
            sl_distance = 0.02  # Default 2% if not provided
        
        position_size = risk_amount / sl_distance
        
        # Cap position size at initial capital (no leverage)
        position_size = min(position_size, self.initial_capital)
        
        return {
            'entry_idx': entry_idx,
            'entry_time': entry_time,
            'entry_price': entry_price_adj,
            'side': side,
            'size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
    
    def _execute_exit(
        self,
        position: Dict[str, Any],
        exit_time: int,
        exit_price: float,
        exit_reason: str,
        holding_periods: int
    ) -> Trade:
        """
        Execute trade exit and calculate P&L.
        """
        # Apply slippage to exit
        slippage_mult = 1 - self.slippage_rate if position['side'] == 'LONG' else 1 + self.slippage_rate
        exit_price_adj = exit_price * slippage_mult
        
        # Calculate P&L
        if position['side'] == 'LONG':
            pnl_pct = (exit_price_adj - position['entry_price']) / position['entry_price']
        else:  # SHORT
            pnl_pct = (position['entry_price'] - exit_price_adj) / position['entry_price']
        
        # Apply fees (entry + exit)
        pnl_pct -= 2 * self.fee_rate
        
        pnl = position['size'] * pnl_pct
        
        return Trade(
            entry_time=position['entry_time'],
            entry_price=position['entry_price'],
            exit_time=exit_time,
            exit_price=exit_price_adj,
            side=position['side'],
            size=position['size'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_periods=holding_periods,
            exit_reason=exit_reason
        )
    
    def _calculate_metrics(
        self,
        trades: List[Trade],
        data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Returns dict with:
        - net_profit_pct, gross_win_rate, profit_factor
        - sharpe_ratio, sortino_ratio, calmar_ratio
        - max_drawdown_pct, avg_drawdown_pct
        - total_trades, winning_trades, losing_trades
        - avg_win_pct, avg_loss_pct, largest_win_pct, largest_loss_pct
        - avg_holding_periods
        - expectancy
        """
        if not trades:
            return {
                'net_profit_pct': 0,
                'sharpe_ratio': 0,
                'total_trades': 0
            }
        
        # Convert trades to arrays
        pnls = np.array([t.pnl for t in trades])
        pnl_pcts = np.array([t.pnl_pct for t in trades])
        
        # Win/Loss separation
        wins = pnl_pcts[pnl_pcts > 0]
        losses = pnl_pcts[pnl_pcts < 0]
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        gross_win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        net_profit = pnls.sum()
        net_profit_pct = (net_profit / self.initial_capital) * 100
        
        avg_win_pct = (wins.mean() * 100) if len(wins) > 0 else 0
        avg_loss_pct = (losses.mean() * 100) if len(losses) > 0 else 0
        largest_win_pct = (wins.max() * 100) if len(wins) > 0 else 0
        largest_loss_pct = (losses.min() * 100) if len(losses) > 0 else 0
        
        # Profit factor
        gross_profit = wins.sum() if len(wins) > 0 else 0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Expectancy
        expectancy = pnl_pcts.mean() * 100
        
        # Risk-adjusted metrics
        if len(pnl_pcts) > 1:
            returns_std = pnl_pcts.std()
            sharpe_ratio = (pnl_pcts.mean() / returns_std) * np.sqrt(252) if returns_std > 0 else 0
            
            # Sortino (downside deviation)
            downside_returns = pnl_pcts[pnl_pcts < 0]
            downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.001
            sortino_ratio = (pnl_pcts.mean() / downside_std) * np.sqrt(252)
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
        
        # Drawdown metrics
        equity_curve = self._generate_equity_curve(trades, data)
        max_drawdown_pct = self._calculate_max_drawdown(equity_curve)
        avg_drawdown_pct = self._calculate_avg_drawdown(equity_curve)
        
        # Calmar ratio
        calmar_ratio = (net_profit_pct / abs(max_drawdown_pct)) if max_drawdown_pct != 0 else 0
        
        # Holding period
        avg_holding_periods = np.mean([t.holding_periods for t in trades])
        
        return {
            'net_profit_pct': round(net_profit_pct, 2),
            'gross_win_rate': round(gross_win_rate, 4),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'avg_drawdown_pct': round(avg_drawdown_pct, 2),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'avg_win_pct': round(avg_win_pct, 2),
            'avg_loss_pct': round(avg_loss_pct, 2),
            'largest_win_pct': round(largest_win_pct, 2),
            'largest_loss_pct': round(largest_loss_pct, 2),
            'avg_holding_periods': round(avg_holding_periods, 1),
            'expectancy': round(expectancy, 2)
        }
    
    def _generate_equity_curve(
        self,
        trades: List[Trade],
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate equity curve over time.
        
        Returns DataFrame with columns: timestamp, equity
        """
        if not trades:
            return pd.DataFrame({
                'timestamp': data['timestamp'],
                'equity': self.initial_capital
            })
        
        # Create equity tracking
        equity = self.initial_capital
        equity_points = [(data['timestamp'].iloc[0], equity)]
        
        for trade in trades:
            equity += trade.pnl
            equity_points.append((trade.exit_time, equity))
        
        return pd.DataFrame(equity_points, columns=['timestamp', 'equity'])
    
    def _calculate_max_drawdown(self, equity_curve: pd.DataFrame) -> float:
        """
        Calculate maximum drawdown percentage.
        
        Drawdown = (Trough - Peak) / Peak
        """
        if len(equity_curve) < 2:
            return 0.0
        
        equity = equity_curve['equity'].values
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100
        
        return drawdown.min()
    
    def _calculate_avg_drawdown(self, equity_curve: pd.DataFrame) -> float:
        """Calculate average drawdown percentage."""
        if len(equity_curve) < 2:
            return 0.0
        
        equity = equity_curve['equity'].values
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100
        
        # Only negative values
        drawdowns = drawdown[drawdown < 0]
        
        return drawdowns.mean() if len(drawdowns) > 0 else 0.0
