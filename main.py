import time
import os
from dotenv import load_dotenv
import datetime

from utils.logger import log
from utils.timeframe_utils import get_lowest_timeframe, timeframe_to_seconds
from core.event_system import EventBus
from core.data_handler import DataHandler
from core.signal_library import SignalLibrary
from core.execution_core import ExecutionCore, Portfolio, SimulatedExchange
from shared.db import get_db_conn

def log_portfolio_history(db_conn, portfolio: Portfolio):
    """Logs the current portfolio equity and cash to the database."""
    if db_conn is None:
        log.error("Database connection is not available for portfolio logging.")
        return
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO portfolio_history (timestamp, cash, equity)
                VALUES (%s, %s, %s)
                """,
                (datetime.datetime.now(datetime.timezone.utc), portfolio.cash, portfolio.current_equity),
            )
        log.info(f"Logged portfolio history: Cash={portfolio.cash:.2f}, Equity={portfolio.current_equity:.2f}")
    except Exception as e:
        log.error(f"Database error while logging portfolio history: {e}", exc_info=True)

def main():
    """
    Main function to run the trading bot.
    """
    log.info("Starting Trad Trading Bot...")
    
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'trad.env')
    load_dotenv(dotenv_path=env_path)
    log.info(f"Loaded environment from {env_path}")

    # Configuration
    symbols = os.getenv('SYMBOLS', 'BTC/USDT').split(',')
    timeframes = os.getenv('TIMEFRAMES', '1h,4h').split(',')
    initial_cash = float(os.getenv('INITIAL_CASH', 10000.0))
    exchange_id = os.getenv('EXCHANGE_ID', 'binance')
    paper_trade = os.getenv('PAPER_TRADE', 'true').lower() in ('true', '1', 't')
    
    log.info(f"Configuration: Symbols={symbols}, Timeframes={timeframes}, Exchange={exchange_id}, Paper Trading={paper_trade}")

    # Initialization
    event_bus = EventBus()
    portfolio = Portfolio(initial_cash=initial_cash)
    db_conn = get_db_conn() # Initialize database connection
    
    # The modules are initialized and wired together via the event bus
    data_handler = DataHandler(event_bus, symbols, timeframes, exchange_id)
    signal_library = SignalLibrary(event_bus, symbols)
    execution_core = ExecutionCore(event_bus, portfolio)

    if paper_trade:
        simulated_exchange = SimulatedExchange(event_bus, data_handler)
        log.info("Paper trading enabled. SimulatedExchange is active.")

    log.info("All modules initialized. Starting main loop...")

    # Main loop
    try:
        lowest_tf_str = get_lowest_timeframe(timeframes)
        lowest_tf_seconds = timeframe_to_seconds(lowest_tf_str)
        log.info(f"Lowest timeframe detected: {lowest_tf_str} ({lowest_tf_seconds} seconds). Synchronizing loop.")

        while True:
            # Log portfolio status at the beginning of each cycle
            log_portfolio_history(db_conn, portfolio)

            # Initial data fetch
            data_handler.update_data()

            # Calculate time until the next candle close
            now = datetime.datetime.utcnow()
            timestamp = now.timestamp()
            
            time_to_next_candle = lowest_tf_seconds - (timestamp % lowest_tf_seconds)
            
            # Add a small buffer to ensure the candle is closed
            sleep_duration = time_to_next_candle + 2 # 2-second buffer
            
            log.info(f"Next candle in {time_to_next_candle:.2f}s. Sleeping for {sleep_duration:.2f}s.")
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        log.info("Trading bot stopped by user.")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        log.info("Trad Trading Bot shutting down.")
        if db_conn:
            db_conn.close()
            log.info("Database connection closed.")

if __name__ == "__main__":
    main()
