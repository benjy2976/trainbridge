# Lanza el worker (runner.py) con el python del venv -- convierte este
# equipo en un "vientre de alquiler": hace polling al NUC por trabajos de
# entrenamiento encolados desde la pestaña "Entrenamiento" de la
# herramienta de revisión, entrena, y sube el modelo solo.
#
# Uso: powershell -File scripts\windows\02_run_worker.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')

$venvPython = '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Error 'No existe .venv -- correr antes: powershell -File scripts\windows\01_setup_env.ps1'
    exit 1
}

& $venvPython runner.py
exit $LASTEXITCODE
