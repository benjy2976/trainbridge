# Procedimientos del proyecto

## Propósito y precondiciones

Estos procedimientos se ejecutan desde la raíz del repositorio. Los requisitos y variables viven
en `docs/entorno.md`. Ningún comando autoriza consultar un servidor real, publicar modelos o borrar
artefactos fuera del alcance solicitado.

## Preparar el entorno

### Linux o WSL2

```bash
bash scripts/01_setup_env.sh
```

### Windows PowerShell

```powershell
powershell -File scripts\windows\01_setup_env.ps1
```

Los scripts crean `.venv`, actualizan `pip`, instalan `requirements.txt` y muestran si PyTorch ve
CUDA. El criterio de éxito para entrenamiento es `CUDA disponible: True` y el nombre de la GPU. Si
la instalación termina pero CUDA no está disponible, seguir `SOLUCION_CUDA.md` antes de entrenar.

Crear la configuración sin exponerla:

```bash
cp .env.example .env
```

Completar `REVIEW_URL` y `REVIEW_TOKEN` localmente. No imprimir el token ni versionar `.env`.

## Ejecutar y detener el worker

Linux o WSL2:

```bash
bash scripts/02_run_worker.sh
```

Windows:

```powershell
powershell -File scripts\windows\02_run_worker.ps1
```

El proceso consulta la cola cada cinco segundos y permanece en primer plano. El arranque correcto
muestra la URL configurada y queda esperando trabajos. Detenerlo con `Ctrl+C`; no existe servicio
de sistema ni healthcheck versionado.

## Recuperar una corrida ya entrenada

Usar este procedimiento cuando existen el dataset de la ejecución y
`runs/<campana>/<job-id>/weights/best.pt`, pero falló validación, exportación o subida:

```bash
.venv/bin/python runner.py --finalizar-job <campana> <job-id>
```

En Windows sustituir el ejecutable por `.venv\Scripts\python.exe`. El comando vuelve a validar,
reutiliza la exportación OpenVINO si existe, reconstruye el paquete, lo sube y reporta `listo`. Tiene
efectos remotos y requiere autorización para usar el servidor configurado. Si falla, conserva el
checkpoint; corregir la causa y reintentar es seguro para los artefactos locales del mismo job.

## Inspeccionar un modelo OpenVINO

```bash
.venv/bin/python inspect_model.py \
  modelos/exportados/<campana>/<job-id>/<modelo>.xml
```

El comando es de lectura y muestra forma, dtype, layout y un bloque orientativo para Frigate. La
asunción `rgb` requiere validación al desplegar.

## Sincronizar el código a otro equipo

Para enviar el proyecto sin copiar entorno, secretos ni artefactos locales:

```bash
rsync -avz \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.env' \
  --exclude 'datasets/*' \
  --exclude 'runs/' \
  --exclude 'modelos/' \
  ./ usuario@equipo:/ruta/a/trainbridge/
```

No se usa `--delete`: el comando no borra archivos remotos. `datasets/README.md` queda excluido por
el patrón en este ejemplo; Git debe ser la vía preferida para sincronizar código versionado.

## Validación técnica

| Validación | Comando | Qué demuestra |
| --- | --- | --- |
| Tests Python | `.venv/bin/python -m unittest discover -s tests -v` | Helpers locales cubiertos |
| Sintaxis Python | `.venv/bin/python -m compileall -q runner.py inspect_model.py tests` | Archivos compilables |
| Markdown | `markdownlint-cli2 "**/*.md" "#.git/**"` | Estilo Markdown global |
| Memoria viva | `scripts/validate-project-memory` | Estructura soportada del estándar |

En Windows usar el Python del venv. No hay CI, formatter, linter Python ni type checker versionados;
esas dimensiones quedan `NOT_EVALUATED` hasta incorporar herramientas y configuración propias.

Para una actualización de la skill, validar además:

```bash
scripts/validate-project-memory --strict --expected-standard-version 1.7.0
```

Si una comprobación falla, corregir y repetir solo ese control salvo que el cambio altere el
resultado global.

## Mantenimiento de memoria

Antes de cambiar una capacidad, inventariar interfaces, capas, módulos, variables y artefactos
afectados. Después del cambio, revisar el diff, repetir el inventario, sincronizar solo las fuentes
normativas exigibles y ejecutar el validador proporcional. En una actualización del estándar se
comparan las versiones, se preservan mejoras locales y se usa el modo estricto indicado arriba.

## Diagnóstico seguro

| Síntoma | Comprobación | Recuperación |
| --- | --- | --- |
| No existe `.venv` | Verificar el directorio sin leer secretos | Ejecutar el setup de la plataforma |
| CUDA no disponible | `.venv/bin/python -c 'import torch; print(torch.cuda.is_available())'` | Seguir `SOLUCION_CUDA.md` |
| Dataset incompleto | Revisar las cuatro carpetas esperadas | Corregir la exportación y encolar otro job |
| Fallo tras entrenar | Comprobar `best.pt` y `dataset.yaml` | Usar `--finalizar-job` |
| Servidor inaccesible | Revisar URL y conectividad sin mostrar token | Corregir entorno y reintentar |

No borrar `.venv`, datasets, runs o modelos como primer paso. Resolver primero la causa y confirmar
el objetivo exacto de cualquier eliminación.
