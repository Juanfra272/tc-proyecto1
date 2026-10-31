"""Comprueba propiedades estáticas de la GLC; no reconoce entradas ni crea AST.

Solo biblioteca estándar. [] representa epsilon; $ es el fin de entrada.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from agroreglas.gramatica import EPS, analizar


def informe(g, resultado):
    first, follow, tabla = resultado.first, resultado.follow, resultado.tabla
    producciones, conflictos, izquierda = resultado.producciones, resultado.conflictos, resultado.izquierda
    inaccesibles, improductivos = resultado.inaccesibles, resultado.improductivos

    def conjunto(xs):
        return "{ " + ", ".join(sorted(xs)) + " }"

    lineas = ["Resultados reproducibles de AgroReglas 1.0", "",
              "Producciones y conjuntos SELECT", "",
              "| N.º | Producción | SELECT |", "| --- | --- | --- |"]
    for n, a, rhs, seleccion in producciones:
        lineas.append(f"| {n} | {a} → {' '.join(rhs) or EPS} | {conjunto(seleccion)} |")
    lineas += ["", "FIRST y FOLLOW completos", "",
               "| No terminal | FIRST | FOLLOW |", "| --- | --- | --- |"]
    for a in g["producciones"]:
        lineas.append(f"| {a} | {conjunto(first[a])} | {conjunto(follow[a])} |")
    columnas = g["terminales"] + [g["fin"]]
    lineas += ["", "Tabla predictiva LL(1)", "",
               "Cada número remite a una producción. Una celda vacía indica error sintáctico.", "",
               "| No terminal | " + " | ".join(columnas) + " |",
               "| " + " | ".join(["---"] * (len(columnas) + 1)) + " |"]
    for a in g["producciones"]:
        lineas.append("| " + a + " | " + " | ".join(str(tabla.get((a, t), "")) for t in columnas) + " |")
    lineas += ["", "Comprobaciones", "",
               f"- {len(g['producciones'])} no terminales, {len(g['terminales'])} terminales y {len(producciones)} producciones.",
               f"- {len(tabla)} celdas ocupadas de {len(g['producciones']) * len(columnas)}.",
               f"- Conflictos LL(1): {len(conflictos)}.",
               f"- No terminales con recursión izquierda: {conjunto(izquierda)}.",
               f"- No terminales inaccesibles: {conjunto(inaccesibles)}.",
               f"- No terminales improductivos: {conjunto(improductivos)}.", ""]
    return "\n".join(lineas)


def autocontrol():
    # Casos de control del análisis estático; no son pruebas del parser del proyecto.
    def gramatica(reglas):
        return {"inicial": "S", "fin": "$", "terminales": ["a", "b"], "producciones": reglas}

    r = analizar(gramatica({"S": [["A", "b"]], "A": [["a", "A"], []]}))
    assert r.first == {"S": {"a", "b"}, "A": {"a", EPS}}
    assert r.follow == {"S": {"$"}, "A": {"b"}}
    assert not r.conflictos and not r.izquierda
    assert analizar(gramatica({"S": [["a"], ["a", "b"]]})).conflictos
    assert analizar(gramatica({"S": [["A", "a"]], "A": [["S"], []]})).izquierda == ["A", "S"]
    assert analizar(gramatica({"S": [["A", "a"]], "A": [["a"], []]})).conflictos


def main():
    if not __debug__:
        raise SystemExit("Validación deshabilitada con -O: ejecute Python sin optimizaciones para conservar los controles.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="Regenera las tablas documentadas")
    args = parser.parse_args()
    autocontrol()
    g = json.loads((RAIZ / "especificacion/gramatica.json").read_text())
    resultado = analizar(g)
    assert not any((resultado.conflictos, resultado.izquierda, resultado.inaccesibles, resultado.improductivos)), "La gramática no supera la validación"
    contenido = informe(g, resultado)
    destino = RAIZ / "docs/first_follow_tabla.txt"
    if args.escribir:
        destino.write_text(contenido, encoding="utf-8")
    else:
        assert destino.read_text(encoding="utf-8") == contenido, "Las tablas no están actualizadas; use --escribir"
    print(f"OK: {len(resultado.producciones)} producciones; {len(resultado.tabla)} celdas; 0 conflictos; autocontroles correctos.")


if __name__ == "__main__":
    main()
