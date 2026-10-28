# 📊 System Monitoring Daemon (Python + PostgreSQL + Grafana)

Este subproyecto corresponde a la **Práctica 1** de la asignatura *Evaluación de Sistemas Informáticos*. Se trata de una solución de monitorización construida "desde cero" (sin usar agentes de terceros como Prometheus), diseñada para ejecutarse como un *daemon* en Linux, recolectar métricas del sistema operativo y almacenarlas de forma eficiente en una base de datos relacional para su posterior visualización.

## 🚀 Arquitectura y Tecnologías
*   **Recolección (Python):** Scripts modulares que utilizan la librería `psutil` para interactuar con el sistema operativo y recolectar métricas de CPU, RAM, Disco, Red y Procesos.
*   **Persistencia (PostgreSQL):** Base de datos relacional configurada con un enfoque **ROLAP** (Procesamiento Analítico en Línea Relacional).
*   **Visualización (Grafana):** Dashboards construidos mediante consultas SQL nativas.
*   **Infraestructura (Linux/systemd):** Configuración del script de Python como un servicio nativo (`systemd`) para garantizar su ejecución ininterrumpida en segundo plano.

## 🏗️ Decisiones de Diseño y Almacenamiento (PostgreSQL)
Dado el entorno de recursos limitados de la máquina virtual (solo 2GB de RAM), se rechazó el uso de bases de datos NoSQL o esquemas en estrella pesados, optando por una **solución mixta de particionamiento dinámico**:

1.  **Agrupación Inteligente:** En lugar de crear una tabla por métrica (generando redundancia de timestamps), las métricas se agrupan por frecuencia de muestreo:
    *   `metrics_perf` (10-15s): CPU global, RAM, Swap y tráfico de red.
    *   `metrics_cpu_cores` (10-15s): Carga desagregada por cada núcleo virtual
    *   `metrics_top_procs` (60s): Ranking de los procesos más pesados.
    *   `metrics_system_state` (60s): Uptime, conexiones TCP, file descriptors.
    *   `metrics_storage` (5 min): IOPS y ocupación de particiones de disco.
2.  **Particionamiento Automático (Rotación):** Se implementaron funciones SQL (`rotate_partitions.sql`) ejecutadas vía *crontab* que utilizan `PARTITION BY RANGE`. El sistema crea automáticamente las particiones del día siguiente y elimina las de hace dos días, manteniendo un tamaño de base de datos predecible y constante.

## 📂 Estructura de Directorios

*   **`ScriptsPython/`**: Contiene la lógica modular del agente recolector (`collectors`, `metrics`, `scheduler`).
*   **`ScriptsSQL/`**: Archivos `.sql` para la definición del esquema, roles y los procedimientos almacenados de rotación de particiones.
*   **`dependencias.txt`**: Librerías necesarias para ejecutar los scripts (`psutil`, adaptadores de base de datos).
*   **`ESI_P1_Grupo16.pdf`**: Cuaderno de bitácora completo con el análisis de cada métrica elegida y las queries SQL utilizadas en Grafana.

## 👥 Autores
Desarrollado como proyecto de la asignatura *Evaluación de Sistemas Informáticos* (Universidad de Valladolid) por el Grupo 16:
*   Álvaro López Primo
*   Edgar Santiesteban Mendo
*   Marcos Álvarez Fulconis