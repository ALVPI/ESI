# 🛡️ OAuth2 EDR & Load Testing (Prometheus + Locust)

Este proyecto implementa un sistema de monitorización avanzada y pruebas de carga sobre un servidor de autenticación **OAuth2** (escrito en Python/Flask). 

El objetivo principal ha sido instrumentar el código base para exponer métricas en tiempo real, simular tráfico legítimo y malicioso mediante pruebas de estrés, y construir un panel de control **EDR (Endpoint Detection and Response)** en Grafana capaz de detectar ataques y cuellos de botella.

## 🚀 Tecnologías Utilizadas
*   **Backend:** Python 3.10, Flask, SQLite (Gestión de paquetes con `uv`).
*   **Monitorización:** Prometheus (Base de datos de series temporales *Pull*).
*   **Visualización:** Grafana (Dashboards interactivos mediante *PromQL*).
*   **Pruebas de Carga:** Locust (Simulación de usuarios concurrentes y flujos de tráfico).

## 🔍 Instrumentación y Enfoque EDR
El servidor ha sido modificado siguiendo el principio DRY (centralizando los contadores en `metrics.py` e inyectando decoradores de *middleware* en `app.py`). Se han implementado métricas clave para la seguridad:

*   **Detección de Fuerza Bruta y Credential Stuffing:** Monitorización de intentos fallidos por `client_id` y `username`.
*   **Prevención de Token Replay:** Seguimiento de códigos de autorización pendientes y detección de intentos de uso de *Refresh Tokens* revocados o expirados.
*   **Rendimiento y Saturación:** Histogramas del tiempo de respuesta (Percentil 95) y medidores (gauges) de peticiones HTTP en curso para detectar posibles ataques DoS.

![Panel EDR en Grafana](./Recursos/VistazoGeneralGrafana.png)

## ⚡ Diseño de Pruebas (Locust)
Se diseñó un `locustfile.py` realista que distribuye el tráfico en tres categorías simulando un entorno de producción:
*   **50% Tráfico Legítimo:** Flujos M2M (*Client Credentials*), autenticaciones web (*Authorization Code*) y rotación de *Refresh Tokens*.
*   **45% Tráfico Malicioso (Ataques):** Inyección controlada de fuerza bruta a APIs, recolección de tokens (*Token Harvesting*), enumeración de clientes y reutilización de códigos interceptados.
*   **5% Monitorización:** Peticiones a endpoints de administración interna.

### Resultados del Análisis de Estrés
Durante las pruebas de estrés escalonadas (de 10 a 200 usuarios concurrentes), se identificó un **cuello de botella de concurrencia** en el servidor de desarrollo de Flask (límite operativo estable: ~10 usuarios concurrentes / 12 RPS antes de degradar el SLA de 250ms), causado por la ejecución síncrona monohilo durante las operaciones criptográficas de los tokens. El dashboard EDR diferenció exitosamente los falsos positivos de los ataques reales de *Credential Stuffing*.

![Prueba de Carga en Locust](./Recursos/CargaNormal.png)

## 📂 Documentación
*   📄 **[Memoria Técnica Completa (PDF)](./docs/ESI_P2_G16.pdf)**: Análisis detallado de las métricas PromQL, capturas del dashboard y flujos de ejecución.
*   📊 **[Presentación del Proyecto (PDF)](./docs/Presentacion.pdf)**.

## 👥 Autores
Desarrollado como proyecto de la asignatura *Evaluación de Sistemas Informáticos* (Universidad de Valladolid) por el Grupo 16:
*   Álvaro López Primo
*   Edgar Santiesteban Mendo
*   Marcos Álvarez Fulconis