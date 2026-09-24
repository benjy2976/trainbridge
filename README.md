# TrainBridge

Runner autohospedado para ejecutar trabajos de entrenamiento de machine
learning en equipos remotos, con transferencia de datasets, seguimiento de
progreso, validación, exportación y entrega de modelos.

Actualmente TrainBridge funciona como un worker que consulta una cola HTTP y
está especializado en detección de objetos con Ultralytics y exportación a
OpenVINO. La dirección futura del proyecto es admitir también solicitudes
directas mediante una API y otros tipos de trabajos de entrenamiento, sin
quedar ligado a un proyecto consumidor concreto.

## Documentación del proyecto

- [Arquitectura](docs/arquitectura.md): componentes, fronteras y flujo global.
- [Contexto funcional](context.md): estados, reglas y recuperación de trabajos.
- [Entorno](docs/entorno.md) y [procedimientos](docs/procedimientos.md): preparación, ejecución y
  validación.
- [Contrato HTTP consumido](docs/api.md) y [contrato CLI](docs/cli.md): interfaces actuales.
- [Guía para agentes](docs/guia_IA.md): índice de la memoria viva del repositorio.

## Caso de uso actual: detector para Frigate

La primera integración reemplaza `ssdlite_mobilenet_v2` (el modelo por defecto
de Frigate, que confunde al gato de canal_3 con una persona) por un YOLO
afinado con imágenes reales de las 5 cámaras. Para el "por qué" completo (el
problema diagnosticado, las alternativas descartadas, y por qué el flujo es
recursivo) ver [CONTEXTO.md](CONTEXTO.md) -- este README es solo el "cómo".

Pensado para reutilizarse: cada campaña de entrenamiento (esta, y las
futuras cuando se agreguen más clases de objetos) agrupa sus ejecuciones
por ID de trabajo bajo `datasets/`, `runs/` y `modelos/exportados/`; el
mismo `runner.py` sirve para todas. El proceso además
es **recursivo**: no hace falta esperar a revisar todo el dataset cosechado
antes de entrenar -- con lo revisado hasta ahora se entrena un primer
modelo intermedio, que ayuda a revisar más rápido lo que falta (sugiere
cajas en vez de partir de cero), y se vuelve a entrenar con el conjunto
ampliado. Por eso el dataset y el modelo se transfieren por HTTP en vez de
copiarse a mano -- y por eso todo el ciclo se dispara con un botón desde
la herramienta de revisión en vez de correrse a mano en cada ronda (ver
"Cómo funciona" abajo).

## Dónde vive cada cosa

- **NUC** (`vision-training/deteccion-objetos/`, dentro del proyecto
  consumidor): recolección de imágenes desde eventos de Frigate,
  revisión/corrección de etiquetas y exportación del dataset final. Los datos
  producidos (`salida/`, imágenes reales de la vivienda) viven fuera del repo,
  en `/srv/vision-training-data/deteccion-objetos/` (ver ADR-0028).
- **TrainBridge** (`proyecto_gpu/` en su ubicación original, se copia entero al
  equipo con GPU): entrenamiento, validación y exportación a OpenVINO. Recomendado
  convertirlo en su propio repo Git ahí (`git init`), separado del repo
  `smarthome` -- no es infraestructura del hogar, es un workspace de ML
  que consume datasets exportados desde el NUC.

## Requisitos según plataforma

El equipo con GPU puede ser Linux, Windows con WSL2, o Windows nativo sin
WSL -- los tres están soportados. Cada paso de abajo trae su bloque de
comandos para **Linux / WSL2** (`scripts/*.sh`) y para **Windows nativo**
(`scripts\windows\*.ps1`).

- **Linux nativo o WSL2**: Python 3.x, `pip`, y el driver NVIDIA/CUDA
  normal del sistema. Para WSL2 puntualmente: `wsl --install` desde
  PowerShell como administrador, y después instalar en Windows el driver
  NVIDIA normal (ya incluye el soporte de passthrough a WSL -- no hace
  falta instalar un driver aparte *dentro* de WSL). Conviene clonar/copiar
  este proyecto dentro del filesystem de WSL (`~/...`) y no en
  `/mnt/c/...`, por rendimiento de E/S. Adentro de WSL todo funciona
  idéntico a Linux nativo: son los mismos `scripts/*.sh`.
