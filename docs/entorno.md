# Entorno de desarrollo y ejecución

## Perfiles soportados

| Perfil | Propósito | Diferencias | Estado |
| --- | --- | --- | --- |
| Linux nativo | Entrenar con GPU NVIDIA | Scripts Bash | Soportado |
| WSL2 | Entrenar desde un host Windows | Passthrough NVIDIA; preferir filesystem WSL | Soportado |
| Windows nativo | Entrenar sin WSL | Scripts PowerShell y rutas del venv Windows | Soportado |
| Tests locales sin GPU | Validar helpers y documentación | No ejecuta entrenamiento real | Soportado parcialmente |

No existe configuración de producción automatizada ni contenedores en este repositorio.

## Requisitos

| Herramienta | Versión | Obligatoria | Uso | Evidencia |
| --- | --- | --- | --- | --- |
| Python | 3.x compatible con los pines | Sí | Runtime y venv | Scripts de setup |
| `pip` y `venv` | Incluidos con Python | Sí | Instalación aislada | Scripts de setup |
| Driver NVIDIA | Compatible con CUDA 12.8 | Para entrenar con GPU | PyTorch CUDA | `SOLUCION_CUDA.md` |
| `rsync` | Sin versión fijada | Solo para copia manual | Sincronización opcional | README |
| PowerShell | Sin versión fijada | En Windows nativo | Scripts `.ps1` | `scripts/windows/` |

Las versiones Python y de herramientas del host no están fijadas. Las dependencias Python sí están
fijadas en `requirements.txt`.

## Servicios

| Servicio | Propósito | Dirección segura de ejemplo | Inicio | Salud |
| --- | --- | --- | --- | --- |
| Servidor de revisión y cola | Entrega jobs/datasets y recibe progreso/modelos | `http://nuc.example.test:8850` | Fuera del repo | No hay healthcheck local |

TrainBridge no abre un puerto. El operador debe autorizar cualquier consulta al servicio real.

## Variables de entorno

| Variable | Propósito | Obligatoria | Ejemplo seguro | Fuente |
| --- | --- | --- | --- | --- |
| `REVIEW_URL` | URL base del servidor externo | Sí al ejecutar | `http://nuc.example.test:8850` | `.env.example`, `runner.py` |
| `REVIEW_TOKEN` | Autenticar solicitudes salientes | Sí al ejecutar | `change-me` | `.env.example`, `runner.py` |

`REVIEW_TOKEN` es secreto. Se administra en `.env` local y nunca debe aparecer en logs, comandos,
capturas ni commits. `load_env` no reemplaza variables ya definidas en el proceso.

## Archivos de configuración

| Archivo | Propósito | Versionado | Secretos | Fuente |
| --- | --- | --- | --- | --- |
| `.env.example` | Plantilla portable | Sí | No | Repositorio |
| `.env` | Configuración real del worker | No | Sí | Copia local de `.env.example` |
| `requirements.txt` | Dependencias reproducibles | Sí | No | Repositorio |
| `dataset.yaml` | Clases y splits de un job | No | Puede describir datos reales | Dataset descargado |

## Rutas de runtime

Todas se resuelven desde la raíz de `runner.py`, no desde el directorio actual:

| Ruta | Contenido | Versionada |
| --- | --- | --- |
| `.venv/` | Entorno Python | No |
| `datasets/<campana>/<job-id>/` | Instantánea exacta del dataset | No |
| `runs/<campana>/<job-id>/` | Checkpoints y validación | No |
| `modelos/base/` | Pesos descargados | No |
| `modelos/exportados/<campana>/<job-id>/` | Paquete OpenVINO y metadatos | No |

## Diferencias y límites conocidos

| Aspecto | Linux/WSL2 | Windows | Impacto |
| --- | --- | --- | --- |
| Python del venv | `.venv/bin/python` | `.venv\Scripts\python.exe` | Cambia el comando, no la lógica |
| Lanzador | Bash | PowerShell | Mantener ambos al cambiar setup o arranque |
| Rendimiento WSL2 | Mejor dentro del filesystem Linux | No aplica | `/mnt/c` o `/mnt/d` puede penalizar E/S |

La compatibilidad real de entrenamiento y exportación debe comprobarse al actualizar PyTorch,
Ultralytics u OpenVINO; los tests unitarios no cargan esos stacks.
