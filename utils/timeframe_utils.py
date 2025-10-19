import backtrader as bt

TIMEFRAME_MAP = {
    '1m': (bt.TimeFrame.Minutes, 1),
    '5m': (bt.TimeFrame.Minutes, 5),
    '15m': (bt.TimeFrame.Minutes, 15),
    '30m': (bt.TimeFrame.Minutes, 30),
    '1h': (bt.TimeFrame.Minutes, 60),
    '4h': (bt.TimeFrame.Minutes, 240),
    '1d': (bt.TimeFrame.Days, 1),
}

REVERSE_TIMEFRAME_MAP = {
    (bt.TimeFrame.Minutes, 1): '1m',
    (bt.TimeFrame.Minutes, 5): '5m',
    (bt.TimeFrame.Minutes, 15): '15m',
    (bt.TimeFrame.Minutes, 30): '30m',
    (bt.TimeFrame.Minutes, 60): '1h',
    (bt.TimeFrame.Minutes, 240): '4h',
    (bt.TimeFrame.Days, 1): '1d',
}

def timeframe_to_seconds(tf_str: str) -> int:
    """Converts a timeframe string (e.g., '1h', '5m') to seconds."""
    unit = tf_str[-1]
    value = int(tf_str[:-1])
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 60 * 60
    elif unit == 'd':
        return value * 24 * 60 * 60
    else:
        raise ValueError(f"Invalid timeframe unit: {unit}")

def get_lowest_timeframe(timeframes: list[str]) -> str:
    """Returns the lowest timeframe string from a list of timeframes."""
    if not timeframes:
        return None
    return min(timeframes, key=timeframe_to_seconds)
