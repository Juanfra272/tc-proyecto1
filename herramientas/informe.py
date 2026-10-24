"""Compila informe/informe.pdf a partir de las secciones de texto de docs.

Ejecutar desde la raíz: python -m herramientas.informe
Requiere LuaLaTeX y latexmk. Las secciones se convierten en cada compilación,
así el PDF no diverge de los textos que mantiene cada autor.

Formato que reconoce cada archivo .txt: la primera línea es el título; cada
párrafo ocupa una línea; un bloque de varias líneas es una tabla si empieza con
|, una lista si empieza con - y texto literal en otro caso, igual que una línea
con sangría de cuatro espacios.
"""

from pathlib import Path
import re
import subprocess

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "informe"
GENERADO = INFORME / "generado"

ESPECIALES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
              "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
# Rutas, identificadores con guion bajo y opciones de línea de comandos usan fuente de ancho fijo.
CODIGO = re.compile(r"--\w+|[\w./]*(?:_|/|\.(?:py|json|txt|ipynb|agro|html|png|pdf)\b)[\w./]*")


def escapar(texto):
    # \kern0pt evita que la ligadura convierta -- en un guion largo.
    return "".join(ESPECIALES.get(c, c) for c in texto).replace("--", "-\\kern0pt-")


def tt(texto):
    # \allowbreak tras / y _ permite cortar rutas largas en columnas estrechas.
    return r"\texttt{" + escapar(texto).replace("/", r"/\allowbreak{}").replace(r"\_", r"\_\allowbreak{}") + "}"


def en_linea(texto):
    partes = []
    for i, trozo in enumerate(texto.split("`")):
        if i % 2:
            partes.append(tt(trozo))
            continue
        ultimo = 0
        for m in CODIGO.finditer(trozo):
            palabra = m.group().rstrip(".")
            if not re.search(r"[A-Za-z]", palabra) or "/" == palabra:
                continue
            partes.append(escapar(trozo[ultimo:m.start()]) + tt(palabra))
            ultimo = m.start() + len(palabra)
        partes.append(escapar(trozo[ultimo:]))
    return "".join(partes)


def literal(lineas):
    sangria = min(len(l) - len(l.lstrip()) for l in lineas if l.strip())
    cuerpo = "\n".join(l[sangria:] for l in lineas)
    return "\\begin{Verbatim}\n" + cuerpo + "\n\\end{Verbatim}"


def tabla(lineas):
    filas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lineas
             if not re.fullmatch(r"\|[\s\-|]+\|", l.strip())]
    columnas = len(filas[0])
    if columnas > 8:
        # Tabla predictiva: todas las columnas centradas y reducida al ancho de página.
        cuerpo = [" & ".join(r"\rotatebox{90}{" + en_linea(c) + "}" if i and n == 0 else en_linea(c)
                             for i, c in enumerate(f)) + r" \\" for n, f in enumerate(filas)]
        cuerpo.insert(1, r"\midrule")
        return ("\\begin{center}\\footnotesize\\resizebox{\\textwidth}{!}{\\begin{tabular}{l"
                + "c" * (columnas - 1) + "}\n\\toprule\n" + "\n".join(cuerpo)
                + "\n\\bottomrule\n\\end{tabular}}\\end{center}")
    largos = [max(len(f[i]) for f in filas) for i in range(columnas)]
    # Columnas cortas a su ancho natural; las largas reparten el resto según su contenido.
    anchas = [i for i, largo in enumerate(largos) if largo > 14] or [columnas - 1]
    # El mínimo evita que una columna corta parta su encabezado.
    pesos = {i: max(largos[i], 24) for i in anchas}
    total = sum(pesos.values())
    formato = "".join(
        f">{{\\raggedright\\arraybackslash\\hsize={len(anchas) * pesos[i] / total:.2f}\\hsize}}X" if i in anchas else "l"
        for i in range(columnas))
    cuerpo = [" & ".join(en_linea(c) for c in f) + r" \\" for f in filas]
    cuerpo[0] = " & ".join(r"\textbf{" + en_linea(c) + "}" for c in filas[0]) + r" \\" + "\n\\midrule\n\\endhead"
    return ("{\\small\\begin{xltabular}{\\textwidth}{" + formato + "}\n\\toprule\n"
            + "\n".join(cuerpo) + "\n\\bottomrule\n\\end{xltabular}}")


