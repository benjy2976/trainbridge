#!/usr/bin/env python3
"""Inspecciona un .xml exportado a OpenVINO para saber qué poner en el
`model:` de Frigate -- en vez de asumir. Los defaults de Frigate son
nhwc/rgb/int; el export típico de ultralytics suele salir nchw/float. Este
módulo lo dice con certeza, para esta exportación puntual.

Se usa de dos formas:
  - `runner.py` lo importa (`from inspect_model import inspeccionar`) para
    incluir el bloque `model:` en el reporte final de un entrenamiento
    automático, sin que haga falta un paso manual aparte.
  - Como script suelto, para inspeccionar cualquier .xml a mano (un modelo
    viejo, uno entrenado fuera del worker, etc.):
      .venv/bin/python inspect_model.py modelos/exportados/<campana>/<job_id>/best.xml
"""

import sys


def inspeccionar(model_path):
    """Devuelve un dict con la forma/dtype/layout reales del .xml, y el
    bloque `model:` ya armado como texto para pegar en Frigate."""
    from openvino import Core

    core = Core()
    modelo = core.read_model(str(model_path))
    input_node = modelo.inputs[0]
    shape = list(input_node.shape)
    dtype = input_node.get_element_type().get_type_name()

    # Heurística simple: NCHW tiene canal=3 en la posición 1;
    # NHWC lo tiene en la última posición.
    if len(shape) == 4 and shape[1] == 3:
        layout = "nchw"
    elif len(shape) == 4 and shape[-1] == 3:
        layout = "nhwc"
    else:
        layout = None

    dtype_map = {"f32": "float", "f16": "float", "i32": "int", "u8": "int"}
    input_dtype = dtype_map.get(dtype)

    width = height = None
    if layout == "nchw":
        width, height = shape[3], shape[2]
    elif layout == "nhwc":
        width, height = shape[2], shape[1]

    return {
        "model_path": str(model_path),
        "shape": shape,
        "dtype": dtype,
        "layout": layout,
        "input_dtype": input_dtype,
        "width": width,
        "height": height,
    }


def formatear_bloque_model(campana, info):
    """Arma el bloque `model:` de Frigate como texto, listo para pegar."""
    layout = info["layout"] or "<verificar -- forma inesperada>"
    input_dtype = info["input_dtype"] or f"<verificar -- dtype {info['dtype']} desconocido>"
    width = info["width"] if info["width"] is not None else "<verificar>"
    height = info["height"] if info["height"] is not None else "<verificar>"
    return f"""model:
  path: /config/model_custom/{campana}/best.xml
  labelmap_path: /config/model_custom/{campana}/labels.txt
  width: {width}
  height: {height}
  model_type: yolo-generic
  input_tensor: {layout}
  input_pixel_format: rgb
  input_dtype: {input_dtype}
"""


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    model_path = sys.argv[1]
    info = inspeccionar(model_path)

    print(f"Modelo: {info['model_path']}")
    print(f"Forma de entrada: {info['shape']}")
    print(f"Tipo de dato: {info['dtype']}")
    print(f"Layout detectado: {info['layout'] or 'desconocido -- revisar a mano'}")
    print()
    print("Para pegar en frigate/config/config.yml del lado del NUC "
          "(reemplazar <campana> por el nombre real):")
    print(formatear_bloque_model("<campana>", info))
    print("input_pixel_format se asume rgb (lo típico en export de "
          "ultralytics) -- si las detecciones salen raras tras desplegar, "
          "es el primer sospechoso a probar con bgr.")


if __name__ == "__main__":
    main()
