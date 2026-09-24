#!/usr/bin/env bash
# Lanza el worker (runner.py) con el python del venv -- convierte este
# equipo en un "vientre de alquiler": hace polling al NUC por trabajos de
# entrenamiento encolados desde la pestaña "Entrenamiento" de la
# herramienta de revisión, entrena, y sube el modelo solo.
#
# Uso: bash scripts/02_run_worker.sh
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "No existe .venv -- correr antes: bash scripts/01_setup_env.sh" >&2
  exit 1
fi

exec .venv/bin/python runner.py
