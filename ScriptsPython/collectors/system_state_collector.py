from metrics.system_metrics import (
    get_system_uptime,
    get_process_counts,
    get_tcp_connections,
    get_open_file_descriptors,
    get_db_stats
)

from utils.time_utils import get_current_timestamp


def collect_system_state_metrics():
    """
    Collects system state metrics (low frequency).
    """

    timestamp = get_current_timestamp()

    uptime_days = get_system_uptime()

    procs_running, procs_sleeping, procs_zombie = get_process_counts()

    tcp_conns_active = get_tcp_connections()

    open_fds = get_open_file_descriptors()

    db_size_mb, db_active_conns = get_db_stats()

    return {
        "time": timestamp,
        "uptime_days": uptime_days,
        "procs_running": procs_running,
        "procs_sleeping": procs_sleeping,
        "procs_zombie": procs_zombie,
        "tcp_conns_active": tcp_conns_active,
        "open_fds": open_fds,
        "db_size_mb": db_size_mb,
        "db_active_conns": db_active_conns
    }