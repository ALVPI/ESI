from metrics.cpu_metrics import get_cpu_core_usage
from utils.time_utils import get_current_timestamp


def collect_cpu_core_metrics():
    """
    Collects per-core CPU usage.
    """

    timestamp = get_current_timestamp()
    core_usages = get_cpu_core_usage()

    results = []

    for core_id, usage_pct in enumerate(core_usages):
        results.append({
            "time": timestamp,
            "core_id": core_id,
            "usage_pct": usage_pct
        })

    return results