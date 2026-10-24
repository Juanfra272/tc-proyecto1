"""Presentación jerárquica del AST, sin librerías gráficas ni recursión."""


def formatear_arbol(ast):
    pendientes = [(ast, 0)]
    lineas = []
    while pendientes:
        nodo, profundidad = pendientes.pop()
        tipo = nodo["tipo"]
        hijos = []
        etiqueta = tipo
        if tipo == "Programa":
            hijos = nodo["reglas"]
        elif tipo == "Regla":
            hijos = [nodo["condicion"], nodo["accion"]]
        elif tipo == "Logica":
            etiqueta = nodo["operador"]
            hijos = [nodo["izquierda"], nodo["derecha"]]
        elif tipo == "Negacion":
            etiqueta = "NOT"
            hijos = [nodo["operando"]]
        elif tipo == "Comparacion":
            etiqueta = f"Comparacion {nodo['identificador']} {nodo['operador']}"
            hijos = [nodo["valor"]]
        elif tipo == "Booleano":
            etiqueta = "Booleano " + ("TRUE" if nodo["valor"] else "FALSE")
        elif tipo == "Numero":
            etiqueta = f"{tipo} {nodo['valor']}"
        elif tipo == "Accion":
            etiqueta = f"Accion {nodo['verbo']} {nodo['destino']}"
        lineas.append("  " * profundidad + etiqueta)
        pendientes.extend((hijo, profundidad + 1) for hijo in reversed(hijos))
    return "\n".join(lineas)
