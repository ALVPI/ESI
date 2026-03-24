import time

from collectors.perf_collector import collect_perf_metrics
from collectors.cpu_core_collector import collect_cpu_core_metrics
from collectors.system_state_collector import collect_system_state_metrics
from collectors.storage_collector import collect_storage_metrics
from collectors.process_collector import collect_top_process_metrics

from metrics.cpu_metrics import get_cpu_counters
from metrics.memory_metrics import get_memory_counters
from metrics.network_metrics import get_network_counters
from metrics.disk_metrics import get_disk_counters

from db_writer import (
    insert_perf_metrics,
    insert_cpu_core_metrics,
    insert_system_state_metrics,
    insert_storage_metrics,
    insert_top_process_metrics
)


# Interval configuration (in seconds)
from config import (
    PERF_INTERVAL,
    SYSTEM_INTERVAL,
    STORAGE_INTERVAL,
    PROCESS_INTERVAL,
    SCHEDULER_SLEEP,
    TOP_PROCESS_COUNT
)


def run_scheduler(conn):
    """
    Main scheduler loop responsible for executing collectors
    at their corresponding intervals.
    """

    # Time tracking variables
    last_perf_time = 0
    last_system_time = 0
    last_storage_time = 0
    last_process_time = 0

    # Initial state for rate calculations
    prev_state = {
        **get_cpu_counters(),
        **get_memory_counters(),
        **get_network_counters(),
        **get_disk_counters()
    }

    while True:
        current_time = time.time()

        # Current state snapshot
        current_state = {
            **get_cpu_counters(),
            **get_memory_counters(),
            **get_network_counters(),
            **get_disk_counters()
        }

        # Performance metrics (every 10 seconds)
        if current_time - last_perf_time >= PERF_INTERVAL:
            try:
                perf_data = collect_perf_metrics(prev_state, current_state)
                insert_perf_metrics(conn, perf_data)

                cpu_core_data = collect_cpu_core_metrics()
                insert_cpu_core_metrics(conn, cpu_core_data)

            except Exception as e:
                print(f"[ERROR] Performance metrics block failed: {e}")

            last_perf_time = current_time

        # System state metrics (every 60 seconds)
        if current_time - last_system_time >= SYSTEM_INTERVAL:
            try:
                system_data = collect_system_state_metrics()
                insert_system_state_metrics(conn, system_data)

            except Exception as e:
                print(f"[ERROR] System state block failed: {e}")

            last_system_time = current_time

        # Storage metrics (every 5 minutes)
        if current_time - last_storage_time >= STORAGE_INTERVAL:
            try:
                storage_data = collect_storage_metrics(prev_state, current_state)
                insert_storage_metrics(conn, storage_data)

            except Exception as e:
                print(f"[ERROR] Storage block failed: {e}")

            last_storage_time = current_time

        # Top processes metrics (every 60 seconds)
        if current_time - last_process_time >= PROCESS_INTERVAL:
            try:
                process_data = collect_top_process_metrics(TOP_PROCESS_COUNT)
                insert_top_process_metrics(conn, process_data)

            except Exception as e:
                print(f"[ERROR] Process block failed: {e}")

            last_process_time = current_time

        # Update previous state for next iteration
        prev_state = current_state

        # Prevent excessive CPU usage
        time.sleep(SCHEDULER_SLEEP)