def convertir(ruta, nivel="section", desplazamiento=0):
    """Devuelve el LaTeX y el último número de sección.

    desplazamiento suma a la numeración propia de cada autor para que el informe
    sea continuo; las referencias internas de Fernando no se desplazan.
    """
    bloques = [b.split("\n") for b in re.split(r"\n\s*\n", ruta.read_text(encoding="utf-8").strip())]
    salida = []
    ultimo = desplazamiento
    for i, lineas in enumerate(bloques):
        primera = lineas[0]
        if i == 0:
            continue  # El título lo pone informe.tex.
        if len(lineas) == 1 and primera.startswith("Autoría:"):
            continue  # informe.tex la indica al abrir cada parte.
        elif len(lineas) > 1 and all(l.startswith("|") for l in lineas):
            salida.append(tabla(lineas))
        elif len(lineas) > 1 and all(l.startswith("- ") for l in lineas):
            salida.append("\\begin{itemize}\n" + "\n".join(r"\item " + en_linea(l[2:]) for l in lineas)
                          + "\n\\end{itemize}")
        elif len(lineas) > 1 or primera.startswith(("    ", "python ")):
            salida.append(literal(lineas))
        elif len(primera) < 70 and not primera.endswith((".", ":", ";")):
            comando = "sub" + nivel if re.match(r"\d+\.\d", primera) else nivel
            numero = re.match(r"\d+", primera)
            if numero:
                ultimo = int(numero.group()) + desplazamiento
                primera = str(ultimo) + primera[numero.end():]
            salida.append(f"\\{comando}*{{{en_linea(primera)}}}\n"
                          f"\\addcontentsline{{toc}}{{{comando}}}{{{en_linea(primera)}}}")
        else:
            salida.append(en_linea(primera))
    return "\n\n".join(salida) + "\n", ultimo


def insertar_antes(tex, numero, contenido):
    marca = f"\\section*{{{numero}. "
    assert marca in tex, f"No se encontró la sección {numero}"
    return tex.replace(marca, contenido + "\n\n" + marca, 1)


def main():
    GENERADO.mkdir(exist_ok=True)
    docs = RAIZ / "docs"
    teoria, ultimo = convertir(docs / "teoria.txt")
    tablas, _ = convertir(docs / "first_follow_tabla.txt", nivel="subsection")
    # Las tablas reproducibles completan la sección 6 de Fernando, sobre la tabla LL(1).
    teoria = insertar_antes(teoria, 7, tablas)
    (GENERADO / "teoria.tex").write_text(teoria, encoding="utf-8")

    implementacion, final = convertir(docs / "implementacion.txt", desplazamiento=ultimo)
    # El árbol de V04 ilustra la sección 3 de Juanfra, sobre el AST.
    arbol = (RAIZ / "ejemplos/arbol_v04.txt").read_text(encoding="utf-8").rstrip("\n").split("\n")
    figura = ("AST del caso V04 producido por " + tt("formatear_arbol") + ":\n\n" + literal(arbol))
    implementacion = insertar_antes(implementacion, ultimo + 4, figura)
    (GENERADO / "implementacion.tex").write_text(implementacion, encoding="utf-8")

    integracion, final = convertir(docs / "integracion.txt", desplazamiento=final)
    resultados, _ = convertir(docs / "resultados_casos.txt", nivel="subsection")
    titulo = f"{final + 1}. Resultados de los 25 casos"
    integracion += (f"\n\\section*{{{titulo}}}\n\\addcontentsline{{toc}}{{section}}{{{titulo}}}\n\n"
                    + resultados)
    (GENERADO / "integracion.tex").write_text(integracion, encoding="utf-8")
    subprocess.run(["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error",
                    "-outdir=" + str(INFORME / "build"), "informe.tex"], cwd=INFORME, check=True)
    (INFORME / "informe.pdf").write_bytes((INFORME / "build" / "informe.pdf").read_bytes())
    print("Informe generado en informe/informe.pdf.")


if __name__ == "__main__":
    main()
