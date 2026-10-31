"""Reconocimiento LL(1) con pila explícita y construcción de AST sin recursión.

La entrada son los pares (tipo, lexema) del notebook y el texto original.
La gramática y la tabla se obtienen de la especificación del proyecto.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from .gramatica import analizar


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    desplazamiento: int
    linea: int
    columna: int


class ErrorSintactico(ValueError):
    """Primer error, con datos estructurados para las pruebas y la CLI."""

    def __init__(self, token, simbolo, esperados):
        self.token = token
        self.simbolo_pendiente = simbolo
        encontrado = "fin de entrada" if token.tipo == "$" else repr(token.lexema)
        nombres = {
            "NUM": "un número", "TRUE": "TRUE", "FALSE": "FALSE",
            "ID": "un identificador", "PARENT_IZQ": "'('",
            "PARENT_DER": "')' para cerrar el grupo",
            "OP_REL": "un operador relacional (>, <, >=, <=, ==, !=)",
            "THEN": "THEN", "AND": "AND", "OR": "OR", "NOT": "NOT",
            "WHEN": "WHEN", "$": "fin de entrada",
            "PUNTO_COMA": "';' al final de la regla",
        }
        self.tokens_esperados = tuple(t for t in nombres if t in esperados)
        textos = [nombres[t] for t in self.tokens_esperados]
        esperado = textos[-1] if len(textos) == 1 else ", ".join(textos[:-1]) + " o " + textos[-1]
        super().__init__(
            f"Error sintáctico en línea {token.linea}, columna {token.columna} "
            f"(desplazamiento {token.desplazamiento}): se esperaba {esperado}; "
            f"se encontró {encontrado}."
        )

    def como_dict(self):
        return {
            "desplazamiento": self.token.desplazamiento,
            "linea": self.token.linea,
            "columna": self.token.columna,
            "token_encontrado": self.token.tipo,
            "lexema_encontrado": self.token.lexema,
            "simbolo_pendiente": self.simbolo_pendiente,
            "tokens_esperados": list(self.tokens_esperados),
        }


def _ubicar(tokens, fuente):
    """Añade ubicaciones sin duplicar ni modificar las reglas del lexer.

    Comprueba que los lexemas cubran el texto salvo los espacios del notebook.
    El marcador EOF se crea aquí; no debe venir en la secuencia del llamador.
    """
    ubicados = []
    posicion, linea, columna = 0, 1, 1

    def avanzar(texto):
        nonlocal posicion, linea, columna
        posicion += len(texto)
        saltos = texto.count("\n")
        if saltos:
            linea += saltos
            columna = len(texto.rsplit("\n", 1)[1]) + 1
        else:
            columna += len(texto)

    for tipo, lexema in tokens:
        while posicion < len(fuente) and fuente[posicion] in " \t\n":
            avanzar(fuente[posicion])
        if tipo == "$" or not lexema or not fuente.startswith(lexema, posicion):
            raise ValueError(f"Tokens y fuente no coinciden en desplazamiento {posicion}.")
        ubicados.append(Token(tipo, lexema, posicion, linea, columna))
        avanzar(lexema)
    fin = (posicion, linea, columna)
    while posicion < len(fuente) and fuente[posicion] in " \t\n":
        avanzar(fuente[posicion])
    if posicion != len(fuente):
        raise ValueError(f"Hay texto sin tokenizar en desplazamiento {posicion}.")
    ubicados.append(Token("$", "", *fin))
    return ubicados


def _cargar_tabla():
    ruta = Path(__file__).resolve().parents[1] / "especificacion" / "gramatica.json"
    gramatica = json.loads(ruta.read_text(encoding="utf-8"))
    resultado = analizar(gramatica)
    tabla, producciones = resultado.tabla, resultado.producciones
    if resultado.conflictos or resultado.izquierda:
        raise ValueError("La gramática debe ser LL(1) y no tener recursión izquierda.")
    reglas = {numero: (a, tuple(rhs)) for numero, a, rhs, _ in producciones}
    esperados = {
        a: {t for fila, t in tabla if fila == a}
        for a in gramatica["producciones"]
    }
    return gramatica, tabla, reglas, esperados


_GRAMATICA, _TABLA, _REGLAS, _ESPERADOS = _cargar_tabla()


def _lista_cola(cola):
    # Las colas enlazadas evitan copiar listas en cada reducción de Resto.
    while cola is not None:
        primero, cola = cola
        yield primero


def _reducir(simbolo, hijos):
    """Acciones semánticas por no terminal, siguiendo las 18 producciones."""
    if simbolo == "Programa":
        return {"tipo": "Programa", "reglas": [hijos[0], *_lista_cola(hijos[1])]}
    if simbolo == "Resto":
        return (hijos[0], hijos[1]) if hijos else None
    if simbolo == "Regla":
        return {"tipo": "Regla", "condicion": hijos[1], "accion": hijos[3]}
    if simbolo in {"Expr", "Termino"}:
        resultado = hijos[0]
        for operador, derecho in _lista_cola(hijos[1]):
            resultado = {"tipo": "Logica", "operador": operador,
                         "izquierda": resultado, "derecha": derecho}
        return resultado
    if simbolo in {"ColaOR", "ColaAND"}:
        return ((hijos[0].tipo, hijos[1]), hijos[2]) if hijos else None
    if simbolo == "Unaria":
        if len(hijos) == 1:
            return hijos[0]
        if hijos[0].tipo == "NOT":
            return {"tipo": "Negacion", "operando": hijos[1]}
        return hijos[1]  # Los paréntesis ya quedan reflejados en la estructura.
    if simbolo == "Comparacion":
        return {"tipo": "Comparacion", "identificador": hijos[0].lexema,
                "operador": hijos[1].lexema, "valor": hijos[2]}
    if simbolo == "Valor":
        token = hijos[0]
        # El literal se conserva como texto: el AST es sintáctico y así no hereda
        # el límite de dígitos que Python impone al convertir texto en entero.
        if token.tipo == "NUM":
            return {"tipo": "Numero", "valor": token.lexema}
        return {"tipo": "Booleano", "valor": token.tipo == "TRUE"}
    if simbolo == "Accion":
        return {"tipo": "Accion", "verbo": hijos[0].lexema, "destino": hijos[1].lexema}
    raise ValueError(f"Sin acción semántica para {simbolo}.")


def analizar_tokens(tokens, fuente, traza=None):
    """Devuelve un AST JSON o lanza ErrorSintactico en el primer fallo.

    tokens: iterable de pares (tipo, lexema), sin EOF.
    fuente: texto exacto que recibió el lexer, necesario para las ubicaciones.
    traza: lista opcional que recibe (pila, entrada, acción) en cada paso del
    reconocimiento; el informe la usa para mostrar la tabla en funcionamiento.
    No ejecuta acciones agrícolas ni verifica tipos o nombres del dominio.
    """
    entrada = _ubicar(tokens, fuente)
    # Cada tupla marca una reducción pendiente (no terminal, cantidad de hijos).
    pila = ["$", _GRAMATICA["inicial"]]
    valores = []
    indice = 0
    while pila:
        simbolo = pila.pop()
        if isinstance(simbolo, tuple):
            nombre, cantidad = simbolo
            hijos = valores[-cantidad:] if cantidad else []
            if cantidad:
                del valores[-cantidad:]
            valores.append(_reducir(nombre, hijos))
            continue
        actual = entrada[indice]
        if traza is not None:
            simbolos = [s for s in pila if not isinstance(s, tuple)] + [simbolo]
            restante = [t.lexema or t.tipo for t in entrada[indice:]]
            traza.append([" ".join(simbolos), " ".join(restante), ""])
        if simbolo in _GRAMATICA["producciones"]:
            numero = _TABLA.get((simbolo, actual.tipo))
            if traza is not None:
                traza[-1][2] = (f"error: M[{simbolo}, {actual.tipo}] vacía" if numero is None else
                                f"{numero}: {simbolo} → " + (" ".join(_REGLAS[numero][1]) or "ε"))
            if numero is None:
                esperados = _ESPERADOS[simbolo]
                # FOLLOW reúne todos los contextos; aquí solo se cierran grupos abiertos.
                if "PARENT_DER" in pila:
                    esperados = esperados - {"THEN"}
                else:
                    esperados = esperados - {"PARENT_DER"}
                raise ErrorSintactico(actual, simbolo, esperados)
            _, rhs = _REGLAS[numero]
            pila.append((simbolo, len(rhs)))
            pila.extend(reversed(rhs))
        else:
            if traza is not None:
                traza[-1][2] = ("aceptar" if simbolo == "$" == actual.tipo else
                                f"coincide {simbolo}" if actual.tipo == simbolo else
                                f"error: se esperaba {simbolo}")
            if actual.tipo != simbolo:
                raise ErrorSintactico(actual, simbolo, {simbolo})
            if simbolo != "$":
                valores.append(actual)
            indice += 1
    return valores[0]
