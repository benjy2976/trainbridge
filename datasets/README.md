# Datasets

Cada ejecución conserva una copia del dataset exacto que usó. El worker crea
la carpeta a partir de la campaña y del ID único del trabajo:

```text
datasets/<nombre-campana>/<job-id>/
  dataset.yaml
  images/train/*.jpg
  images/val/*.jpg
  labels/train/*.txt
  labels/val/*.txt
```

`dataset.yaml` viene con las clases (`person`, `cat`, etc.). Al descargarlo,
`runner.py` reemplaza `path` por la ruta absoluta de esa ejecución para que
Ultralytics no dependa de su configuración global `datasets_dir`.

Los datasets se descargan del NUC por HTTP cuando el worker toma un trabajo;
no hace falta crear estas carpetas ni copiar los datos manualmente. Para una
campaña futura, preparar y revisar la nueva exportación en el NUC y encolar el
entrenamiento desde la herramienta de revisión.
