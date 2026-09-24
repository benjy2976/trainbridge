# Contrato HTTP consumido

## Propósito, alcance y límite de evidencia

Este documento describe las solicitudes que el worker realiza a un servidor externo. TrainBridge no
expone endpoints HTTP ni es la autoridad del contrato servidor. Métodos, rutas, headers y cuerpos
enviados están confirmados por `runner.py`; códigos de respuesta, schemas completos, autorización,
idempotencia y efectos internos del servidor quedan `NOT_EVALUATED` porque su implementación y sus
pruebas no están en este repositorio.

La API directa futura mencionada en README no está implementada y no forma parte de este contrato.

## Convenciones transversales

- URL base: `REVIEW_URL`, sin versión explícita observable.
- Autenticación enviada: header `X-Auth-Token` con `REVIEW_TOKEN` en todas las operaciones.
- JSON: jobs y reportes de estado; encoding generado por `json.dumps`.
- Binario: dataset recibido como tar gzip y modelo enviado como `application/gzip`.
- Timeout: 60 segundos por defecto.
- Errores: `urllib` genera excepciones; no hay schema remoto confirmado.

## Índice de operaciones

| Método | Ruta | Acceso | Tipo | Rol | Ciclo | Concepto | Propietario | Ruta canónica | Propósito | Decisión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/train/jobs/siguiente` | Token | consulta | cliente externo | Sin identidad local | Selección de job | Servidor externo | `NOT_EVALUATED` | Obtener el siguiente job | Resultado calculado; posible claim remoto no evaluado |
| GET | `/api/export` | Token | consulta | cliente externo | Instantánea efímera | Exportación de dataset | Servidor externo | `NOT_EVALUATED` | Descargar dataset actual | El resultado no tiene identidad expuesta |
| POST | `/api/train/jobs/{job_id}/estado` | Token | acción | contextual | Depende del job remoto | Reporte de progreso | Servidor externo | `NOT_EVALUATED` | Reportar estado o error | POST expresa transición/progreso no modelado aquí como CRUD |
| POST | `/api/model?campana={campana}` | Token | acción | cliente externo | Crea entrega remota no identificada | Entrega de modelo | Servidor externo | `NOT_EVALUATED` | Subir paquete OpenVINO | La respuesta no expone un recurso canónico al worker |

## Aplicabilidad CRUD

No aplica una matriz CRUD: las operaciones detectadas son consultas y acciones contra conceptos
propiedad de otro sistema. Determinar recursos canónicos, CRUD omitido y autoridad de mutación exige
revisar el repositorio servidor.

## Trazabilidad del registro

No hay routers locales. Las rutas se construyen como `REVIEW_URL` más el literal de `api_request`
en `runner.py`. Prefijos de proxy, reescritura, versionado y montaje del servidor son
`NOT_EVALUATED`.

## `GET /api/train/jobs/siguiente`

**Propósito:** obtener un objeto `job` o indicar que no hay trabajo disponible.

- Request: sin body; header `X-Auth-Token`.
- Respuesta consumida: JSON con clave `job`; puede ser `null`.
- Campos que usa el worker: `id`, `campana`, `epochs` y `modelo_base`.
- Efectos e idempotencia: `NOT_EVALUATED`; el nombre sugiere selección y podría reclamar el job,
  pero el cliente no demuestra esa semántica.
- Recuperación local: errores de red se registran y el loop vuelve a consultar.
- Pruebas de contrato: no existen en este repositorio.

## `GET /api/export`

**Propósito:** descargar la instantánea del dataset usada por el job que se está ejecutando.

- Request: sin body; header `X-Auth-Token`.
- Respuesta consumida: stream tar gzip; Content-Type y estados no se validan localmente.
- Efecto local: extracción temporal y reemplazo de `datasets/<campana>/<job-id>/`.
- Integridad remota, tamaño máximo y reintentos: `NOT_EVALUATED`.
- Validación posterior: `dataset.yaml` y las cuatro carpetas YOLO obligatorias.

## `POST /api/train/jobs/{job_id}/estado`

**Propósito:** reportar progreso, resultado o error del trabajo remoto.

- Path: `job_id`, validado como segmento seguro en el flujo principal.
- Body JSON: combinación de `estado` y campos como `mensaje`, `epoca_actual`, `epocas_totales`,
  `detalle` o `error` según el punto del flujo.
- Respuesta: el body no se consume; los estados HTTP aceptados son `NOT_EVALUATED`.
- Reintento: no automático. El error se registra y el trabajo continúa para no ocultar la causa
  original.
- Estados emitidos por el cliente: ver `context.md`.

## `POST /api/model?campana={campana}`

**Propósito:** entregar al servidor externo el paquete exportado del trabajo.

- Query: `campana`, validada previamente como segmento seguro.
- Header propio: `Content-Type: application/gzip`, además del token.
- Body: tar gzip con el contenido del directorio exportado.
- Respuesta: se exige que la solicitud termine sin excepción; body y schema no se consumen.
- Idempotencia, límites de tamaño e identidad del modelo recibido: `NOT_EVALUATED`.
- Efecto local: ninguno después de construir y borrar el archivo temporal de transferencia.

## Compatibilidad y pruebas pendientes

No existe OpenAPI, cliente generado ni prueba de contrato local. Antes de cambiar rutas, nombres de
campos o semántica se debe inspeccionar el servidor propietario y coordinar compatibilidad. Como
mínimo faltan pruebas para autenticación negativa, schemas de job, errores HTTP, timeouts,
idempotencia de reportes y subida repetida.
