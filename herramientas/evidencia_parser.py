"""Regenera las salidas de texto que respaldan el informe.

Ejecutar desde la raíz: python -m herramientas.evidencia_parser
Escribe docs/resultados_casos.txt, docs/traza_ll1.txt, docs/evidencias/*.txt y los
AST de V03 y V04 en ejemplos. El informe copia estas salidas en informe/informe.tex;
tras un cambio en el parser o en los casos, compara y actualiza esas tablas a mano.
"""

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


def tabla_casos(casos):
    """Tabla del enunciado: entrada, resultado esperado, obtenido y observación."""
    filas = ["| ID | Entrada | Esperado | Obtenido | Observación |", "| --- | --- | --- | --- | --- |"]
    coinciden = 0
    for caso in casos:
        _, error = resultado(caso["entrada"])
        obtenido = "aceptar"
        if error:
            obtenido = f"rechazar. {error}"
        coinciden += obtenido.startswith(caso["resultado_esperado"])
        entrada = caso["entrada"].replace("\n", "\\n").replace("\t", "\\t")
        filas.append(f"| {caso['id']} | `{entrada}` | {caso['resultado_esperado']} | {obtenido} | {caso['propiedad']} |")
    return "\n".join(["Resultados de los casos de prueba", "", *filas, "",
                      f"Coinciden {coinciden} de {len(casos)} resultados con lo esperado.", ""])


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
        "La pila se escribe con la cima a la derecha y la entrada muestra los lexemas pendientes. "
        "Las marcas que construyen el AST no se muestran.", "",
        f"V01: `{fuentes['V01']}`", "", traza(fuentes["V01"]), "",
        f"I04: `{fuentes['I04']}`", "", traza(fuentes["I04"]), ""])


def ejecutar(comando):
    proceso = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True)
    return proceso


def cli(*argumentos):
    proceso = ejecutar([sys.executable, "-m", "agroreglas", *argumentos])
    return f"$ python -m agroreglas {shlex.join(argumentos)}\n{proceso.stdout}(código de salida {proceso.returncode})\n"


def main():
    destino = RAIZ / "docs/evidencias"
    destino.mkdir(parents=True, exist_ok=True)
    demo = ejecutar([sys.executable, "-m", "herramientas.demo_parser"])
    pruebas = ejecutar([sys.executable, "-m", "unittest", "discover", "-s", "pruebas", "-v"])
    (destino / "ejecucion.txt").write_text("$ python -m herramientas.demo_parser\n" + demo.stdout, encoding="utf-8")
    (destino / "pruebas.txt").write_text(pruebas.stdout + pruebas.stderr, encoding="utf-8")
    cli_salida = "\n".join([cli("ejemplos/riego.agro"), cli("ejemplos/error.agro"),
                            cli("--texto", "WHEN humedad < 3.5 THEN abrir valvula;")])
    (destino / "cli.txt").write_text(cli_salida, encoding="utf-8")
    casos = cargar_casos()
    (RAIZ / "docs/resultados_casos.txt").write_text(tabla_casos(casos), encoding="utf-8")
    (RAIZ / "docs/traza_ll1.txt").write_text(documento_traza(casos), encoding="utf-8")
    for identificador in ("V03", "V04"):
        fuente = next(c["entrada"] for c in casos if c["id"] == identificador)
        ast = analizar_programa(fuente)
        nombre = RAIZ / f"ejemplos/arbol_{identificador.lower()}"
        nombre.with_suffix(".json").write_text(json.dumps(ast, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        nombre.with_suffix(".txt").write_text(fuente + "\n\n" + formatear_arbol(ast) + "\n", encoding="utf-8")
    if pruebas.returncode or demo.returncode:
        raise SystemExit("Las pruebas o la demostración fallaron; revisa docs/evidencias.")
    print("Salidas regeneradas en docs, docs/evidencias y ejemplos.")


if __name__ == "__main__":
    main()
