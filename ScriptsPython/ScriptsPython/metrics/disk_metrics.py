import psutil
import time


def get_disk_usage():
    """
    Returns usage per mount point.
    """

    partitions = psutil.disk_partitions()
    result = {}

    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)

            result[p.mountpoint] = {
                "used_pct": usage.percent,
                "free_gb": usage.free / (1024 ** 3)
            }
        except PermissionError:
            continue

    return result


def get_disk_io_stats(prev_state, current_state):
    """
    iops = input/output operations per second
    """

    delta_time = current_state["timestamp"] - prev_state["timestamp"]

    results = {}

    for disk in current_state["disks"]:
        prev_disk = prev_state["disks"].get(disk, {})
        curr_disk = current_state["disks"][disk]

        if delta_time <= 0:
            continue

        read_ops = curr_disk["read_count"] - prev_disk.get("read_count", 0)
        write_ops = curr_disk["write_count"] - prev_disk.get("write_count", 0)

        results[disk] = {
            "iops_read": read_ops / delta_time,
            "iops_write": write_ops / delta_time,
            "io_wait_ms": curr_disk.get("busy_time", 0)
        }

    return results


def get_disk_counters():
    """
    Returns raw disk stats.
    """
    io = psutil.disk_io_counters(perdisk=True)

    disks = {}

    for disk, stats in io.items():
        disks[disk] = {
            "read_count": stats.read_count,
            "write_count": stats.write_count,
            "busy_time": getattr(stats, "busy_time", 0)
        }

    return {
        "disks": disks,
        "timestamp": time.time()
    }