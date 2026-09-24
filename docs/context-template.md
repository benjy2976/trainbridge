# Plantilla de contexto de módulo

Usar esta plantilla cuando aparezca una capacidad funcional cohesiva con reglas, actores, estados o
flujo propios. No crear un contexto para una carpeta puramente técnica. Sustituir las indicaciones
de cada sección por evidencia real y eliminar las secciones opcionales que no apliquen.

## Propósito y alcance de la plantilla

El contexto de un módulo explica qué resultado produce, qué comportamiento debe preservar y por qué.
Es la fuente normativa para su vocabulario, actores, permisos, estados, reglas y decisiones.

No debe duplicar contratos HTTP o CLI, campos persistidos, arquitectura global ni procedimientos.
Debe enlazar esas fuentes y resumir solo lo necesario para comprender el módulo.

## Evidencia que se debe consultar

- Casos de uso, servicios, handlers y políticas del módulo.
- Modelos, artefactos o mensajes que materializan sus conceptos.
- Rutas HTTP, comandos, eventos o jobs visibles.
- Pruebas, fixtures seguros y escenarios de aceptación.
- Documentación e historial pertinentes cuando expliquen una decisión vigente.

Si las fuentes se contradicen, registrar el conflicto y resolverlo antes de presentar una regla como
confirmada.

## Estructura que se copia al módulo

El archivo resultante se llama `context.md`, comienza con `# Contexto: nombre del módulo` y conserva
las siguientes secciones adaptadas.

### Propósito

Explicar en una o dos oraciones quién obtiene valor y qué resultado observable produce el módulo.

### Alcance y límites

Indicar capacidades incluidas, exclusiones explícitas y dependencias funcionales. Distinguir
claramente lo actual de lo planeado.

### Vocabulario

| Término | Significado en el módulo | No confundir con |
| --- | --- | --- |
| Ejemplo seguro | Significado específico respaldado por evidencia | Concepto parecido |

Conservar solo palabras cuyo significado local no sea obvio.

### Actores y permisos

| Actor o rol | Puede | No puede | Evidencia |
| --- | --- | --- | --- |
| Actor ficticio | Acción autorizada | Límite explícito | Política o prueba local |

Distinguir autenticación, autorización y propiedad. Si una dimensión no puede comprobarse, marcarla
`NOT_EVALUATED` y explicar qué evidencia falta.

### Entidades o estado relevantes

Resumir el papel de las entidades persistentes, artefactos, mensajes o estado efímero. Enlazar
`docs/modelo-datos.md` cuando exista; no copiar sus campos.

### Estados y transiciones

| Origen | Evento | Condición | Destino | Efecto |
| --- | --- | --- | --- | --- |
| Estado inicial | Acción observable | Regla verificable | Estado final | Resultado |

Agregar un diagrama cuando existan tres o más estados o bifurcaciones importantes.

### Reglas de negocio

Enumerar reglas que puedan convertirse en pruebas: condición, comportamiento, excepción y evidencia.
Evitar instrucciones vagas como “validar correctamente”.

### Flujo e interfaces

Enlazar entradas HTTP, CLI, eventos o jobs; describir la secuencia principal, la salida y las
integraciones. Usar un diagrama cuando participen tres o más componentes.

### Errores y recuperación

| Situación | Comportamiento esperado | Mensaje o código | Recuperación |
| --- | --- | --- | --- |
| Fallo representativo | Resultado observable | Referencia estable | Acción segura |

Separar errores de entrada, reglas de negocio, concurrencia y fallos técnicos. Indicar si el
reintento es seguro.

### Pruebas mínimas

Documentar camino principal, autorización cuando aplique y transición o excepción crítica. Cada
caso debe indicar precondición, acción y resultado, sea automatizado o manual.

### Decisiones recientes

| Fecha | Decisión | Motivo | Consecuencia |
| --- | --- | --- | --- |
| Fecha verificable | Decisión vigente | Razón | Impacto actual |

Conservar solo decisiones no obvias que sigan condicionando el módulo.

## Cierre de un cambio de módulo

1. Comparar propósito, actores, estados, reglas e interfaces antes y después.
2. Actualizar el contexto y su índice en `docs/guia_IA.md`.
3. Sincronizar contratos o modelo de datos únicamente si también cambiaron.
4. Ejecutar pruebas del módulo y `scripts/validate-project-memory`.
5. Confirmar que no quedaron marcadores genéricos ni conocimiento duplicado.
