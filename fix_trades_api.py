"""
Quick fix for trades API to match server database schema
"""

# Replace the trades query in api/trades.py
query_fix = '''
            cur.execute(
                """
                SELECT id, symbol, direction, quantity, price, fill_cost, commission, executed_at
                FROM trades 
                WHERE user_id = 1
                ORDER BY executed_at DESC 
                LIMIT 10
                """
            )
            trades = cur.fetchall()
            
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    "id": trade['id'],
                    "timestamp": trade['executed_at'].isoformat() if trade['executed_at'] else None,
                    "symbol": trade['symbol'],
                    "direction": trade['direction'],
                    "quantity": float(trade['quantity'] or 0),
                    "price": float(trade['price'] or 0),
                    "fillCost": float(trade['fill_cost'] or 0),
                    "commission": float(trade['commission'] or 0),
                    "status": "CLOSED"
                })
'''

print("Updated query for trades endpoint:")
print(query_fix)