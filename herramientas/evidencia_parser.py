"""Regenera resultados y páginas de evidencia de Juanfra.

Ejecutar desde la raíz: python -m herramientas.evidencia_parser
Las capturas PNG se toman después de abrir las páginas HTML resultantes.
"""

import html
import json
from pathlib import Path
import subprocess
import sys

from agroreglas import analizar_tokens
from agroreglas.arbol import formatear_arbol
from herramientas.demo_parser import cargar_lexer_notebook

RAIZ = Path(__file__).resolve().parents[1]


def pagina(titulo, salida):
    return f'''<!doctype html>
<html lang="es"><meta charset="utf-8"><title>{html.escape(titulo)}</title>
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; color: #182c26; }}
h1 {{ font-size: 22px; margin: 0 0 12px; }}
main {{ padding: 24px; background: #f4f7f5; }}
pre {{ padding: 18px; background: #152a23; color: #ebf3ef; border-radius: 8px;
font: 13px/1.55 monospace; white-space: pre-wrap; overflow-wrap: anywhere; }}
p {{ font-size: 13px; }}
</style><main><h1>{html.escape(titulo)}</h1>
<p>Salida real de Python. Página preparada para capturar e incorporar al informe.</p>
<pre>{html.escape(salida)}</pre></main></html>'''


def main():
    destino = RAIZ / "docs/evidencias"
    destino.mkdir(parents=True, exist_ok=True)
    demo = subprocess.run([sys.executable, "-m", "herramientas.demo_parser"],
                          cwd=RAIZ, capture_output=True, text=True, check=True)
    pruebas = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "pruebas", "-v"],
                             cwd=RAIZ, capture_output=True, text=True, check=True)
    salida = "$ python -m herramientas.demo_parser\n" + demo.stdout
    (destino / "ejecucion.txt").write_text(salida, encoding="utf-8")
    (destino / "pruebas.txt").write_text(pruebas.stdout + pruebas.stderr, encoding="utf-8")
    resumen = salida.split("AST del caso V04:")[0]
    (destino / "ejecucion.html").write_text(pagina("AgroReglas: aceptación y errores", resumen), encoding="utf-8")
    casos = json.loads((RAIZ / "especificacion/casos.json").read_text(encoding="utf-8"))["casos"]
    fuente = next(c["entrada"] for c in casos if c["id"] == "V04")
    ast = analizar_tokens(cargar_lexer_notebook()(fuente), fuente)
    (RAIZ / "ejemplos/arbol_v04.json").write_text(
        json.dumps(ast, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    arbol = fuente + "\n\n" + formatear_arbol(ast) + "\n"
    (RAIZ / "ejemplos/arbol_v04.txt").write_text(arbol, encoding="utf-8")
    (destino / "arbol.html").write_text(pagina("AgroReglas: AST de V04", arbol), encoding="utf-8")
    print("Evidencia generada en docs/evidencias y ejemplos.")


if __name__ == "__main__":
    main()
