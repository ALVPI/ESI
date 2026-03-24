import time
from datetime import datetime


def get_current_timestamp():
    """
    Returns current timestamp in datetime format.

    This is used for SQL insertion (TIMESTAMP).
    """
    return datetime.now()


def get_current_time_seconds():
    """
    Returns current time in seconds (float).

    Used for rate calculations.
    """
    return time.time()


def calculate_time_delta(prev_timestamp, current_timestamp):
    """
    Calculates time difference in seconds.

    prev_timestamp: float (seconds)
    current_timestamp: float (seconds)
    """

    return current_timestamp - prev_timestamp