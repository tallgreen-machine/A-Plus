#!/usr/bin/env python3
"""
Database Migration Script for Trad Trading System
Executes all SQL migrations in the correct order to set up the complete schema.
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.db import get_db_conn

def execute_sql_file(conn, file_path):
    """Execute a SQL file"""
    print(f"📝 Executing {file_path.name}...")
    
    with open(file_path, 'r') as f:
        sql_content = f.read()
    
    try:
        cur = conn.cursor()
        cur.execute(sql_content)
        conn.commit()
        print(f"✅ {file_path.name} executed successfully")
        return True
    except Exception as e:
        print(f"❌ Error executing {file_path.name}: {e}")
        conn.rollback()
        return False

def main():
    """Run all database migrations"""
    print("🚀 Starting Trad Database Migration...")
    
    # SQL files in execution order (dependencies matter)
    sql_files = [
        "006_create_users_and_multitenancy.sql",  # Users first (everything depends on this)
        "002_create_market_data.sql",             # Market data
        "005_create_market_data.sql",             # Additional market data
        "005_create_market_state.sql",            # Market state
        "004_create_current_embeddings.sql",     # Embeddings
        "006_create_policy_config.sql",          # Policy config
        "003_create_trades.sql",                 # Trades table
        "007_create_portfolio_system.sql",       # Portfolio system
        "008_create_pattern_system.sql",         # Pattern system
        "001_create_backtest_results.sql",       # Backtest results
        "002_create_pattern_training_results.sql", # Pattern training
        "dashboard_init.sql",                    # Dashboard data
    ]
    
    sql_dir = project_root / "sql"
    
    try:
        conn = get_db_conn()
        print("✅ Database connected")
        
        success_count = 0
        for sql_file in sql_files:
            file_path = sql_dir / sql_file
            if file_path.exists():
                if execute_sql_file(conn, file_path):
                    success_count += 1
            else:
                print(f"⚠️  File not found: {sql_file}")
        
        # Create initial admin user with password hash
        print("👤 Creating initial admin user...")
        cur = conn.cursor()
        # Using bcrypt hash for password 'admin123'
        password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewMqRZgBrG4WdpP6'
        cur.execute("""
            INSERT INTO users (username, display_name, email, password_hash, is_active, is_admin) 
            VALUES ('admin', 'Administrator', 'admin@trad.ai', %s, true, true)
            ON CONFLICT (username) DO NOTHING;
        """, (password_hash,))
        conn.commit()
        
        # Show final table list
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
        tables = [t[0] for t in cur.fetchall()]
        
        conn.close()
        
        print(f"\n🎉 Migration completed! {success_count}/{len(sql_files)} files executed successfully")
        print(f"📊 Database now has {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()