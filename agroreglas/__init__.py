"""Analizador de AgroReglas: lexer del docente, parser LL(1) propio y AST."""

from .lexer import ErrorLexico, analizador_lexico
from .parser import ErrorSintactico, analizar_tokens


def analizar_programa(fuente):
    """Tokeniza y analiza un texto completo; lanza ErrorLexico o ErrorSintactico."""
    return analizar_tokens(analizador_lexico(fuente), fuente)


__all__ = ["ErrorLexico", "ErrorSintactico", "analizador_lexico",
           "analizar_programa", "analizar_tokens"]
