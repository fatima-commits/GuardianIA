"""
Guardián de Seguridad para un Agente de IA.

Uso:
    python main.py tests/corpus_semilla.txt
    python main.py tests/*.txt
    python main.py archivo.txt --salida resultados/archivo.txt

Formato del archivo de entrada:
    # modo: normal            <- encabezado (normal | congelado)
    [usuario]  consultar_bd("SELECT ...;")
    [mensaje]  abrir_enlace("https://...")

Los espacios y tabuladores entre elementos se ignoran. Las líneas vacías se
saltan. Después del encabezado, las líneas que empiezan con '#' se tratan
como comentarios (útil para anotar el resultado esperado de cada prueba).
"""

import argparse
import re
import sys

import reporte
from guardian import analizar_accion

MODOS = ("normal", "congelado")
ENCABEZADO = re.compile(r"^#\s*modo\s*:\s*(\S+)\s*$", re.IGNORECASE)


def leer_modo(lineas):
    """
    Busca el encabezado en la primera línea no vacía.
    Regresa (modo, indice_siguiente_linea, avisos).

    Si el encabezado falta o tiene un modo inválido se usa 'congelado':
    ante la duda, el Guardián elige la opción más restrictiva.
    """
    for i, linea in enumerate(lineas):
        if not linea.strip():
            continue
        m = ENCABEZADO.match(linea.strip())
        if not m:
            return "congelado", i, ["falta el encabezado '# modo: ...'; "
                                    "se usa 'congelado' por seguridad"]
        modo = m.group(1).lower()
        if modo not in MODOS:
            return "congelado", i + 1, [f"modo '{m.group(1)}' no reconocido "
                                        "(normal | congelado); se usa "
                                        "'congelado' por seguridad"]
        return modo, i + 1, []
    return "normal", len(lineas), ["el archivo está vacío"]


def procesar_archivo(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        lineas = f.read().splitlines()

    modo, inicio, avisos = leer_modo(lineas)

    resultados = []
    for linea in lineas[inicio:]:
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        resultados.append(analizar_accion(linea, modo))

    return reporte.generar(ruta, modo, resultados, avisos)


def main():
    # Para que ✓ y ✗ se vean bien también en la consola de Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    ap = argparse.ArgumentParser(description="Guardián de Seguridad para un Agente de IA")
    ap.add_argument("archivos", nargs="+", help="archivo(s) de acciones")
    ap.add_argument("--salida", help="guardar también el reporte en este archivo "
                                     "(solo con un archivo de entrada)")
    args = ap.parse_args()

    for i, ruta in enumerate(args.archivos):
        if i:
            print()
        try:
            texto = procesar_archivo(ruta)
        except OSError as e:
            print(f"No se pudo leer '{ruta}': {e.strerror}")
            continue
        print(texto)
        if args.salida and len(args.archivos) == 1:
            with open(args.salida, "w", encoding="utf-8") as f:
                f.write(texto + "\n")


if __name__ == "__main__":
    main()
