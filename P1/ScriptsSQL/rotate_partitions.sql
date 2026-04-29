CREATE OR REPLACE FUNCTION manage_all_metrics_partitions() RETURNS void AS $$
DECLARE
    t_name TEXT;
    today_table TEXT;
    tomorrow_table TEXT;
    old_table TEXT;
    tomorrow_start DATE := CURRENT_DATE + 1;
    tomorrow_end DATE := CURRENT_DATE + 2;
    old_date DATE := CURRENT_DATE - 2; -- Borra lo de hace 2 días
BEGIN
    -- Lista de tus tablas maestras
    FOR t_name IN SELECT unnest(ARRAY['metrics_perf', 'metrics_cpu_cores', 'metrics_system_state', 'metrics_storage', 'metrics_top_procs'])
    LOOP
        -- 1. Crear partición de MAÑANA
        tomorrow_table := t_name || '_' || to_char(tomorrow_start, 'YYYY_MM_DD');
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = tomorrow_table) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)', 
                            tomorrow_table, t_name, tomorrow_start, tomorrow_end);
        END IF;

        -- 2. Borrar partición ANTIGUA (Anteayer)
        old_table := t_name || '_' || to_char(old_date, 'YYYY_MM_DD');
        EXECUTE format('DROP TABLE IF EXISTS %I', old_table);
    END LOOP;
END;
$$ LANGUAGE plpgsql;