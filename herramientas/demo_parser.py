"""Ejecuta los 25 casos documentados y muestra la decisión del analizador en cada uno.

Ejecutar desde la raíz: python -m herramientas.demo_parser
"""

import json
from pathlib import Path

from agroreglas import ErrorLexico, ErrorSintactico, analizar_programa

RAIZ = Path(__file__).resolve().parents[1]


def cargar_casos():
    return json.loads((RAIZ / "especificacion/casos.json").read_text(encoding="utf-8"))["casos"]


def resultado(fuente):
    """Devuelve (ast, None) si se acepta o (None, error) con el primer error léxico o sintáctico."""
    try:
        return analizar_programa(fuente), None
    except (ErrorLexico, ErrorSintactico) as error:
        return None, error


def main():
    casos = cargar_casos()
    for caso in casos:
        ast, error = resultado(caso["entrada"])
        print(f"{caso['id']}: {caso['entrada']!r}")
        if error:
            print(f"RECHAZADO. {error}\n")
        else:
            cantidad = len(ast["reglas"])
            print(f"ACEPTADO. {cantidad} {'regla' if cantidad == 1 else 'reglas'} en el AST.\n")
    print("AST del caso V04:")
    fuente = next(c["entrada"] for c in casos if c["id"] == "V04")
    print(json.dumps(analizar_programa(fuente), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
