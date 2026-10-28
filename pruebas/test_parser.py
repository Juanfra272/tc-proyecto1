"""Pruebas de Juanfra: AST completo de V01 a V05 y contrato de errores."""

import json
from pathlib import Path
import unittest

from agroreglas import ErrorSintactico, analizador_lexico, analizar_tokens

RAIZ = Path(__file__).resolve().parents[1]
CASOS = {c["id"]: c for c in json.loads(
    (RAIZ / "especificacion/casos.json").read_text(encoding="utf-8"))["casos"]}


def numero(valor):
    return {"tipo": "Numero", "valor": valor}


def booleano(valor):
    return {"tipo": "Booleano", "valor": valor}


def comparacion(nombre, operador, valor):
    return {"tipo": "Comparacion", "identificador": nombre, "operador": operador, "valor": valor}


def logica(operador, izquierda, derecha):
    return {"tipo": "Logica", "operador": operador, "izquierda": izquierda, "derecha": derecha}


def negacion(operando):
    return {"tipo": "Negacion", "operando": operando}


def regla(condicion, verbo, destino):
    return {"tipo": "Regla", "condicion": condicion,
            "accion": {"tipo": "Accion", "verbo": verbo, "destino": destino}}


def programa(*reglas):
    return {"tipo": "Programa", "reglas": list(reglas)}


