"""
Reporte en consola con el formato del enunciado:

Analizando: sesion_03.txt  (modo: normal)
--------------------------------------------------
[1] ✓ PERMITIR   consultar_bd: SELECT nombre, salario FROM empleos ...
[3] ✗ BLOQUEAR   abrir_enlace: https://bbva.mx@acceso-seguro.xyz/login
      R5: usuario con '@' antes del host; el sitio real es acceso-seguro.xyz
[6] ✗ ERROR      consultar_bd: SELECT FROM empleos;
      Error sintáctico (SQL): se esperaba una lista de columnas después de SELECT
Resumen: 2 permitidas, 0 por confirmar, 3 bloqueadas, 1 con error
"""

import os

SIMBOLO = {
    "PERMITIR": "✓",
    "CONFIRMAR": "!",
    "BLOQUEAR": "✗",
    "ERROR": "✗",
}

ANCHO_ACCION = 60


def _recortar(texto, ancho=ANCHO_ACCION):
    texto = " ".join(texto.split())
    return texto if len(texto) <= ancho else texto[:ancho - 4] + " ..."


def encabezado(ruta, modo, avisos=()):
    lineas = [f"Analizando: {os.path.basename(ruta)}  (modo: {modo})"]
    for aviso in avisos:
        lineas.append(f"  Aviso: {aviso}")
    lineas.append("-" * 70)
    return "\n".join(lineas)


def linea_resultado(numero, res):
    if res.herramienta is not None:
        accion = f"{res.herramienta}: {_recortar(res.argumento)}"
    else:
        accion = _recortar(res.texto)

    num = f"[{numero}]"
    salida = [f"{num:<4} {SIMBOLO[res.dictamen]} {res.dictamen:<10} {accion}"]

    if res.error is not None:
        salida.append(f"      {res.error}")
    for r in res.riesgos:
        salida.append(f"      {r.regla}: {r.mensaje}")
    return "\n".join(salida)


def resumen(resultados):
    cuenta = {k: 0 for k in SIMBOLO}
    for r in resultados:
        cuenta[r.dictamen] += 1
    return (f"Resumen: {cuenta['PERMITIR']} permitidas, "
            f"{cuenta['CONFIRMAR']} por confirmar, "
            f"{cuenta['BLOQUEAR']} bloqueadas, "
            f"{cuenta['ERROR']} con error")


def generar(ruta, modo, resultados, avisos=()):
    partes = [encabezado(ruta, modo, avisos)]
    partes += [linea_resultado(i, r) for i, r in enumerate(resultados, 1)]
    partes.append(resumen(resultados))
    return "\n".join(partes)
