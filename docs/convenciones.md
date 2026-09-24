# Convenciones del proyecto

## Propósito y evidencia

Estas reglas transversales se derivan de `runner.py`, `inspect_model.py`, los scripts, las pruebas y
los manifests actuales. Las reglas exclusivas de Python viven en
`.github/instructions/python.instructions.md`; el comportamiento funcional, en `context.md`.

## Idioma y nombres

| Elemento | Convención | Evidencia |
| --- | --- | --- |
| Documentación, mensajes y comentarios | Español | README y código actuales |
| Archivos y funciones Python | `snake_case` | `runner.py`, `inspect_model.py` |
| Constantes Python | `UPPER_SNAKE_CASE` | Constantes de rutas y red en `runner.py` |
| Clases de tests | `PascalCase`; métodos `test_*` | `tests/test_runner.py` |
| Campaña e ID de trabajo | Un segmento ASCII seguro | `validar_segmento` |

Conservar los nombres públicos existentes aunque mezclen español y términos técnicos del contrato,
como `job_id` y `map50`. Un renombre público requiere revisar compatibilidad.

## Organización y dependencias

- `runner.py` orquesta cola, archivos, entrenamiento, exportación y entrega.
- `inspect_model.py` encapsula la lectura de un modelo OpenVINO y puede usarse como CLI.
- `scripts/` solo adapta preparación y arranque por plataforma; no duplica la lógica del worker.
- `tests/` usa la biblioteca estándar `unittest` y dobles locales; no debe llamar a red ni GPU.
- Las dependencias se fijan en `requirements.txt`. PyTorch y TorchVision conservan una pareja y una
  build CUDA compatibles; Ultralytics se actualiza deliberadamente junto con pruebas de exportación.

La estructura es deliberadamente plana mientras exista un solo módulo funcional. Una división en
paquete requiere una responsabilidad nueva y actualización de arquitectura, imports y entrypoints.

## Funciones, efectos y errores

- Validar entradas remotas en la frontera antes de construir rutas.
- Usar rutas relativas a `ROOT`; no depender del directorio desde el que se invoca el proceso.
- Mantener funciones pequeñas para cada etapa observable y conservar contexto en los errores.
- No capturar errores para ignorarlos. El loop puede aislar un trabajo fallido, pero debe reportarlo
  y continuar disponible para la cola.
- Los imports pesados son diferidos para permitir que el worker arranque y diagnostique su entorno.

## Seguridad y datos sensibles

- `REVIEW_TOKEN` es secreto y solo vive en `.env`, que está ignorado.
- `.env.example` usa valores ficticios y nunca contiene hosts privados reales ni tokens funcionales.
- Todas las solicitudes salientes incluyen timeout y el token en `X-Auth-Token`.
- Campaña, ID de trabajo y nombre de modelo se validan contra un único segmento antes de tocar el
  filesystem.
- Datasets, runs y modelos pueden contener datos o artefactos grandes; están ignorados y no se usan
  como fixtures versionados.

El worker autentica sus solicitudes, pero la autorización efectiva la decide el servidor remoto y
no puede comprobarse desde este repositorio.

## Consistencia de artefactos

Los artefactos se agrupan por campaña e ID de trabajo:

```text
datasets/<campana>/<job-id>/
runs/<campana>/<job-id>/
modelos/exportados/<campana>/<job-id>/
```

El dataset se extrae primero a un directorio temporal y luego reemplaza la instantánea del trabajo.
La exportación final también reemplaza su directorio de destino. No se promete exclusión mutua
entre dos procesos sobre el mismo trabajo; evitar ejecutarlos concurrentemente.

## Diseño HTTP consumido

TrainBridge no expone HTTP actualmente: consume un contrato de otro sistema. Cada operación se
clasifica en `docs/api.md`. No convertir esas rutas en una API propia ni declarar autoridad de
mutación del servidor sin revisar su repositorio.

- Base URL configurable mediante `REVIEW_URL`; las rutas observadas comienzan por `/api`.
- JSON se usa para trabajos y progreso; dataset y modelo viajan como archivos tar comprimidos.
- Las consultas y acciones remotas no se presentan como CRUD canónico sin evidencia del servidor.
- La futura API receptora mencionada en README es dirección de producto, no capacidad actual.

## Pruebas

| Cambio | Cobertura mínima | Ubicación o comando |
| --- | --- | --- |
| Rutas y estructura del dataset | Casos válido e incompleto | `tests/test_runner.py` |
| Segmentos del filesystem | Entradas de escape rechazadas | `tests/test_runner.py` |
| Labels o modelo base | Resultado y migración local | `tests/test_runner.py` |
| HTTP, entrenamiento o exportación | Prueba controlada adicional | Aún no automatizada |

Las pruebas unitarias deben usar directorios temporales y mocks. No requieren GPU, red ni secretos.

## Documentación y commits

- Mantener una fuente normativa por conocimiento y enlazarla en vez de duplicarla.
- Documentar decisiones futuras como futuras, no como implementadas.
- Usar ejemplos ficticios y portables.
- Para cambios nuevos, preferir Conventional Commits, por ejemplo
  `docs(memory): initialize living project documentation`.
- Mantener cada commit revisable y no incluir `.env`, datasets, runs, modelos ni `.venv`.

## Calidad y cierre

Ejecutar los tests proporcionales, Markdownlint y el validador descritos en
`docs/procedimientos.md`. Revisar manualmente secretos, rutas, errores, documentación y archivos sin
uso; las herramientas actuales no incluyen formatter, linter Python ni análisis estático.
