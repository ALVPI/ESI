"""
Configuration file for the monitoring system.
All configurable parameters are centralized here.
"""

# =========================
# DATABASE CONFIGURATION
# =========================

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "metrics"
DB_USER = "grafana"
DB_PASSWORD = "akelarre"


# =========================
# INTERVAL CONFIGURATION (seconds)
# =========================

PERF_INTERVAL = 10          # metrics_perf + cpu_cores
SYSTEM_INTERVAL = 60       # metrics_system_state
STORAGE_INTERVAL = 300     # metrics_storage (5 minutes)
PROCESS_INTERVAL = 60      # metrics_top_procs


# =========================
# PROCESS CONFIGURATION
# =========================

TOP_PROCESS_COUNT = 3      # number of top processes to store


# =========================
# SYSTEM SETTINGS
# =========================

SCHEDULER_SLEEP = 1        # loop sleep time (seconds)


# =========================
# DEBUG / LOGGING
# =========================

DEBUG = True               # enable debug prints