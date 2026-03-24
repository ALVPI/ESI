from metrics.cpu_metrics import (
    get_load_average,
    get_cpu_usage_percentages,
    get_ctx_switches_per_sec,
    get_interrupts_per_sec
)

from metrics.memory_metrics import (
    get_memory_usage,
    get_swap_usage,
    get_page_faults_per_sec
)

from metrics.network_metrics import (
    get_network_throughput,
    get_network_errors
)

from utils.time_utils import get_current_timestamp


def collect_perf_metrics(prev_state, current_state):
    """
    Collects all high-frequency performance metrics.

    prev_state: previous snapshot of counters (for rate calculation)
    current_state: current snapshot
    """

    timestamp = get_current_timestamp()

    # CPU
    load_1min, load_5min, load_15min = get_load_average()
    cpu_user_pct, cpu_sys_pct, cpu_idle_pct = get_cpu_usage_percentages()

    ctx_switches_sec = get_ctx_switches_per_sec(prev_state, current_state)
    interrupts_sec = get_interrupts_per_sec(prev_state, current_state)

    # Memory
    ram_used_pct, ram_free_mb, ram_cache_mb, ram_buffers_mb = get_memory_usage()
    swap_used_pct = get_swap_usage()
    page_faults_sec = get_page_faults_per_sec(prev_state, current_state)

    # Network
    net_rx_kbps, net_tx_kbps = get_network_throughput(prev_state, current_state)
    net_err_in, net_err_out = get_network_errors()

    return {
        "time": timestamp,
        "load_1min": load_1min,
        "load_5min": load_5min,
        "load_15min": load_15min,
        "cpu_user_pct": cpu_user_pct,
        "cpu_sys_pct": cpu_sys_pct,
        "cpu_idle_pct": cpu_idle_pct,
        "ctx_switches_sec": ctx_switches_sec,
        "interrupts_sec": interrupts_sec,
        "ram_used_pct": ram_used_pct,
        "ram_free_mb": ram_free_mb,
        "ram_cache_mb": ram_cache_mb,
        "ram_buffers_mb": ram_buffers_mb,
        "swap_used_pct": swap_used_pct,
        "page_faults_sec": page_faults_sec,
        "net_rx_kbps": net_rx_kbps,
        "net_tx_kbps": net_tx_kbps,
        "net_err_in": net_err_in,
        "net_err_out": net_err_out
    }