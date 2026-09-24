# Crea el entorno virtual e instala dependencias. Correr una sola vez
# (o de nuevo si se borra .venv/ o cambia requirements.txt).
#
# Uso: powershell -File scripts\windows\01_setup_env.ps1
#
# Si PowerShell bloquea la ejecución de este archivo (ExecutionPolicy por
# defecto en Windows), correrlo como:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\01_setup_env.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')

python -m venv .venv
if ($LASTEXITCODE -ne 0) { Write-Error 'No se pudo crear el entorno virtual (¿python no está en el PATH?)'; exit 1 }

$venvPython = '.venv\Scripts\python.exe'

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit 1 }

& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ''
Write-Host 'Entorno listo. Verificando GPU visible para PyTorch/Ultralytics:'
& $venvPython -c @'
import torch
print("CUDA disponible:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("ADVERTENCIA: no se detecto GPU. Revisar drivers CUDA antes de entrenar.")
'@
