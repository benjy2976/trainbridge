# Solución de incompatibilidad entre PyTorch, CUDA y el driver NVIDIA

## Síntoma

Al ejecutar:

```bash
bash scripts/01_setup_env.sh
```

la instalación de paquetes termina correctamente, pero la verificación final
muestra un resultado similar a este:

```text
The NVIDIA driver on your system is too old (found version 12090)
CUDA disponible: False
ADVERTENCIA: no se detectó GPU.
```

En el equipo donde se encontró el problema, `nvidia-smi` sí detectaba una
NVIDIA GeForce RTX 3060 y mostraba un driver 577.00 con soporte para CUDA 12.9.
Por tanto, WSL2 y el passthrough de la GPU estaban funcionando.

## Causa

El `requirements.txt` original solo fijaba `ultralytics==8.3.40`.
Ultralytics declara una dependencia abierta, `torch>=1.8.0`, así que `pip`
seleccionó automáticamente PyTorch 2.14.0 y sus librerías para CUDA 13.

El driver instalado soporta CUDA 12.9, pero no una aplicación compilada para
CUDA 13. Por eso PyTorch se instaló sin errores, aunque luego no pudo
inicializar CUDA. El mensaje no significa que WSL2 no vea la GPU ni que sea
necesario instalar el CUDA Toolkit dentro de WSL.

## Solución aplicada a `requirements.txt`

Se fijan versiones compatibles y reproducibles de PyTorch y TorchVision,
compiladas para CUDA 12.8:

```text
--extra-index-url https://download.pytorch.org/whl/cu128
torch==2.11.0+cu128
torchvision==0.26.0+cu128
ultralytics==8.3.40
```

La build CUDA 12.8 puede ejecutarse con el driver actual, que soporta CUDA
12.9. `--extra-index-url` permite obtener las builds `+cu128` del índice
oficial de PyTorch, mientras las demás dependencias continúan disponibles en
PyPI.

Los pines son importantes: no se deben reemplazar por `torch>=...` ni omitir,
porque eso permitiría que una instalación futura vuelva a elegir una build de
CUDA incompatible.

## Recuperar un entorno que ya tiene la versión incompatible

La forma más limpia es recrear el entorno virtual. Esto también elimina los
paquetes CUDA 13, que ocupan varios gigabytes y ya no son necesarios:

```bash
rm -rf .venv
bash scripts/01_setup_env.sh
```

El comando solo elimina el entorno virtual local; no elimina el código, los
datasets ni los modelos.

## Verificación

Una vez terminado el setup, ejecutar:

```bash
.venv/bin/python -c 'import torch; print("PyTorch:", torch.__version__); print("CUDA de la build:", torch.version.cuda); print("CUDA disponible:", torch.cuda.is_available()); print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no disponible")'
```

El resultado esperado es equivalente a:

```text
PyTorch: 2.11.0+cu128
CUDA de la build: 12.8
CUDA disponible: True
GPU: NVIDIA GeForce RTX 3060
```

También se puede confirmar que WSL2 ve la GPU independientemente de PyTorch:

```bash
nvidia-smi
```

## Cuándo actualizar estas versiones

Antes de cambiar PyTorch, TorchVision o la variante `cu128`, comprobar en
conjunto:

1. Que PyTorch y TorchVision sean una pareja de versiones publicada por el
   proyecto PyTorch.
2. Que el driver NVIDIA soporte la versión CUDA con la que fue compilado
   PyTorch.
3. Que el entrenamiento, la validación y la exportación a OpenVINO sigan
   funcionando con la versión fijada de Ultralytics.
4. Que el modelo OpenVINO exportado conserve los tensores, el layout y los
   tipos esperados por la configuración de Frigate.

No se debe actualizar una sola de estas dependencias de manera aislada en un
equipo de producción.
