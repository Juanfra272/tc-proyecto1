"""Pruebas de Vicente: los 25 casos documentados y la ejecución desde texto o archivo."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from agroreglas import ErrorLexico, analizador_lexico
from agroreglas.__main__ import main
from herramientas.demo_parser import resultado

RAIZ = Path(__file__).resolve().parents[1]
CASOS = json.loads((RAIZ / "especificacion/casos.json").read_text(encoding="utf-8"))["casos"]


def ejecutar(fuente):
    """Resultado observable de un caso: (resultado, datos del error o None)."""
    _, error = resultado(fuente)
    if error is None:
        return "aceptar", None
    etapa = "lexico" if isinstance(error, ErrorLexico) else "sintactico"
    return "rechazar", {"tipo_error": etapa, **error.como_dict()}


def cli(*argumentos):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue()


class PruebasCasos(unittest.TestCase):
    def test_hay_25_casos_distintos(self):
        ids = [c["id"][0] for c in CASOS]
        self.assertEqual((ids.count("V"), ids.count("I"), ids.count("L")), (10, 10, 5))
        self.assertEqual(len({c["entrada"] for c in CASOS}), 25)

    def test_resultado_y_error_de_cada_caso(self):
        for caso in CASOS:
            with self.subTest(caso=caso["id"]):
                if "tokens_esperados" in caso:
                    self.assertEqual([list(t) for t in analizador_lexico(caso["entrada"])],
                                     caso["tokens_esperados"])
                resultado, error = ejecutar(caso["entrada"])
                self.assertEqual(resultado, caso["resultado_esperado"])
                if error:
                    esperado = {k: v for k, v in caso["error_esperado"].items()
                                if k != "mensaje_orientativo"}
                    if "tokens_esperados" in error:
                        error["tokens_esperados"] = sorted(error["tokens_esperados"])
                        esperado["tokens_esperados"] = sorted(esperado["tokens_esperados"])
                    self.assertEqual(error, esperado)


class PruebasCLI(unittest.TestCase):
    def test_texto_aceptado_muestra_arbol(self):
        codigo, salida = cli("--texto", "WHEN humedad < 30 THEN abrir valvula;")
        self.assertEqual(codigo, 0)
        self.assertIn("ACEPTADO. 1 regla.", salida)
        self.assertIn("Comparacion humedad <", salida)

    def test_archivo_crlf_con_error_marca_la_columna(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "reglas.agro"
            ruta.write_bytes(b"\xef\xbb\xbfWHEN nivel == 0 THEN apagar bomba;\r\n\tWHEN humedad < THEN abrir valvula;\r\n")
            codigo, salida = cli(str(ruta))
        self.assertEqual(codigo, 1)
        self.assertIn("línea 2, columna 17", salida)
        self.assertTrue(salida.endswith("\tWHEN humedad < THEN abrir valvula;\n  \t               ^\n"))

    def test_texto_con_crlf(self):
        codigo, salida = cli("-t", "WHEN a < 1 THEN x y;\r\nWHEN b < 2 THEN x y;")
        self.assertEqual(codigo, 0)
        self.assertIn("ACEPTADO. 2 reglas.", salida)

    def test_error_lexico_ubicado(self):
        codigo, salida = cli("-t", "WHEN humedad < 3.5 THEN abrir valvula;")
        self.assertEqual(codigo, 1)
        self.assertIn("Error léxico en línea 1, columna 17", salida)

    def test_eof_no_senala_linea_vacia_final(self):
        for final in ("", "\n", "\n  ", "\n\n"):
            with self.subTest(final=final):
                codigo, salida = cli("-t", "WHEN a < 1 THEN x y" + final)
                self.assertEqual(codigo, 1)
                self.assertIn("línea 1, columna 20", salida)
                self.assertTrue(salida.endswith("WHEN a < 1 THEN x y\n  " + " " * 19 + "^\n"))

    def test_archivo_inexistente(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli(str(RAIZ / "no_existe.agro"))[0], 2)


if __name__ == "__main__":
    unittest.main()
