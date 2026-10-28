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

from agroreglas import analizador_lexico, analizar_programa
from agroreglas.arbol import formatear_arbol
from agroreglas.parser import analizar_tokens
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
              "Generado por python -m herramientas.evidencia_parser. Cada rechazo indica la línea y la columna del primer error. Todos son sintácticos salvo L05, que es léxico. El mensaje completo de cada rechazo aparece en la tabla siguiente.", "",
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
    lineas += ["", f"Coinciden {coinciden} de {len(casos)} resultados con lo esperado.", "",
               "Mensajes de los rechazos", "",
               "Texto exacto que entrega el analizador en cada caso rechazado.", "",
               "| ID | Mensaje |", "| --- | --- |"]
    for caso in casos:
        _, error = resultado(caso["entrada"])
        if error:
            lineas.append(f"| {caso['id']} | {error} |")
    return "\n".join(lineas) + "\n"


def traza(fuente):
    """Pasos del reconocimiento LL(1) como tabla: pila, entrada restante y acción."""
    pasos = []
    try:
        analizar_tokens(analizador_lexico(fuente), fuente, pasos)
    except ValueError:
        pass  # La traza termina en la fila del error.
    filas = [f"| {n} | `{pila}` | `{entrada}` | {accion} |"
             for n, (pila, entrada, accion) in enumerate(pasos, 1)]
    return "\n".join(["| Paso | Pila | Entrada | Acción |", "| --- | --- | --- | --- |", *filas])


def documento_traza(casos):
    fuentes = {c["id"]: c["entrada"] for c in casos}
    return "\n".join([
        "Traza del análisis LL(1)", "",
        "Generado por `python -m herramientas.evidencia_parser` con el mismo parser que analiza los casos. La pila se escribe con la cima a la derecha. La entrada muestra los lexemas pendientes; la tabla se consulta con su tipo de token. Cuando la cima es un no terminal A y el token es de tipo t, la acción indica la producción M[A, t]; cuando es un terminal, indica si coincide con el token. Las marcas de reducción que construyen el AST no se muestran, porque no son símbolos de la gramática.", "",
        "Traza de V01", "",
        f"Entrada: `{fuentes['V01']}`. La regla mínima recorre todas las filas que necesita una comparación numérica. Las colas ColaAND y ColaOR derivan ε ante THEN, y Resto deriva ε ante el fin de entrada.", "",
        traza(fuentes["V01"]), "",
        "Traza de I04", "",
        f"Entrada: `{fuentes['I04']}`. El grupo abierto apila PARENT_DER. Ante THEN, la tabla permite cerrar las colas internas con ε porque THEN pertenece a FOLLOW de ColaAND y ColaOR; el error aparece al cotejar el terminal PARENT_DER con THEN.", "",
        traza(fuentes["I04"]), ""])


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
    # Una página por grupo de cinco casos, para que cada captura sea legible en el informe.
    bloques = demo.stdout.split("AST del caso V04:")[0].split("\n\n")
    for grupo in ("V01", "I01", "V06", "I06", "L01"):
        inicio = next(i for i, b in enumerate(bloques) if b.lstrip().startswith(grupo + ":"))
        texto = "\n\n".join(b.strip("\n") for b in bloques[inicio:inicio + 5]) + "\n"
        ultimo = texto.rsplit("\n\n", 1)[-1].split(":")[0]
        (destino / f"ejecucion-{grupo.lower()}.html").write_text(
            pagina(f"AgroReglas: casos {grupo} a {ultimo}", texto), encoding="utf-8")
    casos = cargar_casos()
    (RAIZ / "docs/resultados_casos.txt").write_text(tabla_casos(casos), encoding="utf-8")
    (RAIZ / "docs/traza_ll1.txt").write_text(documento_traza(casos), encoding="utf-8")
    cli = (ejecutar_cli("ejemplos/riego.agro") + "\n"
           + ejecutar_cli("ejemplos/error.agro") + "\n"
           + ejecutar_cli("--texto", "WHEN humedad < 3.5 THEN abrir valvula;"))
    (destino / "cli.txt").write_text(cli, encoding="utf-8")
    (destino / "cli.html").write_text(pagina("AgroReglas: ejecución desde archivo y texto", cli), encoding="utf-8")
    for identificador in ("V03", "V04"):
        fuente = next(c["entrada"] for c in casos if c["id"] == identificador)
        ast = analizar_programa(fuente)
        nombre = "ejemplos/arbol_" + identificador.lower()
        (RAIZ / (nombre + ".json")).write_text(
            json.dumps(ast, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        arbol = fuente + "\n\n" + formatear_arbol(ast) + "\n"
        (RAIZ / (nombre + ".txt")).write_text(arbol, encoding="utf-8")
        if identificador == "V04":
            (destino / "arbol.html").write_text(pagina("AgroReglas: AST de V04", arbol), encoding="utf-8")
    print("Evidencia generada en docs/evidencias, docs/resultados_casos.txt, docs/traza_ll1.txt y ejemplos.")


if __name__ == "__main__":
    main()
