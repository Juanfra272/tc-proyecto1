"""Cálculo de conjuntos y tabla predictiva de una gramática."""

from dataclasses import dataclass

EPS = "ε"


@dataclass(frozen=True)
class ResultadoGramatica:
    first: dict
    follow: dict
    tabla: dict
    producciones: list
    conflictos: list
    izquierda: list
    inaccesibles: set
    improductivos: set


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
    return ResultadoGramatica(first, follow, tabla, producciones, conflictos, izquierda,
                              nt - alcanzables, nt - productivos)

