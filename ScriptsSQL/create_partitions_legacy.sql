--LEGACY, no usar, los nombres no servian para la funcion de rotate_partitions.sql
--Particiones iniciales antes del script

-- Particiones para la tabla metrics_perf
CREATE TABLE IF NOT EXISTS metrics_perf_today 
PARTITION OF metrics_perf FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + 1);

CREATE TABLE IF NOT EXISTS metrics_perf_tomorrow 
PARTITION OF metrics_perf FOR VALUES FROM (CURRENT_DATE + 1) TO (CURRENT_DATE + 2);

-- Particiones para la tabla metrics_cpu_cores
CREATE TABLE IF NOT EXISTS metrics_cpu_cores_today 
PARTITION OF metrics_cpu_cores FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + 1);

CREATE TABLE IF NOT EXISTS metrics_cpu_cores_tomorrow 
PARTITION OF metrics_cpu_cores FOR VALUES FROM (CURRENT_DATE + 1) TO (CURRENT_DATE + 2);

-- Particiones para la tabla metrics_system_state
CREATE TABLE IF NOT EXISTS metrics_system_state_today 
PARTITION OF metrics_system_state FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + 1);

CREATE TABLE IF NOT EXISTS metrics_system_state_tomorrow 
PARTITION OF metrics_system_state FOR VALUES FROM (CURRENT_DATE + 1) TO (CURRENT_DATE + 2);

-- Particiones para la tabla metrics_storage
CREATE TABLE IF NOT EXISTS metrics_storage_today 
PARTITION OF metrics_storage FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + 1);

CREATE TABLE IF NOT EXISTS metrics_storage_tomorrow 
PARTITION OF metrics_storage FOR VALUES FROM (CURRENT_DATE + 1) TO (CURRENT_DATE + 2);

-- Particiones para la tabla metrics_top_procs
CREATE TABLE IF NOT EXISTS metrics_top_procs_today 
PARTITION OF metrics_top_procs FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + 1);

CREATE TABLE IF NOT EXISTS metrics_top_procs_tomorrow 
PARTITION OF metrics_top_procs FOR VALUES FROM (CURRENT_DATE + 1) TO (CURRENT_DATE + 2);