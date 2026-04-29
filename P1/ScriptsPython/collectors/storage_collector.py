from metrics.disk_metrics import (
    get_disk_usage,
    get_disk_io_stats
)

from utils.time_utils import get_current_timestamp


def collect_storage_metrics(prev_state, current_state):
    """
    Collects storage metrics per mount point.
    """

    timestamp = get_current_timestamp()

    disk_usages = get_disk_usage()
    disk_io_stats = get_disk_io_stats(prev_state, current_state)

    results = []

    for mount_point in disk_usages:

        usage = disk_usages[mount_point]
        io_stats = disk_io_stats.get(mount_point, {})

        results.append({
            "time": timestamp,
            "mount_point": mount_point,
            "used_pct": usage["used_pct"],
            "free_gb": usage["free_gb"],
            "iops_read": io_stats.get("iops_read", 0),
            "iops_write": io_stats.get("iops_write", 0),
            "io_wait_ms": io_stats.get("io_wait_ms", 0)
        })

    return results