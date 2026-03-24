import psutil
import time
import os
import subprocess


def get_system_uptime():
    """
    Returns system uptime in days.
    """
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time

    return uptime_seconds / (60 * 60 * 24)


def get_tcp_connections():
    """
    Returns number of active TCP connections.
    """
    connections = psutil.net_connections(kind='tcp')

    return len([c for c in connections if c.status == 'ESTABLISHED'])


def get_open_file_descriptors():
    """
    Returns number of open file descriptors.
    """
    try:
        return len(os.listdir('/proc/self/fd'))
    except:
        return 0


def get_db_stats():
    """
    Returns database size and active connections.
    Uses PostgreSQL system queries.
    """

    try:
        size_query = "SELECT pg_database_size(current_database());"
        conn_query = "SELECT count(*) FROM pg_stat_activity;"

        db_uri = "postgresql://usuario:akelarre@localhost:5432/metrics"

        size = subprocess.check_output(
                ["psql",db_uri, "-t", "-c", size_query]
        ).decode().strip()

        conns = subprocess.check_output(
            ["psql", db_uri, "-t", "-c", conn_query]
        ).decode().strip()

        return float(size) / (1024 * 1024), int(conns)

    except:
        return 0, 0
