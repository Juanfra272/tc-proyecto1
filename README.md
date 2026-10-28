# AgroReglas

AgroReglas es un lenguaje de reglas para monitoreo agrícola. Una regla relaciona lecturas de sensores con una acción sobre un dispositivo:

```text
WHEN humedad < 30 AND lluvia == FALSE THEN abrir valvula;
```

El proyecto incluye la gramática LL(1) del lenguaje, un parser predictivo con tabla y pila explícita escrito sin generadores de parsers, la construcción del AST y mensajes de error con línea y columna. Es el proyecto 1 de Teoría de la Computación (INFO1148).

## Requisitos

Python 3.10 o posterior. Solo usa la biblioteca estándar, así que no hay dependencias que instalar.

## Uso

Ejecuta todos los comandos desde la raíz del repositorio.

```sh
python -m agroreglas ejemplos/riego.agro
python -m agroreglas --texto "WHEN humedad < 30 THEN abrir valvula;"
python -m agroreglas ejemplos/riego.agro --json
```

Si el programa es válido, se imprime `ACEPTADO` y el AST como árbol; con `--json`, el mismo AST en JSON:

```text
ACEPTADO. 1 regla.

Programa
  Regla
    Comparacion humedad <
      Numero 30
    Accion abrir valvula
```

Si es inválido, se imprime el primer error y se señala su posición:

```text
$ python -m agroreglas ejemplos/error.agro
RECHAZADO. Error sintáctico en línea 3, columna 2 (desplazamiento 77): se esperaba ')' para cerrar el grupo; se encontró 'THEN'.
  	THEN desplegar malla;
  	^
```

El código de salida es 0 al aceptar, 1 al rechazar y 2 si el archivo no se puede leer.

Desde Python:

```python
from agroreglas import analizar_programa

ast = analizar_programa("WHEN nivel == 0 THEN apagar bomba;")
```

`analizar_programa` lanza `ErrorLexico` o `ErrorSintactico`. Ambos son subclases de `ValueError` y ofrecen `como_dict()` con la ubicación del error.

## Formato de entrada

Un programa es texto UTF-8 con una o más reglas de la forma `WHEN condición THEN verbo destino;`.

- La condición es una comparación `identificador operador valor`, con los operadores `>`, `<`, `>=`, `<=`, `==` y `!=`, y un valor que es un entero sin signo, `TRUE` o `FALSE`.
- Las comparaciones se combinan con `AND` y `OR`, se niegan con `NOT` y se agrupan con paréntesis. `NOT` tiene más prioridad que `AND`, y `AND` más que `OR`.
- La acción son dos identificadores: verbo y destino.
- Las palabras reservadas no distinguen mayúsculas de minúsculas. Los espacios, tabuladores y saltos de línea solo separan tokens; los saltos CRLF de Windows y el BOM inicial se normalizan antes de analizar.

```text
WHEN humedad < 30 AND lluvia == FALSE THEN abrir valvula;
WHEN NOT (temperatura < 35 OR sombra == TRUE) THEN desplegar malla;
WHEN nivel == 0 THEN apagar bomba;
```

No hay comentarios, números negativos ni decimales.

## Pruebas

```sh
python -m unittest discover -s pruebas -v
python herramientas/validar_gramatica.py
```

La primera ejecuta 23 pruebas, entre ellas los 25 casos de `especificacion/casos.json`: 10 válidos, 10 inválidos y 5 casos límite. La segunda vuelve a calcular FIRST, FOLLOW y la tabla LL(1) y comprueba que coincidan con `docs/first_follow_tabla.txt`.

Para regenerar la tabla de resultados, las salidas de ejemplo y las páginas de evidencia:

```sh
python -m herramientas.evidencia_parser
```

Para compilar `informe/informe.pdf` hacen falta LuaLaTeX y latexmk (incluidos en TeX Live). El comando convierte las secciones de `docs/` a LaTeX y luego compila:

```sh
python -m herramientas.informe
```

## Estructura

| Ruta                     | Contenido                                                          |
| ------------------------ | ------------------------------------------------------------------ |
| `agroreglas/lexer.py`    | Lexer del docente, extraído de `anlizador_lexico1.ipynb`           |
| `agroreglas/parser.py`   | Parser LL(1) con pila explícita y construcción del AST             |
| `agroreglas/arbol.py`    | Presentación del AST como árbol de texto                           |
| `agroreglas/__main__.py` | Ejecución desde archivo o texto                                    |
| `especificacion/`        | Gramática en JSON y los 25 casos con su resultado esperado         |
| `herramientas/`          | Verificador de la gramática, demostración y generador de evidencia |
| `pruebas/`               | Pruebas automáticas                                                |
| `docs/`                  | Secciones del informe, tablas, resultados y capturas               |
| `informe/`               | Fuente LaTeX e informe final en PDF                                |
| `ejemplos/`              | Programas de ejemplo y el AST del caso V04                         |

## Autores

Fernando, Juanfra y Vicente.
