"""Demostración de Juanfra con el lexer original, sin copiarlo a un módulo.

Ejecutar: python -m herramientas.demo_parser
Vicente podrá sustituir cargar_lexer_notebook por un import de su módulo.
"""

import json
from pathlib import Path

from agroreglas import ErrorSintactico, analizar_tokens

RAIZ = Path(__file__).resolve().parents[1]


def cargar_lexer_notebook():
    notebook = json.loads((RAIZ / "anlizador_lexico1.ipynb").read_text(encoding="utf-8"))
    entorno = {}
    # Solo la celda de definición local del docente; no se ejecuta el ejemplo.
    exec(compile("".join(notebook["cells"][0]["source"]), "lexer_notebook", "exec"), entorno)
    return entorno["analizador_lexico"]


def main():
    lexer = cargar_lexer_notebook()
    casos = json.loads((RAIZ / "especificacion/casos.json").read_text(encoding="utf-8"))["casos"]
    for caso in casos:
        print(f"{caso['id']}: {caso['entrada']}")
        try:
            ast = analizar_tokens(lexer(caso["entrada"]), caso["entrada"])
        except ErrorSintactico as error:
            print(f"RECHAZADO. {error}\n")
        else:
            print(f"ACEPTADO. Reglas en AST: {len(ast['reglas'])}\n")
    print("AST del caso V04:")
    fuente = casos[3]["entrada"]
    print(json.dumps(analizar_tokens(lexer(fuente), fuente), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
