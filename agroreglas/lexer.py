"""Lexer del docente, extraído de anlizador_lexico1.ipynb sin cambiar sus reglas.

La única diferencia es ErrorLexico, que sigue siendo ValueError y además ubica
el carácter rechazado con el mismo criterio que los errores sintácticos.
"""

import re

ESPECIFICACION_TOKENS = [
    ('NUM',        r'\d+'),
    ('OP_REL',     r'>=|<=|==|!=|>|<'),
    ('PUNTO_COMA', r';'),
    ('PARENT_IZQ', r'\('),
    ('PARENT_DER', r'\)'),
    ('ID',         r'[A-Za-z_][A-Za-z0-9_]*'),
    ('ESPACIO',    r'[ \t\n]+'),
    ('ERROR',      r'.')
]

PATRON = re.compile('|'.join(
    f'(?P<{nombre}>{expresion})'
    for nombre, expresion in ESPECIFICACION_TOKENS
))

PALABRAS_RESERVADAS = {'WHEN', 'THEN', 'AND', 'OR', 'NOT', 'TRUE', 'FALSE'}


class ErrorLexico(ValueError):
    """Carácter fuera del alfabeto; desplazamiento desde 0, línea y columna desde 1."""

    def __init__(self, lexema, desplazamiento, cadena):
        self.lexema = lexema
        self.desplazamiento = desplazamiento
        self.linea = cadena.count("\n", 0, desplazamiento) + 1
        self.columna = desplazamiento - cadena.rfind("\n", 0, desplazamiento)
        super().__init__(
            f"Error léxico en línea {self.linea}, columna {self.columna} "
            f"(desplazamiento {desplazamiento}): símbolo no reconocido {lexema!r}."
        )

    def como_dict(self):
        return {
            "desplazamiento": self.desplazamiento,
            "linea": self.linea,
            "columna": self.columna,
            "lexema_encontrado": self.lexema,
        }


def analizador_lexico(cadena):
    """
    Convierte una cadena de entrada en una lista de tokens.
    Retorna:
        [(TIPO_TOKEN, lexema), ...]
    """
    tokens = []

    for coincidencia in PATRON.finditer(cadena):

        tipo = coincidencia.lastgroup
        lexema = coincidencia.group()

        if tipo == 'ESPACIO':
            continue

        elif tipo == 'ID' and lexema.upper() in PALABRAS_RESERVADAS:
            tipo = lexema.upper()

        elif tipo == 'ERROR':
            raise ErrorLexico(lexema, coincidencia.start(), cadena)

        tokens.append((tipo, lexema))

    return tokens