- **Windows nativo (sin WSL)**: Python 3.x instalado desde
  [python.org](https://python.org) con la casilla **"Add python.exe to
  PATH"** marcada durante la instalación, y el driver NVIDIA/CUDA normal
  (el mismo que usarías para cualquier otro entrenamiento, no hace falta
  nada especial). Los scripts `.ps1` llaman directo al ejecutable del
  entorno virtual (`.venv\Scripts\python.exe`) en vez de "activarlo"
  (`Activate.ps1`), así que **no** hace falta tocar la `ExecutionPolicy`
  de PowerShell para nada relacionado al venv --
  puede que sí haga falta `powershell -ExecutionPolicy Bypass -File ...`
  para poder correr los `.ps1` en sí, según la política del equipo (cada
  script lo recuerda en su encabezado). `curl.exe` y `tar.exe` ya vienen
  incluidos en Windows 10 (actualización 1803 o más nueva) y Windows 11 --
  no hace falta instalar nada aparte para eso.

## Cómo funciona

Todo el trabajo real (descargar el dataset, entrenar, validar, exportar a
OpenVINO, inspeccionar el tensor, subir el modelo) lo hace `runner.py` --
un único script Python, sin nada específico de sistema operativo. Los
scripts de `scripts/` no son "el proceso paso a paso": son solo los dos
momentos que sí dependen de la plataforma (instalar el entorno la primera
vez, y lanzar el worker), cada uno con su versión bash y PowerShell.

### 1. En el NUC: preparar el dataset y dejar la herramienta corriendo

El código de recolección/revisión vive en `vision-training/deteccion-objetos/`
(versionado); los datos (imágenes reales) viven aparte, fuera del repo, en
`/srv/vision-training-data/deteccion-objetos/` (ver ADR-0028). Ver el
`README.md` de esa carpeta para el flujo de cosechar/revisar. Con eso
hecho, dejar corriendo la herramienta de revisión:

```bash
python3 vision-training/deteccion-objetos/herramienta_revision/review_server.py \
  --dataset /srv/vision-training-data/deteccion-objetos/salida \
  --host 0.0.0.0 --port 8850
```

### 2. En el equipo con GPU: copiar el proyecto (una sola vez)

```bash
mkdir -p ~/trainbridge
rsync -avz \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.env' \
  --exclude 'datasets/*' \
  --exclude 'runs/' \
  --exclude 'modelos/' \
  usuario@nuc:/ruta/a/trainbridge/ \
  ~/trainbridge/

cd ~/trainbridge
git init   # opcional, si querés versionar scripts/README acá (el .gitignore ya excluye datasets/runs/modelos)
```

Crear `.env` a partir de `.env.example` y completarlo localmente. La IP del NUC
y el token los imprime `review_server.py` al iniciar; también quedan en
`salida/.upload_token` en el NUC. `.env` contiene secretos y no se versiona.

### 3. En el equipo con GPU: instalar el entorno (una sola vez por equipo)

**Linux / WSL2:**

```bash
bash scripts/01_setup_env.sh
```

**Windows (PowerShell):**

```powershell
powershell -File scripts\windows\01_setup_env.ps1
```

Crea `.venv/`, instala `requirements.txt`, y confirma que ve la GPU
(imprime el nombre). Si dice que no hay CUDA disponible, resolver los
drivers antes de seguir -- entrenar en CPU un YOLO, aunque sea chico, no
vale la pena el tiempo. Si aparece el aviso de que el driver es demasiado
antiguo aunque `nvidia-smi` sí detecte la GPU, consultar
[SOLUCION_CUDA.md](SOLUCION_CUDA.md).

### 4. En el equipo con GPU: lanzar el worker

**Linux / WSL2:**

```bash
bash scripts/02_run_worker.sh
```

**Windows (PowerShell):**

```powershell
powershell -File scripts\windows\02_run_worker.ps1
```

Queda corriendo en loop, haciendo *polling* al NUC cada pocos segundos
preguntando si hay un entrenamiento encolado -- nunca al revés, el NUC no
necesita poder conectarse a este equipo (ver
[CONTEXTO.md](CONTEXTO.md#el-flujo-recursivo-por-qué-esto-no-es-una-sola-corrida)
para el porqué). Cualquier equipo con GPU disponible que tenga el worker
corriendo puede tomar el próximo trabajo -- no hace falta que sea siempre
el mismo ("vientre de alquiler"). Repetir los pasos 2-4 en cada equipo
nuevo que se quiera sumar.

Si un trabajo terminó de entrenar y exportar pero falló en el procesamiento o
la subida final, se puede recuperar sin repetir las épocas:

```bash
.venv/bin/python runner.py --finalizar-job <campana> <job-id>
```

El comando exige que existan el dataset de esa ejecución y
`runs/<campana>/<job-id>/weights/best.pt`. Repite solamente la validación de
`best.pt`, reutiliza el OpenVINO existente si está disponible, completa el
paquete, lo sube al NUC y actualiza el estado del trabajo a `listo`.

### 5. Encolar un entrenamiento

En la herramienta de revisión (paso 1, corriendo en el NUC), pestaña
**Entrenamiento**: completar campaña/modelo base/épocas y apretar
"Entrenar". La barra de progreso se actualiza con lo que el worker va
reportando (descarga del dataset, época actual, validación, exportación,
subida) hasta terminar o fallar. Al terminar con éxito, la pestaña
muestra el bloque `model:` completo (path/labelmap/width/height/
model_type/input_tensor/input_pixel_format/input_dtype) con el layout y
dtype *reales* de esa exportación -- ya inspeccionado por `runner.py`, no
hace falta correr nada aparte para saberlo. El modelo en sí queda en el
NUC bajo `modelos_recibidos/<campana>/<timestamp>/`.

En el equipo de entrenamiento, los artefactos quedan separados y versionados:

```text
modelos/base/<modelo-base>.pt
datasets/<campana>/<job-id>/
runs/<campana>/<job-id>/
modelos/exportados/<campana>/<job-id>/
```

La campaña es el nombre legible que agrupa entrenamientos relacionados; el
ID del trabajo evita colisiones cuando una campaña se vuelve a entrenar. Cada
exportación incluye el modelo OpenVINO, `labels.txt` generado desde las clases
del dataset y `metadata.json` con la procedencia del entrenamiento.

Recursivo: no hace falta esperar a revisar todo el dataset cosechado antes
de encolar un entrenamiento -- con lo revisado hasta ahora se entrena un
primer modelo intermedio, que ayuda a revisar más rápido lo que falta
(sugiere cajas en vez de partir de cero), y se vuelve a entrenar con el
conjunto ampliado cuando convenga.

`runner.py` entrena de punta a punta sin pausas para revisión humana. Si
en algún momento hace falta mirar a ojo las predicciones antes de decidir
si exportar (el mAP no garantiza que un caso puntual como el gato quedó
resuelto), o depurar un paso suelto, sus piezas son funciones normales de
Python (`descargar_dataset`, `entrenar_job`, `inspeccionar`, etc.) -- se
pueden llamar a mano desde una consola Python con el venv activado, sin
necesitar scripts aparte para eso.

### 6. En el NUC: desplegar, primero solo en canal_3

Copiar el modelo recibido a su destino final (ya está en el mismo equipo,
es un `cp` local, no hace falta red):

```bash
cp -r /srv/vision-training-data/deteccion-objetos/modelos_recibidos/deteccion-smarthome-v1/<timestamp> \
  /srv/frigate/config/model_custom/deteccion-smarthome-v1
```

Editar `frigate/config/config.yml`: pegar el bloque `model:` que mostró la
pestaña Entrenamiento al terminar, y **antes de aplicarlo global**,
probarlo apuntando el detector solo a canal_3 (o correr una segunda
instancia de prueba). Validar contra los casos ya conocidos (el gato, el
evento de 30s en negro) antes de replicar a las otras 4 cámaras -- mismo
criterio incremental que ADR-0025 (validar en un solo punto antes de
generalizar).

Este último paso lo hacemos juntos cuando llegues acá -- avisame cuando
tengas el modelo entrenado y seguimos.

## Futuras campañas (más clases de objetos)

1. En el NUC: adaptar `harvest.py` para las cámaras/clases nuevas (mismo
   patrón), revisar.
2. Acá: encolar con el nombre de campaña nuevo desde la pestaña
   Entrenamiento -- mismo `runner.py`, no hace falta cambiar nada.
