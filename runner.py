#!/usr/bin/env python3
"""Worker que convierte este equipo con GPU en un "vientre de alquiler"
para entrenar el detector: hace polling al NUC preguntando por trabajos
de entrenamiento encolados desde la pestaña "Entrenamiento" de la
herramienta de revisión, y cuando encuentra uno, descarga el dataset ya
revisado, entrena, valida, exporta a OpenVINO y sube el modelo -- todo
reportando progreso de vuelta al NUC en cada paso.

Deliberadamente al revés de lo que parecería obvio: el NUC nunca se
conecta a este equipo. Es este equipo el que siempre inicia el contacto
(igual que un runner de CI self-hosted) -- así cualquier máquina con GPU
sirve sin necesitar IP fija, puertos abiertos ni estar siempre prendida.
Ver ADR-0029.

Uso (con el venv ya creado por 01_setup_env, y .env ya completado --
mismos requisitos que 00_fetch_dataset.sh/06_upload_model.sh):
  .venv/bin/python runner.py            # Linux / WSL2
  .venv\\Scripts\\python.exe runner.py  # Windows

Corre en loop indefinido -- Ctrl+C para parar. No hace falta correr los
scripts 00/02/03/04/06 a mano mientras el worker está activo; siguen
disponibles para depurar un paso puntual o mirar a ojo las predicciones
de validación (el worker automático no se detiene a esperar esa revisión
humana -- ver README, sección "Modo automático vs. manual").
"""

import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DATASETS_DIR = ROOT / "datasets"
RUNS_DIR = ROOT / "runs"
MODELS_DIR = ROOT / "modelos"
BASE_MODELS_DIR = MODELS_DIR / "base"
EXPORTED_MODELS_DIR = MODELS_DIR / "exportados"
POLL_SECONDS = 5
HTTP_TIMEOUT = 60
SEGMENTO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def api_request(method, path, token, body=None, extra_headers=None, timeout=HTTP_TIMEOUT):
    url = f"{os.environ['REVIEW_URL']}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-Auth-Token", token)
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    data = None
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = body
        else:
            data = json.dumps(body).encode()
            req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, data=data, timeout=timeout)


def reportar(token, job_id, **campos):
    try:
        api_request("POST", f"/api/train/jobs/{job_id}/estado", token, body=campos)
    except (urllib.error.URLError, OSError) as exc:
        print(f"! no se pudo reportar estado al NUC: {exc}")


def validar_segmento(valor, nombre):
    """Valida nombres que se usarán como un solo componente de una ruta."""
    if not isinstance(valor, str) or not SEGMENTO_RE.fullmatch(valor):
        raise ValueError(
            f"{nombre} inválido: usar solo letras ASCII, números, punto, guión o guion bajo"
        )
    return valor


def normalizar_dataset_yaml(dataset_dir):
    """Fija la raíz real del dataset y comprueba su estructura YOLO."""
    dataset_yaml = dataset_dir / "dataset.yaml"
    if not dataset_yaml.is_file():
        raise FileNotFoundError(f"el dataset descargado no contiene {dataset_yaml.name}")

    config = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("dataset.yaml no contiene un objeto YAML válido")
    if "train" not in config or "val" not in config or "names" not in config:
        raise ValueError("dataset.yaml debe declarar train, val y names")

    for ruta in ("images/train", "images/val", "labels/train", "labels/val"):
        if not (dataset_dir / ruta).is_dir():
            raise FileNotFoundError(f"falta el directorio requerido del dataset: {ruta}")

    # Ultralytics interpreta `path: .` respecto a su setting global
    # datasets_dir, no respecto al YAML. La ruta absoluta evita que la misma
    # exportación se resuelva de manera diferente en cada worker.
    config["path"] = str(dataset_dir.resolve())
    dataset_yaml.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return dataset_yaml


