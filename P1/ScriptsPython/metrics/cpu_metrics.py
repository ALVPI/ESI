import psutil
import time


def get_load_average():
    """
    Returns system load average over 1, 5, 15 minutes.
    """
    return psutil.getloadavg()


def get_cpu_usage_percentages():
    """
    Returns CPU usage percentages.

    user: time spent in user processes
    system: time spent in kernel
    idle: idle CPU time
    """
    cpu_times = psutil.cpu_times_percent(interval=0)

    return (
        cpu_times.user,
        cpu_times.system,
        cpu_times.idle
    )


def get_cpu_core_usage():
    """
    Returns usage percentage for each CPU core.
    """
    return psutil.cpu_percent(percpu=True, interval=0)


def get_ctx_switches_per_sec(prev_state, current_state):
    """
    ctx = context switches
    sec = per second
    """
    prev = prev_state["ctx_switches"]
    curr = current_state["ctx_switches"]
    delta_time = current_state["timestamp"] - prev_state["timestamp"]

    return (curr - prev) / delta_time if delta_time > 0 else 0


def get_interrupts_per_sec(prev_state, current_state):
    """
    interrupts per second
    """
    prev = prev_state["interrupts"]
    curr = current_state["interrupts"]
    delta_time = current_state["timestamp"] - prev_state["timestamp"]

    return (curr - prev) / delta_time if delta_time > 0 else 0


def get_cpu_counters():
    """
    Returns raw counters needed for rate calculations.
    """
    stats = psutil.cpu_stats()

    return {
        "ctx_switches": stats.ctx_switches,
        "interrupts": stats.interrupts,
        "timestamp": time.time()
    }