
import re

from url_parser import analizar_url
from semantic import dictamen_url


def procesar_archivo(nombre_archivo):

    with open(nombre_archivo, 'r', encoding='utf-8') as archivo:
        lineas = archivo.readlines()

    modo = "normal"

    for linea in lineas:

        linea = linea.strip()

        if not linea:
            continue

        # Leer encabezado
        if linea.startswith("# modo:"):
            modo = linea.split(":")[1].strip().lower()
            continue

        # Identificar origen
        coincidencia = re.match(
            r'^\[(usuario|documento|mensaje)\]\s*(.*)$',
            linea
        )

        if not coincidencia:
            print("ERROR: origen inválido")
            continue

        origen = coincidencia.group(1)
        accion = coincidencia.group(2)

        print("\nAnalizando:", accion)

        try:

            # Identificar herramienta
            llamada = re.fullmatch(
                r'(consultar_bd|abrir_enlace)\s*\("(.*)"\)',
                accion
            )

            if not llamada:
                raise ValueError(
                    "Error léxico o sintáctico en la llamada"
                )

            herramienta = llamada.group(1)
            argumento = llamada.group(2)

            if herramienta == "abrir_enlace":

                datos = analizar_url(argumento)

                resultado, riesgos = dictamen_url(
                    datos,
                    origen
                )

                print("Dictamen:", resultado)

                for riesgo in riesgos:
                    print(" -", riesgo)

            elif herramienta == "consultar_bd":

                print("SQL identificado.")
                print("Modo:", modo)
                print("Origen:", origen)
                print("Pendiente: conectar parser SQL y semántica.")

        except Exception as error:
            print("ERROR:", error)


if __name__ == "__main__":

    procesar_archivo(
        "tests/corpus_semilla.txt"
    )
