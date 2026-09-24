---
applyTo: "**/*.py"
---

# Instrucciones de la capa Python

Aplicar primero `AGENTS.md`. Estas reglas cubren `runner.py`, `inspect_model.py` y las pruebas
Python; las reglas funcionales del worker viven en `context.md`.

## Alcance y límites

- Mantener los entrypoints ligeros y diferir imports pesados de PyTorch, Ultralytics y OpenVINO
  hasta que la operación los necesite.
- Usar `pathlib.Path` para rutas locales y validar todo valor remoto antes de convertirlo en un
  segmento de ruta.
- Mantener los artefactos bajo las raíces definidas en `runner.py`; no escribir datasets, runs ni
  modelos en la raíz del repositorio.
- No registrar tokens ni cuerpos que puedan contener imágenes o datos privados.
- Añadir dependencias solo en `requirements.txt`, con versión fija cuando afecten la
  reproducibilidad de entrenamiento o exportación.

## Manejo de errores y red

- Configurar timeout en toda solicitud saliente.
- Un fallo de reporte no debe ocultar el error original del entrenamiento.
- Las operaciones que reemplazan directorios deben validar campaña e ID de trabajo antes de
  borrar o mover contenido.
- No asumir el contrato del servidor remoto más allá de la evidencia local de `docs/api.md`.

## Preflight adicional

- Identificar si el cambio afecta el flujo del trabajo, el contrato HTTP, la CLI o la estructura
  de artefactos.
- Leer `context.md` y las fuentes normativas correspondientes.

## Validaciones de cierre

- Ejecutar `.venv/bin/python -m unittest discover -s tests -v` en Linux/WSL2.
- En Windows usar `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- Ejecutar pruebas específicas adicionales cuando cambien red, entrenamiento o exportación; los
  tests unitarios actuales no cubren esos flujos con las librerías reales.
