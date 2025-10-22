#!/usr/bin/env python3
"""
Database Seeding Script for Trad Trading System
Seeds the database with initial trading data, portfolio, and test strategies.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
from decimal import Decimal

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.db import get_db_conn

def seed_portfolio_data(conn):
    """Create initial portfolio data for admin user"""
    print("💰 Seeding portfolio data...")
    
    cur = conn.cursor()
    
    # Create portfolio snapshot with $100k equity
    cur.execute("""
        INSERT INTO portfolio_snapshots (user_id, total_equity, cash_balance, unrealized_pnl, position_count, market_value, total_pnl)
        VALUES (1, 100000.00, 75000.00, 2500.00, 5, 25000.00, 2500.00);
    """)
    
    # Create some holdings
    holdings_data = [
        ('BTC/USDT', 0.5, 48000.00, 50000.00),
        ('ETH/USDT', 5.0, 3000.00, 3200.00),  
        ('SOL/USDT', 50.0, 100.00, 120.00),
        ('ADA/USDT', 10000.0, 0.45, 0.52),
        ('DOT/USDT', 100.0, 35.00, 42.00)
    ]
    
    for symbol, quantity, avg_cost, current_price in holdings_data:
        market_value = quantity * current_price
        unrealized_pnl = (current_price - avg_cost) * quantity
        unrealized_pnl_percent = (unrealized_pnl / (avg_cost * quantity)) * 100
        
        cur.execute("""
            INSERT INTO holdings (user_id, symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent)
            VALUES (1, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, symbol) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                avg_cost = EXCLUDED.avg_cost,
                current_price = EXCLUDED.current_price,
                market_value = EXCLUDED.market_value,
                unrealized_pnl = EXCLUDED.unrealized_pnl,
                unrealized_pnl_percent = EXCLUDED.unrealized_pnl_percent;
        """, (symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent))
    
    conn.commit()
    print("✅ Portfolio data seeded")

def seed_trading_history(conn):
    """Create sample trading history"""
    print("📈 Seeding trading history...")
    
    cur = conn.cursor()
    
    # Generate 30 days of sample trades
    base_time = datetime.now() - timedelta(days=30)
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
    
    for i in range(25):  # 25 sample trades
        trade_time = base_time + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        symbol = random.choice(symbols)
        side = random.choice(['BUY', 'SELL'])
        quantity = random.uniform(0.01, 2.0)
        price = random.uniform(30000, 70000) if symbol == 'BTC/USDT' else random.uniform(100, 5000)
        fill_cost = quantity * price
        
        # Generate realistic P&L (70% win rate)
        if random.random() < 0.7:  # Win
            pnl = random.uniform(50, 500)
        else:  # Loss
            pnl = -random.uniform(20, 200)
            
        pnl_percent = (pnl / fill_cost) * 100
        
        cur.execute("""
            INSERT INTO trades (user_id, wallet_id, symbol, trade_type, entry_price, exit_price, pnl_percentage, entry_time, exit_time, strategy_name)
            VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (f'wallet_{i}', symbol, side, price, price * (1 + pnl_percent/100), pnl_percent, trade_time, trade_time + timedelta(hours=random.randint(1, 24)), 'Test Pattern'))
    
    conn.commit()
    print("✅ Trading history seeded")

def seed_patterns_and_performance(conn):
    """Create sample pattern data"""
    print("🎯 Seeding pattern data...")
    
    cur = conn.cursor()
    
    # Create strategies
    patterns_data = [
        ('Liquidity Sweep', 'Detects liquidity sweeps above/below key levels', 'Tier1', True),
        ('Volume Breakout', 'High volume breakouts from consolidation', 'Tier1', True),
        ('Funding Rate Extreme', 'Extreme funding rates indicating sentiment', 'Tier1', False),
        ('HTF Sweep', 'Higher timeframe liquidity sweeps', 'Tier2', True),
        ('Divergence Capitulation', 'Price-RSI divergence with high volume', 'Tier1', True)
    ]
    
    for name, description, category, is_active in patterns_data:
        cur.execute("""
            INSERT INTO strategies (name, description, category, is_active, created_by, min_confidence, max_risk_per_trade)
            VALUES (%s, %s, %s, %s, 1, 0.7, 0.02)
            ON CONFLICT (name) DO UPDATE SET 
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                is_active = EXCLUDED.is_active;
        """, (name, description, category, is_active))
    
    # Add pattern performance data
    cur.execute("SELECT id, name FROM strategies;")
    strategies = cur.fetchall()
    
    for strategy_id, strategy_name in strategies:
        # Random but realistic performance metrics
        total_pl = random.uniform(-500, 2000)
        win_rate = random.uniform(0.6, 0.85)
        total_trades = random.randint(10, 50)
        avg_win = random.uniform(100, 300)
        avg_loss = random.uniform(-50, -150)
        
        # Win/loss ratio
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 2.0
        
        cur.execute("""
            INSERT INTO strategy_performance (user_id, strategy_id, symbol, timeframe, total_pnl, win_rate, total_trades, winning_trades, losing_trades, avg_win, avg_loss, profit_factor)
            VALUES (1, %s, 'BTC/USDT', '1h', %s, %s, %s, %s, %s, %s, %s, %s);
        """, (strategy_id, total_pl, win_rate, total_trades, int(total_trades * win_rate), int(total_trades * (1-win_rate)), avg_win, avg_loss, win_loss_ratio))
    
    conn.commit()
    print("✅ Strategy data seeded")

def seed_equity_history(conn):
    """Create equity curve history"""
    print("📊 Seeding equity history...")
    
    cur = conn.cursor()
    
    # Generate 30 days of equity history
    base_equity = 97500.0  # Starting equity
    current_equity = base_equity
    
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        
        # Random daily movement (-2% to +3%)
        daily_change = random.uniform(-0.02, 0.03)
        current_equity = current_equity * (1 + daily_change)
        
        daily_return = daily_change
        
        cur.execute("""
            INSERT INTO equity_history (user_id, timestamp, equity, cash, market_value, total_pnl, daily_return)
            VALUES (1, %s, %s, %s, %s, %s, %s);
        """, (date, current_equity, current_equity * 0.75, current_equity * 0.25, current_equity - base_equity, daily_return))
    
    conn.commit()
    print("✅ Equity history seeded")

def main():
    """Run all database seeding"""
    print("🌱 Starting Trad Database Seeding...")
    
    try:
        conn = get_db_conn()
        print("✅ Database connected")
        
        seed_portfolio_data(conn)
        seed_trading_history(conn)
        seed_patterns_and_performance(conn)
        seed_equity_history(conn)
        
        conn.close()
        
        print("\n🎉 Database seeding completed successfully!")
        print("📊 Dashboard should now show realistic trading data")
        print("👤 Admin login: username='admin', password='admin123'")
            
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()