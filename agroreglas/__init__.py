"""Parser propio de AgroReglas; el lexer se proporciona por separado."""

from .parser import ErrorSintactico, analizar_tokens

__all__ = ["ErrorSintactico", "analizar_tokens"]
