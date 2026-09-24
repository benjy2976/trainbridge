# Contexto: por qué existe este proyecto

Este archivo es autocontenido a propósito -- a diferencia del resto de la
documentación del proyecto `smarthome` (donde el detalle completo vive en
`docs/decisions/`), esta carpeta se copia entera a un equipo con GPU que no
tiene ese repo. Acá va el resumen que hace falta para entender el "por qué"
sin necesitar el resto del árbol de `smarthome`. El registro canónico y
completo, si tenés acceso a ese repo, es ADR-0026, en el NUC bajo
`docs/decisions/0026-detector-propio-afinado-con-gpu-externa.md`.

## El problema

Frigate (el NVR que corre en el NUC de la vivienda) usa por defecto
`ssdlite_mobilenet_v2`, un detector genérico y liviano entrenado sobre
COCO. En canal_3 confundía sistemáticamente al gato de la casa con una
persona -- con score de confianza tan alto (0.86-0.97) como un acierto
real, así que subir el umbral no separaba un caso del otro. Tampoco lo
hacía filtrar por área de la caja: dependiendo de qué tan cerca de la
cámara estuviera el gato, su caja podía ser más grande que la de una
persona real al fondo de la escena. El resultado práctico: una
automatización que encendía la luz de la sala "por persona" terminaba
encendiéndose por el gato, y tuvo que deshabilitarse manualmente.

Evaluamos ajustes de configuración (umbral, área, máscara de zona) y un
servicio pago (Frigate+) antes de descartarlos -- ninguno resolvía el
problema de raíz o no aportaba ventaja real teniendo ya GPU propia
disponible.

## La decisión

Entrenar un detector YOLO propio por transfer learning (parte de pesos ya
entrenados en COCO, no aprende a detectar objetos desde cero) usando
imágenes reales de las propias cámaras, corregidas a mano. Se entrena acá,
en el equipo con GPU, y se exporta a OpenVINO para correr en la NPU del
NUC, reemplazando al detector genérico de Frigate.

El equipo con GPU puede ser Linux, Windows con WSL2, o Windows nativo sin
WSL -- las GPU disponibles están en equipos Windows, así que los tres
caminos están igual de detallados (`scripts/*.sh` para Linux/WSL2,
`scripts\windows\*.ps1` para Windows nativo, ver `README.md`).

Alcance ampliado a las 5 cámaras de la vivienda (no solo la del gato),
porque entre todas usan un conjunto acotado de clases -- hoy: `person`,
`car`, `motorcycle`, `cat`, `trimovil`, `camioneta`, `camion` (las 4
primeras ya existen en COCO; las últimas 3 se agregaron después, específicas
del contexto local).

## De dónde salen los datos

En el NUC (`vision-training/deteccion-objetos/`, código versionado; los
datos que produce ni viven dentro del repo, están en
`/srv/vision-training-data/deteccion-objetos/`, porque contienen
imágenes reales de la vivienda -- ver ADR-0028):

1. `harvest.py` descarga eventos ya grabados por Frigate y saca hasta 3
   frames por evento (usando `path_data`, la trayectoria del objeto, para
   que la caja de cada frame corresponda a donde el objeto está *en ese
   instante*, no a una caja fija reciclada). La etiqueta de cada frame es
   la que Frigate ya calculó -- **candidata, no verdad**, porque el
   detector actual es justo el que se está corrigiendo.
2. Una herramienta de revisión web (`herramienta_revision/`, corre en el
   NUC) permite corregir la clase y/o redibujar las cajas de cada evento a
   mano.
3. `export_dataset.py` arma el layout final (train/val, separado por
   evento para que no haya fuga de datos entre frames de un mismo evento).

## El flujo recursivo (por qué esto no es "una sola corrida")

La idea no es esperar a revisar los ~3.700 frames cosechados antes de
entrenar nada. Con una porción ya revisada, se entrena un primer modelo
intermedio -- aunque imperfecto, sugiere cajas mejor que partir de cero, lo
que **acelera** la revisión manual de lo que falta (menos dibujar cajas
desde cero, más corregir sugerencias). A medida que se revisa más, se
vuelve a entrenar con el conjunto ampliado, y así sucesivamente.

Por eso el dataset y el modelo viajan por HTTP entre el NUC y este equipo
(en vez de copiarse a mano una sola vez): `runner.py` descarga siempre el
estado más reciente de lo revisado al empezar cada trabajo, y devuelve el
modelo entrenado al terminar. Ver el `README.md` de esta carpeta para el
paso a paso concreto.

Como las GPU disponibles están repartidas en varios equipos (no siempre el
mismo, no siempre prendido), `runner.py` lleva esa idea un paso más allá:
en vez de correr los scripts a mano en cada ciclo, es un worker que hace
polling al NUC por trabajos encolados desde un botón en la herramienta web
-- cualquier equipo que lo tenga corriendo puede tomar el próximo trabajo,
como un "vientre de alquiler" intercambiable. Ver
[el contexto normativo local](context.md#estados-emitidos-y-flujo).

## Qué NO resuelve este proyecto (todavía)

- No incluye reconocimiento facial ni re-identificación de personas entre
  cámaras -- esa es una iniciativa hermana, separada, explorada en el
  árbol de `smarthome` pero pausada mientras se afina este detector.
- El despliegue final en Frigate (copiar el modelo exportado, editar
  `config.yml`, validar en producción) es un paso manual y deliberadamente
  no automatizado -- se hace primero solo en canal_3, contra los casos ya
  conocidos, antes de replicar a las otras cámaras.
