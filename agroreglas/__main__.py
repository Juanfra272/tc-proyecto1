"""Analiza un programa AgroReglas desde un archivo o desde texto.

Uso desde la raíz del repositorio:
    python -m agroreglas ejemplos/riego.agro
    python -m agroreglas --texto "WHEN humedad < 30 THEN abrir valvula;"
Código de salida: 0 si se acepta, 1 si se rechaza y 2 si falla la lectura.
"""

import argparse
import json
import sys

from . import ErrorLexico, ErrorSintactico, analizar_programa
from .arbol import formatear_arbol


def marcar_posicion(fuente, linea, columna):
    """Línea del error con un ^ bajo la columna; los tabuladores se copian para alinear."""
    texto = fuente.split("\n")[linea - 1]
    margen = "".join(c if c == "\t" else " " for c in texto[:columna - 1])
    return f"  {texto}\n  {margen}^"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m agroreglas",
        description="Reconoce un programa AgroReglas y muestra su AST o el primer error.")
    origen = parser.add_mutually_exclusive_group(required=True)
    origen.add_argument("archivo", nargs="?", help="archivo de texto UTF-8 con el programa")
    origen.add_argument("-t", "--texto", help="programa escrito directamente en la línea de comandos")
    parser.add_argument("--json", action="store_true", help="muestra el AST en JSON en vez del árbol")
    args = parser.parse_args(argv)

    if args.texto is not None:
        fuente = args.texto
    else:
        try:
            # utf-8-sig descarta el BOM que agregan algunos editores de Windows.
            with open(args.archivo, encoding="utf-8-sig") as archivo:
                fuente = archivo.read()
        except (OSError, UnicodeDecodeError) as error:
            print(f"No se pudo leer {args.archivo}: {error}", file=sys.stderr)
            return 2
    # El lexer solo admite LF como salto de línea.
    fuente = fuente.replace("\r\n", "\n").replace("\r", "\n")

    try:
        ast = analizar_programa(fuente)
    except (ErrorLexico, ErrorSintactico) as error:
        # ErrorSintactico guarda la ubicación en su token; ErrorLexico, en sí mismo.
        lugar = getattr(error, "token", error)
        print(f"RECHAZADO. {error}\n{marcar_posicion(fuente, lugar.linea, lugar.columna)}")
        return 1

    cantidad = len(ast["reglas"])
    print(f"ACEPTADO. {cantidad} {'regla' if cantidad == 1 else 'reglas'}.\n")
    print(json.dumps(ast, indent=2, ensure_ascii=False) if args.json else formatear_arbol(ast))
    return 0


if __name__ == "__main__":
    sys.exit(main())
