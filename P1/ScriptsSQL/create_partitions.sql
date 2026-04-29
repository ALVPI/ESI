-- Ejecuta esto para inicializar hoy y mañana con el formato de fecha correcto
DO $$ 
DECLARE 
    t_name TEXT;
    today_date TEXT := to_char(CURRENT_DATE, 'YYYY_MM_DD');
    tomorrow_date TEXT := to_char(CURRENT_DATE + 1, 'YYYY_MM_DD');
    d_today DATE := CURRENT_DATE;
    d_tomorrow DATE := CURRENT_DATE + 1;
    d_after DATE := CURRENT_DATE + 2;
BEGIN
    FOR t_name IN SELECT unnest(ARRAY['metrics_perf', 'metrics_cpu_cores', 'metrics_system_state', 'metrics_storage', 'metrics_top_procs'])
    LOOP
        -- Partición de HOY
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)', 
                        t_name || '_' || today_date, t_name, d_today, d_tomorrow);
        -- Partición de MAÑANA
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)', 
                        t_name || '_' || tomorrow_date, t_name, d_tomorrow, d_after);
    END LOOP;
END $$;