# Contrato CLI

## Convenciones

- Linux/WSL2: `.venv/bin/python`; Windows: `.venv\Scripts\python.exe`.
- Las CLIs no ofrecen `--help` estructurado ni salida de máquina estable.
- Mensajes normales y diagnósticos se escriben actualmente en `stdout`.
- No hay confirmación interactiva ni modo dry-run.
- Los códigos no documentados producidos por excepciones de librerías no forman un contrato estable.

## Índice

| Comando | Propósito | Efectos |
| --- | --- | --- |
| `runner.py` | Ejecutar el worker continuo | Red y artefactos locales; puede entrenar |
| `runner.py --finalizar-job` | Recuperar y entregar una corrida | Validación, exportación, red y estado remoto |
| `inspect_model.py` | Inspeccionar un XML OpenVINO | Solo lectura |
| Scripts de setup | Crear el entorno Python | Modifica `.venv` e instala paquetes |
| Scripts de worker | Lanzar `runner.py` | Los mismos efectos del worker |

## `runner.py`

```text
python runner.py
```

Requiere `.venv`, `REVIEW_URL` y `REVIEW_TOKEN`. No usa stdin. Permanece en primer plano hasta
`Ctrl+C`, consulta la cola, ejecuta jobs y muestra progreso humano. Un fallo de un job se reporta y
no termina el loop; un error de configuración termina con código `1`.

No existe una prueba automatizada del loop, la red, GPU o interrupción por señal.

## `runner.py --finalizar-job`

```text
python runner.py --finalizar-job <campana> <job-id>
```

| Argumento | Tipo | Requerido | Regla |
| --- | --- | --- | --- |
| `campana` | Texto | Sí | Un segmento ASCII seguro |
| `job-id` | Texto | Sí | Un segmento ASCII seguro |

Requiere `.env`, `.venv`, el dataset y `best.pt` del trabajo. Valida de nuevo el checkpoint,
reutiliza o crea la exportación, reemplaza el paquete exportado, sube el tar y reporta el estado
remoto. No usa stdin ni tiene salida de máquina.

| Código | Significado | Acción |
| --- | --- | --- |
| `0` | Trabajo recuperado y subido | Verificar estado en el sistema solicitante |
| `1` | Falta configuración antes del parsing | Completar `.env` o crear `.venv` |
| `2` | Sintaxis distinta de la forma exacta | Corregir argumentos |
| Otro no cero | Excepción de archivos, librerías, validación o red | Leer diagnóstico y corregir causa |

Repetirlo reemplaza artefactos locales del mismo job y vuelve a intentar la entrega. La idempotencia
del servidor remoto es `NOT_EVALUATED`.

## `inspect_model.py`

```text
python inspect_model.py <ruta-modelo.xml>
```

Recibe exactamente una ruta, no usa stdin y solo lee el modelo. Muestra shape, dtype, layout y un
bloque Frigate. Código `0` indica inspección completada; sin un único argumento termina con `1`.
Errores de lectura o formatos inesperados pueden terminar con otro código no cero.

## Scripts de plataforma

```text
bash scripts/01_setup_env.sh
bash scripts/02_run_worker.sh
powershell -File scripts\windows\01_setup_env.ps1
powershell -File scripts\windows\02_run_worker.ps1
```

Los scripts de setup crean o actualizan `.venv` e instalan `requirements.txt`. Los scripts de
worker validan el Python del venv y reemplazan el proceso o propagan su código. El procedimiento y
los criterios de éxito viven en `docs/procedimientos.md`.

## Pruebas y compatibilidad

`tests/test_runner.py` cubre helpers usados por la CLI, pero no parsing, códigos de salida ni
capturas de salida. Cambiar argumentos, texto consumido por automatizaciones o códigos exige añadir
pruebas específicas y actualizar este contrato.
