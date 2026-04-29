import psutil


def get_process_counts():
    """
    Returns number of processes by state.
    """
    running = 0
    sleeping = 0
    zombie = 0

    for proc in psutil.process_iter(['status']):
        try:
            status = proc.info['status']

            if status == psutil.STATUS_RUNNING:
                running += 1
            elif status == psutil.STATUS_SLEEPING:
                sleeping += 1
            elif status == psutil.STATUS_ZOMBIE:
                zombie += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return running, sleeping, zombie


def get_top_processes(top_n=3):
    """
    Returns top processes by CPU usage.
    """

    processes = []

    for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append({
                "name": proc.info['name'],
                "cpu_pct": proc.info['cpu_percent'],
                "mem_pct": proc.info['memory_percent']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda x: x["cpu_pct"], reverse=True)

    return processes[:top_n]