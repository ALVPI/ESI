def insert_perf_metrics(conn, data):
    """
    Inserts into metrics_perf table.
    """

    query = """
    INSERT INTO metrics_perf (
        time,
        load_1min, load_5min, load_15min,
        cpu_user_pct, cpu_sys_pct, cpu_idle_pct,
        ctx_switches_sec, interrupts_sec,
        ram_used_pct, ram_free_mb,
        ram_cache_mb, ram_buffers_mb,
        swap_used_pct, page_faults_sec,
        net_rx_kbps, net_tx_kbps,
        net_err_in, net_err_out
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data.get("time"),
        data.get("load_1min"), data.get("load_5min"), data.get("load_15min"),
        data.get("cpu_user_pct"), data.get("cpu_sys_pct"), data.get("cpu_idle_pct"),
        data.get("ctx_switches_sec"), data.get("interrupts_sec"),
        data.get("ram_used_pct"), data.get("ram_free_mb"),
        data.get("ram_cache_mb"), data.get("ram_buffers_mb"),
        data.get("swap_used_pct"), data.get("page_faults_sec"),
        data.get("net_rx_kbps"), data.get("net_tx_kbps"),
        data.get("net_err_in"), data.get("net_err_out")
    )

    with conn.cursor() as cur:
        try:
            cur.execute(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] insert_perf_metrics: {e}")


def insert_cpu_core_metrics(conn, data_list):
    """
    Inserts multiple rows into metrics_cpu_cores.
    """

    if not data_list:
        return

    query = """
    INSERT INTO metrics_cpu_cores (time, core_id, usage_pct)
    VALUES (%s, %s, %s)
    """

    values = [
        (d.get("time"), d.get("core_id"), d.get("usage_pct"))
        for d in data_list
    ]

    with conn.cursor() as cur:
        try:
            cur.executemany(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] insert_cpu_core_metrics: {e}")


def insert_system_state_metrics(conn, data):
    """
    Inserts into metrics_system_state.
    """

    query = """
    INSERT INTO metrics_system_state (
        time,
        uptime_days,
        procs_running, procs_sleeping, procs_zombie,
        tcp_conns_active,
        open_fds,
        db_size_mb,
        db_active_conns
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data.get("time"),
        data.get("uptime_days"),
        data.get("procs_running"), data.get("procs_sleeping"), data.get("procs_zombie"),
        data.get("tcp_conns_active"),
        data.get("open_fds"),
        data.get("db_size_mb"),
        data.get("db_active_conns")
    )

    with conn.cursor() as cur:
        try:
            cur.execute(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] insert_system_state_metrics: {e}")


def insert_storage_metrics(conn, data_list):
    """
    Inserts multiple rows into metrics_storage.
    """

    if not data_list:
        return

    query = """
    INSERT INTO metrics_storage (
        time,
        mount_point,
        used_pct,
        free_gb,
        iops_read,
        iops_write,
        io_wait_ms
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    values = [
        (
            d.get("time"),
            d.get("mount_point"),
            d.get("used_pct"),
            d.get("free_gb"),
            d.get("iops_read"),
            d.get("iops_write"),
            d.get("io_wait_ms")
        )
        for d in data_list
    ]

    with conn.cursor() as cur:
        try:
            cur.executemany(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] insert_storage_metrics: {e}")


def insert_top_process_metrics(conn, data_list):
    """
    Inserts into metrics_top_procs.
    """

    if not data_list:
        return

    query = """
    INSERT INTO metrics_top_procs (
        time,
        rank,
        proc_name,
        cpu_pct,
        mem_pct
    ) VALUES (%s, %s, %s, %s, %s)
    """

    values = [
        (
            d.get("time"),
            d.get("rank"),
            d.get("proc_name"),
            d.get("cpu_pct"),
            d.get("mem_pct")
        )
        for d in data_list
    ]

    with conn.cursor() as cur:
        try:
            cur.executemany(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] insert_top_process_metrics: {e}")