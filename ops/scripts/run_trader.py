# ops/scripts/run_trader.py
import sys
import os
import argparse

# This is a bit of a hack to make sure the script can find the other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from policy.trader import SimpleTrader

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the simple trading bot.")
    parser.add_argument('--symbol', type=str, default="BTC/USDT", help='The trading symbol to monitor.')
    args = parser.parse_args()

    trader = SimpleTrader(symbol=args.symbol)
    trader.run_trading_loop()