def crear_labelmap(dataset_yaml, destino):
    """Crea el mapa indexado que Frigate espera a partir de `names`."""
    config = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8"))
    names = config.get("names") if isinstance(config, dict) else None
    if isinstance(names, list):
        clases = list(enumerate(names))
    elif isinstance(names, dict):
        try:
            clases = sorted((int(indice), nombre) for indice, nombre in names.items())
        except (TypeError, ValueError) as exc:
            raise ValueError("los índices de names en dataset.yaml deben ser enteros") from exc
    else:
        raise ValueError("names en dataset.yaml debe ser una lista o un mapa")

    indices = [indice for indice, _ in clases]
    if indices != list(range(len(clases))):
        raise ValueError("los índices de names deben ser consecutivos y comenzar en 0")
    if any(not isinstance(nombre, str) or not nombre.strip() for _, nombre in clases):
        raise ValueError("todos los nombres de clases deben ser textos no vacíos")

    destino.write_text(
        "".join(f"{indice} {nombre.strip()}\n" for indice, nombre in clases),
        encoding="utf-8",
    )
    return [nombre.strip() for _, nombre in clases]


def descargar_dataset(token, campana, job_id):
    campana = validar_segmento(campana, "campana")
    job_id = validar_segmento(job_id, "job_id")
    campana_dir = DATASETS_DIR / campana
    dataset_dir = campana_dir / job_id
    campana_dir.mkdir(parents=True, exist_ok=True)

    with api_request("GET", "/api/export", token) as resp:
        fd, tmp_name = tempfile.mkstemp(suffix=".tar.gz")
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(resp, f)

    extraccion_dir = Path(tempfile.mkdtemp(prefix=f".{job_id}-", dir=campana_dir))
    try:
        with tarfile.open(tmp_name) as tar:
            tar.extractall(extraccion_dir, filter="data")
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        extraccion_dir.replace(dataset_dir)
        return normalizar_dataset_yaml(dataset_dir)
    finally:
        os.unlink(tmp_name)
        if extraccion_dir.exists():
            shutil.rmtree(extraccion_dir)


def preparar_modelo_base(nombre_modelo):
    """Descarga una vez el peso base y devuelve su ruta administrada."""
    nombre_modelo = validar_segmento(nombre_modelo, "modelo_base")
    if not nombre_modelo.endswith(".pt"):
        raise ValueError("modelo_base debe ser el nombre de un archivo .pt")

    BASE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    destino = BASE_MODELS_DIR / nombre_modelo
    legado = ROOT / nombre_modelo
    if not destino.exists() and legado.is_file():
        shutil.move(str(legado), destino)

    if not destino.exists():
        from ultralytics.utils.downloads import attempt_download_asset

        descargado = Path(attempt_download_asset(destino))
        if not descargado.is_file():
            raise FileNotFoundError(f"no se pudo descargar el modelo base {nombre_modelo}")
    return destino


def subir_modelo(token, campana, modelo_dir):
    fd, tmp_name = tempfile.mkstemp(suffix=".tar.gz")
    os.close(fd)
    try:
        with tarfile.open(tmp_name, "w:gz") as tar:
            tar.add(modelo_dir, arcname=".")
        with open(tmp_name, "rb") as f:
            cuerpo = f.read()
        api_request(
            "POST", f"/api/model?campana={campana}", token, body=cuerpo,
            extra_headers={"Content-Type": "application/gzip"},
        ).close()
    finally:
        os.unlink(tmp_name)