class PruebasParser(unittest.TestCase):
    lexer = staticmethod(analizador_lexico)

    def analizar(self, fuente):
        return analizar_tokens(self.lexer(fuente), fuente)

    def comprobar_valido(self, identificador, esperado):
        caso = CASOS[identificador]
        tokens = self.lexer(caso["entrada"])
        self.assertEqual([list(t) for t in tokens], caso["tokens_esperados"])
        self.assertEqual(analizar_tokens(tokens, caso["entrada"]), esperado)

    def test_v01_regla_numerica(self):
        self.comprobar_valido("V01", programa(regla(
            comparacion("humedad", "<", numero("30")), "abrir", "valvula")))

    def test_v02_booleano(self):
        self.comprobar_valido("V02", programa(regla(
            comparacion("lluvia", "==", booleano(False)), "activar", "riego")))

    def test_v03_precedencia(self):
        self.comprobar_valido("V03", programa(regla(logica("OR",
            logica("AND", comparacion("temperatura", ">=", numero("28")),
                   comparacion("humedad", "<=", numero("40"))),
            comparacion("emergencia", "==", booleano(True))), "activar", "alarma")))

    def test_v04_negacion_y_grupo(self):
        self.comprobar_valido("V04", programa(regla(logica("AND",
            negacion(logica("OR", comparacion("lluvia", "==", booleano(True)),
                            comparacion("humedad", ">", numero("60")))),
            comparacion("nivel", "!=", numero("0"))), "encender", "bomba")))

    def test_v05_anidamiento_y_varias_reglas(self):
        self.comprobar_valido("V05", programa(
            regla(negacion(negacion(logica("AND",
                comparacion("humedad", "<", numero("30")),
                logica("OR", comparacion("lluvia", "==", booleano(False)),
                       comparacion("reserva", ">", numero("0")))))), "abrir", "valvula"),
            regla(comparacion("nivel", "==", numero("0")), "apagar", "bomba")))

    def test_asociacion_izquierda_para_ambos_conectores(self):
        for operador in ("AND", "OR"):
            with self.subTest(operador=operador):
                fuente = f"WHEN a < 1 {operador} b < 2 {operador} c < 3 THEN abrir valvula;"
                self.assertEqual(self.analizar(fuente), programa(regla(logica(operador,
                    logica(operador, comparacion("a", "<", numero("1")),
                           comparacion("b", "<", numero("2"))),
                    comparacion("c", "<", numero("3"))), "abrir", "valvula")))

    def test_ubicacion_multilinea_y_numero_unicode(self):
        fuente = "when humedad < ٣ THEN abrir valvula;\n\tWHEN nivel ==\n  THEN apagar bomba;"
        with self.assertRaises(ErrorSintactico) as capturado:
            self.analizar(fuente)
        error = capturado.exception
        self.assertEqual((error.token.linea, error.token.columna), (3, 3))
        self.assertEqual(error.token.desplazamiento, fuente.rindex("THEN"))
        self.assertEqual(error.simbolo_pendiente, "Valor")

    def test_entrada_vacia_y_texto_sobrante(self):
        for fuente, simbolo in ((" \n\t", "Programa"),
                                (CASOS["V01"]["entrada"] + " extra", "Resto")):
            with self.subTest(fuente=fuente):
                with self.assertRaises(ErrorSintactico) as capturado:
                    self.analizar(fuente)
                self.assertEqual(capturado.exception.simbolo_pendiente, simbolo)

    def test_eof_tras_espacios(self):
        fuente = "WHEN nivel == 0 THEN apagar bomba\n  "
        with self.assertRaises(ErrorSintactico) as capturado:
            self.analizar(fuente)
        self.assertEqual(capturado.exception.token.desplazamiento, len(fuente.rstrip()))
        self.assertEqual((capturado.exception.token.linea, capturado.exception.token.columna), (1, 34))

    def test_mensajes_legibles_y_orden_de_valores(self):
        for fuente, esperado in (
            (CASOS["I06"]["entrada"], "un operador relacional"),
            (CASOS["I01"]["entrada"], "un número, TRUE o FALSE"),
            (CASOS["V01"]["entrada"] + " extra", "fin de entrada"),
        ):
            with self.subTest(fuente=fuente):
                with self.assertRaises(ErrorSintactico) as capturado:
                    self.analizar(fuente)
                mensaje = str(capturado.exception)
                self.assertIn(esperado, mensaje)
                for interno in ("OP_REL", "$", "Símbolo pendiente", "Cola", "Resto"):
                    self.assertNotIn(interno, mensaje)

    def test_i07_no_sugiere_cerrar_grupo_inexistente(self):
        with self.assertRaises(ErrorSintactico) as capturado:
            self.analizar(CASOS["I07"]["entrada"])
        self.assertNotIn("PARENT_DER", capturado.exception.tokens_esperados)
        self.assertNotIn("cerrar", str(capturado.exception))
        with self.assertRaises(ErrorSintactico) as capturado:
            self.analizar("WHEN (a < 1 abrir valvula;")
        self.assertIn("PARENT_DER", capturado.exception.tokens_esperados)

    def test_booleanos_del_arbol_en_mayusculas(self):
        from agroreglas.arbol import formatear_arbol
        for valor in ("TRUE", "FALSE"):
            arbol = formatear_arbol(self.analizar(f"WHEN a == {valor} THEN x y;"))
            self.assertIn(f"Booleano {valor}", arbol)

    def test_pila_no_depende_del_limite_de_recursion(self):
        fuente = "WHEN " + "(" * 1100 + "nivel == 0" + ")" * 1100 + " THEN apagar bomba;"
        self.assertEqual(self.analizar(fuente), programa(regla(
            comparacion("nivel", "==", numero("0")), "apagar", "bomba")))
        self.assertEqual(len(self.analizar(CASOS["V01"]["entrada"] * 1100)["reglas"]), 1100)

    def test_numero_conserva_el_literal_sin_limite_de_digitos(self):
        # Python no convierte a entero textos de más de 4300 dígitos; el AST no debe heredar ese límite.
        literal = "0" + "9" * 5000
        self.assertEqual(self.analizar(f"WHEN nivel > {literal} THEN abrir valvula;"), programa(regla(
            comparacion("nivel", ">", numero(literal)), "abrir", "valvula")))

    def test_contrato_tokens_y_fuente(self):
        with self.assertRaisesRegex(ValueError, "no coinciden"):
            analizar_tokens([("WHEN", "when")], "WHEN")
        with self.assertRaisesRegex(ValueError, "sin tokenizar"):
            analizar_tokens([], "WHEN")


if __name__ == "__main__":
    unittest.main()
