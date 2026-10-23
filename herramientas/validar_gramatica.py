"""Comprueba propiedades estáticas de la GLC; no reconoce entradas ni crea AST.

Solo biblioteca estándar. [] representa epsilon; $ es el fin de entrada.
"""

import argparse
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EPS = "ε"


def analizar(g):
    reglas = g["producciones"]
    nt, terminales = set(reglas), set(g["terminales"])
    assert g["inicial"] in nt, "Símbolo inicial desconocido"
    assert not nt & terminales, "Terminales y no terminales se superponen"
    assert g["fin"] not in nt | terminales, "Fin reservado"
    assert EPS not in nt | terminales, "Epsilon se representa con []"
    assert len(terminales) == len(g["terminales"]), "Terminales repetidos"
    for a, alternativas in reglas.items():
        assert alternativas, f"Sin producciones: {a}"
        for rhs in alternativas:
            assert all(s in nt | terminales for s in rhs), f"Símbolo desconocido en {a}"

    first = {a: set() for a in nt}

    def primero(secuencia):
        resultado = set()
        for s in secuencia:
            fs = {s} if s in terminales else first[s]
            resultado |= fs - {EPS}
            if EPS not in fs:
                return resultado
        return resultado | {EPS}

    cambio = True
    while cambio:
        cambio = False
        for a, alternativas in reglas.items():
            for rhs in alternativas:
                anterior = len(first[a])
                first[a] |= primero(rhs)
                cambio |= len(first[a]) != anterior

    follow = {a: set() for a in nt}
    follow[g["inicial"]].add(g["fin"])
    cambio = True
    while cambio:
        cambio = False
        for a, alternativas in reglas.items():
            for rhs in alternativas:
                for i, s in enumerate(rhs):
                    if s in nt:
                        sufijo = primero(rhs[i + 1:])
                        nuevos = sufijo - {EPS}
                        if EPS in sufijo:
                            nuevos |= follow[a]
                        anterior = len(follow[s])
                        follow[s] |= nuevos
                        cambio |= len(follow[s]) != anterior

    # Un ciclo en la relación de esquinas izquierdas implica recursión izquierda.
    esquinas = {a: set() for a in nt}
    for a, alternativas in reglas.items():
        for rhs in alternativas:
            for s in rhs:
                if s in terminales:
                    break
                esquinas[a].add(s)
                if EPS not in first[s]:
                    break
    for _ in nt:
        for a in nt:
            esquinas[a] |= set().union(*(esquinas[b] for b in tuple(esquinas[a])))
    izquierda = sorted(a for a in nt if a in esquinas[a])

    alcanzables = {g["inicial"]}
    productivos = set()
    cambio = True
    while cambio:
        antes = (len(alcanzables), len(productivos))
        for a, alternativas in reglas.items():
            if a in alcanzables:
                alcanzables.update(s for rhs in alternativas for s in rhs if s in nt)
            if any(all(s in terminales | productivos for s in rhs) for rhs in alternativas):
                productivos.add(a)
        cambio = antes != (len(alcanzables), len(productivos))

    tabla, producciones, conflictos = {}, [], []
    for a, alternativas in reglas.items():
        for rhs in alternativas:
            numero = len(producciones) + 1
            seleccion = primero(rhs) - {EPS}
            if EPS in primero(rhs):
                seleccion |= follow[a]
            producciones.append((numero, a, rhs, seleccion))
            for t in sorted(seleccion):
                clave = (a, t)
                if clave in tabla:
                    conflictos.append((a, t, tabla[clave], numero))
                else:
                    tabla[clave] = numero
    return first, follow, tabla, producciones, conflictos, izquierda, nt - alcanzables, nt - productivos


def informe(g, resultado):
    first, follow, tabla, producciones, conflictos, izquierda, inaccesibles, improductivos = resultado

    def conjunto(xs):
        return "{ " + ", ".join(sorted(xs)) + " }"

    lineas = ["Resultados reproducibles de AgroReglas 1.0", "",
              "Generado por python herramientas/validar_gramatica.py --escribir.", "",
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
               "Cada número remite a una producción. error representa una celda vacía.", "",
               "| No terminal | " + " | ".join(columnas) + " |",
               "| " + " | ".join(["---"] * (len(columnas) + 1)) + " |"]
    for a in g["producciones"]:
        lineas.append("| " + a + " | " + " | ".join(str(tabla.get((a, t), "error")) for t in columnas) + " |")
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
    assert r[0] == {"S": {"a", "b"}, "A": {"a", EPS}}
    assert r[1] == {"S": {"$"}, "A": {"b"}}
    assert not r[4] and not r[5]
    assert analizar(gramatica({"S": [["a"], ["a", "b"]]}))[4]
    assert analizar(gramatica({"S": [["A", "a"]], "A": [["S"], []]}))[5] == ["A", "S"]
    assert analizar(gramatica({"S": [["A", "a"]], "A": [["a"], []]}))[4]


def main():
    if not __debug__:
        raise SystemExit("Validación deshabilitada con -O: ejecute Python sin optimizaciones para conservar los controles.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="Regenera las tablas documentadas")
    args = parser.parse_args()
    autocontrol()
    g = json.loads((RAIZ / "especificacion/gramatica.json").read_text())
    resultado = analizar(g)
    assert not any(resultado[i] for i in (4, 5, 6, 7)), "La gramática no supera la validación"
    contenido = informe(g, resultado)
    destino = RAIZ / "docs/fernando/first_follow_tabla.txt"
    if args.escribir:
        destino.write_text(contenido, encoding="utf-8")
    else:
        assert destino.read_text(encoding="utf-8") == contenido, "Tablas desactualizadas; use --escribir"
    print(f"OK: {len(resultado[3])} producciones; {len(resultado[2])} celdas; 0 conflictos; autocontroles correctos.")


if __name__ == "__main__":
    main()
