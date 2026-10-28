#!/bin/bash
# Llama a la función que ya está guardada en la base de datos
psql -d metrics -c "SELECT manage_all_metrics_partitions();"