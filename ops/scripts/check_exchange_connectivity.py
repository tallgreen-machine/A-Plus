import ccxt

def test_exchange_connectivity(exchange_id):
    """
    Tests the connectivity to a given exchange and fetches ticker data.
    """
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        exchange.load_markets()
        if exchange.has['fetchTickers']:
            tickers = exchange.fetch_tickers()
            print(f"✅ Successfully connected to {exchange_id} and fetched {len(tickers)} tickers.")
        else:
            print(f"⚠️ Could not fetch tickers from {exchange_id} - 'fetchTickers' not supported.")
    except Exception as e:
        print(f"❌ Failed to connect to {exchange_id}: {e}")

def main():
    """
    Main function to test connectivity for a list of exchanges.
    """
    exchanges = [
        'binanceus',
        'bitstamp',
        'coinbase',
        'cryptocom',
        'gemini',
        'kraken',
    ]
    
    for exchange_id in exchanges:
        test_exchange_connectivity(exchange_id)

if __name__ == "__main__":
    main()
