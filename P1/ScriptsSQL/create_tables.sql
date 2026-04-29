CREATE TABLE IF NOT EXISTS metrics_perf (
        time TIMESTAMPTZ(0) DEFAULT CURRENT_TIMESTAMP,
        
        -- CPU
        load_1min FLOAT, load_5min FLOAT, load_15min FLOAT,
        cpu_user_pct FLOAT, cpu_sys_pct FLOAT, cpu_idle_pct FLOAT,
        ctx_switches_sec FLOAT, interrupts_sec FLOAT,
        
        -- Memoria
        ram_used_pct FLOAT, ram_free_mb FLOAT, 
        ram_cache_mb FLOAT, ram_buffers_mb FLOAT,
        swap_used_pct FLOAT, page_faults_sec FLOAT,
        
        -- Red instantánea
        net_rx_kbps FLOAT, net_tx_kbps FLOAT,
        net_err_in INT, net_err_out INT,
        PRIMARY KEY (time)
) PARTITION BY RANGE (time);

-- Particion por defecto si no se ha creado particion de hoy
CREATE TABLE IF NOT EXISTS metrics_perf_default PARTITION OF metrics_perf DEFAULT; 

CREATE TABLE IF NOT EXISTS metrics_cpu_cores (
    time TIMESTAMPTZ(0) NOT NULL,
    core_id INT NOT NULL,
    usage_pct FLOAT NOT NULL,
    PRIMARY KEY (time, core_id)
) PARTITION BY RANGE (time);

-- Particion por defecto si no se ha creado particion de hoy
CREATE TABLE IF NOT EXISTS metrics_cpu_cores_default PARTITION OF metrics_cpu_cores DEFAULT;

CREATE TABLE IF NOT EXISTS metrics_system_state (
    time TIMESTAMPTZ(0) DEFAULT CURRENT_TIMESTAMP,
    uptime_days FLOAT,
    procs_running INT, procs_sleeping INT, procs_zombie INT,
    tcp_conns_active INT,
    open_fds INT,
    db_size_mb FLOAT,
    db_active_conns INT,
    PRIMARY KEY (time)
) PARTITION BY RANGE (time);

-- Particion por defecto si no se ha creado particion de hoy
CREATE TABLE IF NOT EXISTS metrics_system_state_default PARTITION OF metrics_system_state DEFAULT;

CREATE TABLE IF NOT EXISTS metrics_storage (
    time TIMESTAMPTZ(0) NOT NULL,
    mount_point VARCHAR(50) NOT NULL,
    used_pct FLOAT,
    free_gb FLOAT,
    iops_read FLOAT, iops_write FLOAT,
    io_wait_ms FLOAT,
    PRIMARY KEY (time, mount_point)
) PARTITION BY RANGE (time);

-- Particion por defecto si no se ha creado particion de hoy
CREATE TABLE IF NOT EXISTS metrics_storage_default PARTITION OF metrics_storage DEFAULT;

CREATE TABLE IF NOT EXISTS metrics_top_procs (
    time TIMESTAMPTZ(0) NOT NULL,
    rank INT, -- 1, 2, 3...
    proc_name VARCHAR(100),
    cpu_pct FLOAT,
    mem_pct FLOAT,
    PRIMARY KEY (time, rank)
) PARTITION BY RANGE (time);

-- Particion por defecto si no se ha creado particion de hoy
CREATE TABLE IF NOT EXISTS metrics_top_procs_default PARTITION OF metrics_top_procs DEFAULT;
