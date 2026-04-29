import psutil
import time


def get_memory_usage():
    """
    Returns RAM usage metrics.

    pct = percentage
    mb = megabytes
    """
    mem = psutil.virtual_memory()

    return (
        mem.percent,
        mem.available / (1024 * 1024),
        mem.cached / (1024 * 1024),
        mem.buffers / (1024 * 1024)
    )


def get_swap_usage():
    """
    Returns swap usage percentage.
    """
    swap = psutil.swap_memory()
    return swap.percent


def get_page_faults_per_sec(prev_state, current_state):
    """
    Page faults per second.
    """
    prev = prev_state["page_faults"]
    curr = current_state["page_faults"]
    delta_time = current_state["timestamp"] - prev_state["timestamp"]

    return (curr - prev) / delta_time if delta_time > 0 else 0


def get_memory_counters():
    """
    Returns raw memory counters.
    """
    vm = psutil.virtual_memory()

    return {
        "page_faults": getattr(vm, "pfaults", 0),
        "timestamp": time.time()
    }