def entrenar_job(job, token):
    # Import diferido: solo hace falta cuando hay un trabajo real, así el
    # worker arranca y hace polling incluso si algo del entorno de
    # ultralytics/torch todavía no está del todo listo.
    from ultralytics import YOLO

    campana = validar_segmento(job["campana"], "campana")
    job_id = validar_segmento(job["id"], "job_id")
    epocas_totales = job["epochs"]

    reportar(token, job_id, estado="entrenando", mensaje="descargando dataset revisado")
    dataset_yaml = descargar_dataset(token, campana, job_id)

    def al_terminar_epoca(trainer):
        epoca = trainer.epoch + 1
        reportar(
            token, job_id, estado="entrenando",
            epoca_actual=epoca, epocas_totales=epocas_totales,
            mensaje=f"entrenando -- época {epoca}/{epocas_totales}",
        )

    modelo_base = preparar_modelo_base(job["modelo_base"])
    modelo = YOLO(str(modelo_base))
    modelo.add_callback("on_train_epoch_end", al_terminar_epoca)
    campana_runs_dir = RUNS_DIR / campana
    campana_runs_dir.mkdir(parents=True, exist_ok=True)
    modelo.train(
        data=str(dataset_yaml), epochs=epocas_totales, imgsz=640,
        patience=20, project=str(campana_runs_dir), name=job_id,
        exist_ok=True,
    )
    run_dir = Path(modelo.trainer.save_dir)

    reportar(token, job_id, estado="validando", mensaje="validando contra el split de validación")
    weights = run_dir / "weights" / "best.pt"
    if not weights.is_file():
        raise FileNotFoundError(f"el entrenamiento no produjo {weights}")
    modelo_val = YOLO(str(weights))
    metricas = modelo_val.val(
        data=str(dataset_yaml), project=str(run_dir), name="validacion",
        exist_ok=True,
    )
    map50 = None
    try:
        map50 = float(metricas.box.map50)
    except (AttributeError, TypeError):
        pass

    reportar(token, job_id, estado="exportando", mensaje="exportando a OpenVINO")
    origen = Path(modelo_val.export(format="openvino", imgsz=640))
    if not origen.is_dir():
        raise FileNotFoundError(f"la exportación OpenVINO no produjo un directorio: {origen}")

    modelo_dir = EXPORTED_MODELS_DIR / campana / job_id
    if modelo_dir.exists():
        shutil.rmtree(modelo_dir)
    modelo_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(origen, modelo_dir)

    xml_exportados = list(modelo_dir.glob("*.xml"))
    if len(xml_exportados) != 1:
        raise RuntimeError(
            f"se esperaba exactamente un .xml OpenVINO en {modelo_dir}; encontrados: {len(xml_exportados)}"
        )

    # Inspecciona el .xml recién exportado para saber con certeza el
    # layout/dtype reales (los defaults de Frigate probablemente no
    # coincidan con lo que ultralytics exportó) -- se incluye en el
    # reporte final para no necesitar un paso manual aparte.
    from inspect_model import inspeccionar, formatear_bloque_model
    info = inspeccionar(xml_exportados[0])
    bloque_model = formatear_bloque_model(campana, info)
    clases = crear_labelmap(dataset_yaml, modelo_dir / "labels.txt")

    metadata = {
        "campana": campana,
        "job_id": job_id,
        "creado_utc": datetime.now(timezone.utc).isoformat(),
        "modelo_base": modelo_base.name,
        "epocas_solicitadas": epocas_totales,
        "map50": map50,
        "dataset_yaml": str(dataset_yaml),
        "run_dir": str(run_dir),
        "openvino_xml": xml_exportados[0].name,
        "clases": clases,
    }
    (modelo_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    reportar(token, job_id, estado="subiendo", mensaje="subiendo modelo al NUC")
    subir_modelo(token, campana, modelo_dir)

    mensaje_final = "listo" if map50 is None else f"listo -- mAP50={map50:.3f}"
    reportar(token, job_id, estado="listo", mensaje=mensaje_final, detalle=bloque_model)


def main():
    load_env()
    token = os.environ.get("REVIEW_TOKEN")
    url = os.environ.get("REVIEW_URL")
    if not token or not url:
        print("Falta REVIEW_URL/REVIEW_TOKEN -- copiar .env.example a .env y completarlo.")
        sys.exit(1)
    if not (ROOT / ".venv").exists():
        print("No existe .venv -- correr antes 01_setup_env (sh o ps1) al menos una vez.")
        sys.exit(1)

    print(f"Worker escuchando trabajos en {url} (cada {POLL_SECONDS}s, Ctrl+C para parar)")
    while True:
        job = None
        try:
            with api_request("GET", "/api/train/jobs/siguiente", token) as resp:
                job = json.loads(resp.read()).get("job")
        except (urllib.error.URLError, OSError) as exc:
            print(f"! error consultando trabajos: {exc}")

        if job is None:
            time.sleep(POLL_SECONDS)
            continue

        print(f"Tomando trabajo {job['id']} (campaña {job['campana']}, {job['epochs']} épocas)")
        try:
            entrenar_job(job, token)
            print("Trabajo terminado.")
        except Exception as exc:  # noqa: BLE001 -- cualquier falla debe reportarse, no tirar el worker
            print(f"! el trabajo falló: {exc}")
            reportar(token, job["id"], estado="error", error=str(exc))


if __name__ == "__main__":
    main()
