def calculate_rate(current_value, previous_value, time_delta):
    """
    Generic rate calculator.

    rate = (current - previous) / time

    Returns value per second.
    """

    if time_delta <= 0:
        return 0

    return (current_value - previous_value) / time_delta


def calculate_kilobytes_per_second(current_bytes, previous_bytes, time_delta):
    """
    Converts byte rate to KB/s.

    kbps = kilobytes per second
    """

    rate_bytes = calculate_rate(current_bytes, previous_bytes, time_delta)

    return rate_bytes / 1024


def calculate_percentage(part, total):
    """
    Calculates percentage safely.

    pct = percent
    """

    if total == 0:
        return 0

    return (part / total) * 100


def calculate_difference(current_value, previous_value):
    """
    Simple difference between values.

    Useful for debugging or raw metrics.
    """

    return current_value - previous_value