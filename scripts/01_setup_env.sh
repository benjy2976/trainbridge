#!/usr/bin/env bash
# Crea el entorno virtual y instala dependencias. Correr una sola vez
# (o de nuevo si se borra .venv/ o cambia requirements.txt).
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Entorno listo. Verificando GPU visible para PyTorch/Ultralytics:"
python3 -c "
import torch
print('CUDA disponible:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
else:
    print('ADVERTENCIA: no se detectó GPU. Revisar drivers CUDA antes de entrenar.')
"
