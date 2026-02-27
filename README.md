# ESI
Prácticas de Evaluación de Sistemas Informáticos del grupo 16
## 🚀 Configuración del Entorno de Desarrollo

Este proyecto utiliza **Python 3.10.12** y se gestiona con [**uv**](https://astral.sh/uv/), un administrador de paquetes ultra rápido que garantiza que todos tengamos las mismas versiones que en la VM de producción.

### 1. Instalación de `uv`
Si aún no tienes `uv` instalado, ejecúta el comando correspondiente a tu sistema operativo:

* **macOS / Linux:**
    ```bash
    curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
    ```
* **Windows (PowerShell):**
    ```powershell
    powershell -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
    ```

### 2. Preparar el Proyecto
Una vez clonado el repositorio, entra en la carpeta y ejecuta:

```bash
uv sync
### 4. Salir o desactivar el entorno
Dependiendo de cómo estés trabajando, puedes salir del entorno virtual así:

* **Si entraste con `uv shell`:**
    ```bash
    exit
    ```
* **Si activaste el entorno manualmente:**
    ```bash
    deactivate
    ```
* **Si usas `uv run`:** No es necesario hacer nada. `uv` gestiona la activación y desactivación automáticamente por cada comando.
