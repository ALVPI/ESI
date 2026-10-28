from metrics.process_metrics import get_top_processes
from utils.time_utils import get_current_timestamp
from config import TOP_PROCESS_COUNT


def collect_top_process_metrics(TOP_PROCESS_COUNT):
    """
    Collects top N processes by CPU and memory usage.

    TOP_PROCESS_COUNT: number of top processes to collect
    """

    timestamp = get_current_timestamp()
    top_processes = get_top_processes(TOP_PROCESS_COUNT)

    results = []

    for rank, proc in enumerate(top_processes, start=1):
        results.append({
            "time": timestamp,
            "rank": rank,
            "proc_name": proc["name"],
            "cpu_pct": proc["cpu_pct"],
            "mem_pct": proc["mem_pct"]
        })

    return results