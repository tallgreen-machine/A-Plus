#!/usr/bin/env python3
"""
Quick database check and fix any missing data
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.db import get_db_conn

def main():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        print("🔍 Checking database status...")
        
        # Check key tables
        tables_to_check = ['users', 'portfolio_snapshots', 'holdings', 'trades', 'patterns', 'equity_history']
        
        for table in tables_to_check:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            print(f"  - {table}: {count} records")
        
        # Add some equity history if missing
        cur.execute("SELECT COUNT(*) FROM equity_history WHERE user_id = 1;")
        equity_count = cur.fetchone()[0]
        
        if equity_count == 0:
            print("📊 Adding equity history...")
            base_equity = 97500.0
            current_equity = base_equity
            
            for i in range(30):
                date = datetime.now() - timedelta(days=29-i)
                daily_change = random.uniform(-0.02, 0.03)
                current_equity = current_equity * (1 + daily_change)
                
                cur.execute("""
                    INSERT INTO equity_history (user_id, timestamp, equity, cash, market_value, total_pnl, daily_return)
                    VALUES (1, %s, %s, %s, %s, %s, %s);
                """, (date, current_equity, current_equity * 0.75, current_equity * 0.25, current_equity - base_equity, daily_change))
            
            conn.commit()
            print("✅ Equity history added")
        
        conn.close()
        
        print("\n🎉 Database check completed!")
        print("🌐 Ready to test with updated APIs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()