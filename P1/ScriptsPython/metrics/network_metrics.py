import psutil
import time


def get_network_throughput(prev_state, current_state):
    """
    rx = receive
    tx = transmit
    kbps = kilobytes per second
    """

    delta_time = current_state["timestamp"] - prev_state["timestamp"]

    rx_bytes = current_state["bytes_recv"] - prev_state["bytes_recv"]
    tx_bytes = current_state["bytes_sent"] - prev_state["bytes_sent"]

    if delta_time <= 0:
        return 0, 0

    rx_kbps = (rx_bytes / 1024) / delta_time
    tx_kbps = (tx_bytes / 1024) / delta_time

    return rx_kbps, tx_kbps


def get_network_errors():
    """
    Returns total network errors.
    """
    stats = psutil.net_io_counters()

    return stats.errin, stats.errout


def get_network_counters():
    """
    Returns raw counters.
    """
    net = psutil.net_io_counters()

    return {
        "bytes_recv": net.bytes_recv,
        "bytes_sent": net.bytes_sent,
        "timestamp": time.time()
    }