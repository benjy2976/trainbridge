import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import runner


class RunnerPathsTest(unittest.TestCase):
    def crear_dataset(self, base):
        for ruta in ("images/train", "images/val", "labels/train", "labels/val"):
            (base / ruta).mkdir(parents=True)
        (base / "dataset.yaml").write_text(
            "path: .\ntrain: images/train\nval: images/val\nnames:\n  0: person\n",
            encoding="utf-8",
        )

    def test_normalizar_dataset_yaml_usa_ruta_absoluta(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_dir = Path(tmp) / "datasets" / "campana" / "job123"
            self.crear_dataset(dataset_dir)

            resultado = runner.normalizar_dataset_yaml(dataset_dir)
            config = yaml.safe_load(resultado.read_text(encoding="utf-8"))

            self.assertEqual(config["path"], str(dataset_dir.resolve()))
            self.assertEqual(config["train"], "images/train")
            self.assertEqual(config["val"], "images/val")

    def test_normalizar_dataset_yaml_detecta_estructura_incompleta(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_dir = Path(tmp)
            (dataset_dir / "dataset.yaml").write_text(
                "path: .\ntrain: images/train\nval: images/val\nnames: [person]\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(FileNotFoundError, "images/train"):
                runner.normalizar_dataset_yaml(dataset_dir)

    def test_validar_segmento_bloquea_escape_de_directorio(self):
        for valor in ("../otra-carpeta", "campana/trabajo", "..", ""):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    runner.validar_segmento(valor, "campana")

    def test_crear_labelmap_respeta_indices_del_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dataset_yaml = base / "dataset.yaml"
            labelmap = base / "labels.txt"
            dataset_yaml.write_text(
                "names:\n  0: person\n  1: cat\n  2: camioneta\n",
                encoding="utf-8",
            )

            clases = runner.crear_labelmap(dataset_yaml, labelmap)

            self.assertEqual(clases, ["person", "cat", "camioneta"])
            self.assertEqual(
                labelmap.read_text(encoding="utf-8"),
                "0 person\n1 cat\n2 camioneta\n",
            )

    def test_preparar_modelo_base_migra_peso_de_la_raiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modelos_base = root / "modelos" / "base"
            legado = root / "yolov9t.pt"
            legado.write_bytes(b"peso de prueba")

            with (
                patch.object(runner, "ROOT", root),
                patch.object(runner, "BASE_MODELS_DIR", modelos_base),
            ):
                resultado = runner.preparar_modelo_base("yolov9t.pt")

            self.assertEqual(resultado, modelos_base / "yolov9t.pt")
            self.assertEqual(resultado.read_bytes(), b"peso de prueba")
            self.assertFalse(legado.exists())


if __name__ == "__main__":
    unittest.main()
