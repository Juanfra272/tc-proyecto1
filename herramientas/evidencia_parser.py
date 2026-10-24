"""Regenera resultados, la tabla de los 25 casos y las páginas de evidencia.

Ejecutar desde la raíz: python -m herramientas.evidencia_parser
Las capturas PNG se toman después de abrir las páginas HTML resultantes.
"""

import html
import json
from pathlib import Path
import shlex
import subprocess
import sys

from agroreglas import analizar_programa
from agroreglas.arbol import formatear_arbol
from herramientas.demo_parser import cargar_casos, resultado

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
<p>Salida real de Python.</p>
<pre>{html.escape(salida)}</pre></main></html>'''


def tabla_casos(casos):
    """Tabla del enunciado: entrada, resultado esperado, obtenido y observación."""
    lineas = ["Resultados de los 25 casos de prueba", "",
              "Generado por python -m herramientas.evidencia_parser. Cada rechazo indica la línea y la columna del primer error. Todos son sintácticos salvo L05, que es léxico. Los mensajes completos están en docs/evidencias/ejecucion.txt.", "",
              "| ID | Entrada | Esperado | Obtenido | Observación |",
              "| --- | --- | --- | --- | --- |"]
    coinciden = 0
    for caso in casos:
        _, error = resultado(caso["entrada"])
        obtenido = "aceptar"
        if error:
            lugar = getattr(error, "token", error)
            obtenido = f"rechazar, {lugar.linea}:{lugar.columna}"
        coinciden += obtenido.startswith(caso["resultado_esperado"])
        entrada = caso["entrada"].replace("\n", "\\n").replace("\t", "\\t")
        lineas.append(f"| {caso['id']} | `{entrada}` | {caso['resultado_esperado']} | {obtenido} | {caso['propiedad']} |")
    lineas += ["", f"Coinciden {coinciden} de {len(casos)} resultados con lo esperado.", ""]
    return "\n".join(lineas)


def ejecutar_cli(*argumentos):
    proceso = subprocess.run([sys.executable, "-m", "agroreglas", *argumentos],
                             cwd=RAIZ, capture_output=True, text=True)
    return f"$ python -m agroreglas {shlex.join(argumentos)}\n{proceso.stdout}(código de salida {proceso.returncode})\n"


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
    # Dos páginas, casos de Fernando y casos nuevos, para que cada captura sea legible en el informe.
    previos, nuevos = salida.split("AST del caso V04:")[0].split("\nV06:")
    (destino / "ejecucion.html").write_text(
        pagina("AgroReglas: casos V01 a I05", previos), encoding="utf-8")
    (destino / "ejecucion-nuevos.html").write_text(
        pagina("AgroReglas: casos V06 a L05", "V06:" + nuevos), encoding="utf-8")
    casos = cargar_casos()
    (RAIZ / "docs/resultados_casos.txt").write_text(tabla_casos(casos), encoding="utf-8")
    cli = (ejecutar_cli("ejemplos/riego.agro") + "\n"
           + ejecutar_cli("ejemplos/error.agro") + "\n"
           + ejecutar_cli("--texto", "WHEN humedad < 3.5 THEN abrir valvula;"))
    (destino / "cli.txt").write_text(cli, encoding="utf-8")
    (destino / "cli.html").write_text(pagina("AgroReglas: ejecución desde archivo y texto", cli), encoding="utf-8")
    fuente = next(c["entrada"] for c in casos if c["id"] == "V04")
    ast = analizar_programa(fuente)
    (RAIZ / "ejemplos/arbol_v04.json").write_text(
        json.dumps(ast, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    arbol = fuente + "\n\n" + formatear_arbol(ast) + "\n"
    (RAIZ / "ejemplos/arbol_v04.txt").write_text(arbol, encoding="utf-8")
    (destino / "arbol.html").write_text(pagina("AgroReglas: AST de V04", arbol), encoding="utf-8")
    print("Evidencia generada en docs/evidencias, docs/resultados_casos.txt y ejemplos.")


if __name__ == "__main__":
    main()
