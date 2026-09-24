# Guía para agentes de IA

## Propósito

Este documento dirige a personas y agentes hacia la fuente normativa correcta. El protocolo
operativo completo vive en `AGENTS.md`.

## Adopción del estándar

- Skill adoptada: `gestionar-memoria-viva-proyecto`.
- Versión adoptada: `1.7.0`.
- Fecha de revisión: `2026-09-24`.
- Versión anterior: no aplica; esta es la inicialización del estándar.

La copia local no se actualiza automáticamente desde la skill externa.

## Mapa de fuentes normativas

| Pregunta | Fuente principal |
| --- | --- |
| ¿Cómo trabajar en el repositorio? | `AGENTS.md` |
| ¿Cómo se compone TrainBridge? | `docs/arquitectura.md` |
| ¿Qué prácticas técnicas se usan? | `docs/convenciones.md` |
| ¿Cómo se instala, ejecuta o valida? | `docs/procedimientos.md` |
| ¿Qué necesita el entorno? | `docs/entorno.md` |
| ¿Qué HTTP consume el worker? | `docs/api.md` |
| ¿Qué comandos propios existen? | `docs/cli.md` |
| ¿Qué reglas gobiernan un trabajo? | `context.md` |
| ¿Cómo se gobiernan recursos de agentes? | `docs/memoria-viva/resource-efficiency.md` |

`docs/modelo-datos.md` y `docs/frontend.md` no existen porque este repositorio no implementa una
base de datos ni una interfaz frontend. Los archivos ignorados de datasets, runs y modelos son
artefactos del filesystem, no entidades persistentes gobernadas por un schema.

## Flujos críticos

| Flujo | Riesgo que se preserva | Fuente normativa | Verificación |
| --- | --- | --- | --- |
| Tomar y ejecutar un trabajo | No mezclar campañas ni trabajos | `context.md` | `tests/test_runner.py` y prueba controlada |
| Exportar y entregar un modelo | Entregar layout, clases y procedencia coherentes | `context.md` | Inspección OpenVINO y metadatos |
| Recuperar una corrida | No repetir entrenamiento ya terminado | `docs/cli.md` | Comando `--finalizar-job` |
| Preparar CUDA | Evitar una build incompatible de PyTorch | `docs/entorno.md` | `docs/procedimientos.md` |

## Contextos de módulos

- TrainBridge worker: `context.md` — gobierna el ciclo de vida local de los trabajos remotos.

## Instrucciones por capa

- Python: `.github/instructions/python.instructions.md` — reglas para worker, inspección y tests.

## Evidencia y contradicciones

Confirmar afirmaciones contra código, configuración, pruebas e historial pertinente. Distinguir
comportamiento implementado, decisión futura, hipótesis y contradicción. Si dos fuentes normativas
difieren y ninguna tiene prioridad clara, detener la edición afectada y consultar al operador.

No leer `.env`, datasets, modelos ni imágenes para completar documentación. No consultar el
servidor remoto sin autorización explícita.

## Cierre

Comparar capacidades antes y después, revisar el diff, sincronizar las fuentes afectadas y ejecutar
las validaciones proporcionales definidas en `docs/procedimientos.md`. Un validador limpio no
sustituye la revisión semántica ni confirma áreas declaradas `NOT_EVALUATED`.
