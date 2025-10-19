import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from flask import Flask, jsonify, render_template
from flask_httpauth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from shared.db import get_db_conn

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'aplus.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
auth = HTTPBasicAuth()

# --- Security ---
users = {
    os.getenv("DASHBOARD_USER", "admin"): os.getenv("DASHBOARD_PASSWORD", "password")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

@app.route('/auth')
@auth.login_required
def auth_check():
    # This view is protected by @auth.login_required. If the user is authenticated,
    # Flask-HTTPAuth will allow the request to proceed and we return 200 OK.
    # If not, it will automatically send a 401 Unauthorized response, which Caddy will intercept.
    return "OK", 200

# --- Routes ---
# The routes below are now protected by Caddy's forward_auth, not directly by @auth.login_required.
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/portfolio')
def get_portfolio():
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Fetch latest portfolio state
    cur.execute("SELECT * FROM portfolio_history ORDER BY timestamp DESC LIMIT 1")
    portfolio = cur.fetchone()
    
    # Fetch current holdings (this is a simplified view)
    cur.execute("SELECT symbol, SUM(CASE WHEN direction = 'BUY' THEN quantity ELSE -quantity END) as quantity FROM trades GROUP BY symbol HAVING SUM(CASE WHEN direction = 'BUY' THEN quantity ELSE -quantity END) > 0")
    holdings = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'portfolio': dict(portfolio) if portfolio else {},
        'holdings': [dict(row) for row in holdings]
    })

@app.route('/api/trades')
def get_trades():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 100")
    trades = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(row) for row in trades])


@app.route('/api/logs')
def get_logs():
    try:
        with open('/var/log/aplus.log', 'r') as f:
            logs = f.readlines()
        return jsonify(logs[-100:]) # Return last 100 lines
    except FileNotFoundError:
        return jsonify(["Log file not found."]), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
