"""
Análisis semántico: reglas de riesgo R1 a R8.

Las reglas se aplican SOLO a acciones bien formadas y SIEMPRE sobre la
estructura reconocida (el AST que construyó yacc), nunca buscando texto en
la cadena original. Por ejemplo, R4 cuenta los elementos de la lista de
sentencias del AST; así un ';' dentro de una cadena ('a;b') no la dispara.

Cada regla produce un Riesgo(regla, nivel, mensaje).
  nivel: 'ALTO'  -> BLOQUEAR
         'MEDIO' -> CONFIRMAR
         'MIN_CONFIRMAR' (solo R8) -> al menos CONFIRMAR

Combinación de dictámenes
-------------------------
Se toma el MÁS SEVERO: PERMITIR < CONFIRMAR < BLOQUEAR.
  * SQL: cualquier regla R1-R4 -> BLOQUEAR.
  * URL: sin señales -> PERMITIR; solo riesgo medio -> CONFIRMAR;
         algún riesgo alto -> BLOQUEAR.
  * R8 (origen [documento] o [mensaje]) sube el dictamen a CONFIRMAR si
    estaba en PERMITIR; nunca lo baja.
  * El modo 'congelado' se evalúa dentro de R1.
"""

import re
from collections import namedtuple

Riesgo = namedtuple("Riesgo", "regla nivel mensaje")

SEVERIDAD = {"PERMITIR": 0, "CONFIRMAR": 1, "BLOQUEAR": 2}

MARCAS = ("bbva", "banorte", "santander", "banamex", "iteso", "sat", "imss")

TABLAS_RESTRINGIDAS = ("admins",)

# Sufijos de dos niveles: en 'bbva.com.mx' el dominio principal es
# 'bbva.com.mx', no 'com.mx'.
SUFIJOS_DOBLES = {
    "com.mx", "org.mx", "gob.mx", "edu.mx", "net.mx",
    "co.uk", "com.ar", "com.br", "com.co", "com.es",
}

ORIGENES_EXTERNOS = ("documento", "mensaje")


def mas_severo(a, b):
    return a if SEVERIDAD[a] >= SEVERIDAD[b] else b

# =============================== SQL ====================================


def _texto_valor(valor):
    if valor["clase"] == "STRING":
        return f"'{valor['v']}'"
    return str(valor["v"])


def _tautologias(nodo):
    """Recorre el árbol de la condición y regresa las comparaciones
    entre dos valores FIJOS iguales (1 = 1, 'a' = 'a')."""
    if nodo is None:
        return []
    tipo = nodo["tipo"]
    if tipo in ("AND", "OR"):
        return _tautologias(nodo["izq"]) + _tautologias(nodo["der"])
    if tipo == "NOT":
        return _tautologias(nodo["valor"])
    # COMPARACION
    izq, der, op = nodo["izq"], nodo["der"], nodo["op"]
    fijos = izq["clase"] != "ID" and der["clase"] != "ID"
    if fijos and op in ("=", "<=", ">=") and izq["v"] == der["v"] \
            and izq["clase"] == der["clase"]:
        return [f"{_texto_valor(izq)} {op} {_texto_valor(der)}"]
    return []


def reglas_sql(ast, modo):
    riesgos = []
    sentencias = ast["sentencias"]

    for s in sentencias:
        tipo = s["tipo"]

        # R1: DROP TABLE, DELETE/UPDATE sin WHERE
        if tipo == "DROP":
            riesgos.append(Riesgo("R1", "ALTO",
                                  f"DROP TABLE elimina la tabla '{s['tabla']}'"))
        elif tipo in ("DELETE", "UPDATE") and s["condicion"] is None:
            riesgos.append(Riesgo("R1", "ALTO",
                                  f"{tipo} sin WHERE afecta toda la tabla "
                                  f"'{s['tabla']}'"))

        # R1: modo congelado -> solo SELECT
        if modo == "congelado" and tipo != "SELECT":
            riesgos.append(Riesgo("R1", "ALTO",
                                  f"{tipo} no permitido en modo congelado "
                                  "(solo lectura)"))

        # R2: tautologías en cualquier condición
        if tipo == "SELECT":
            condiciones = [parte["condicion"] for parte in s["partes"]]
        elif tipo in ("UPDATE", "DELETE"):
            condiciones = [s["condicion"]]
        else:
            condiciones = []
        for c in condiciones:
            for t in _tautologias(c):
                riesgos.append(Riesgo("R2", "ALTO",
                                      f"tautología {t} en la condición"))

        # R3: UNION hacia una tabla no permitida
        if tipo == "SELECT" and len(s["partes"]) > 1:
            for parte in s["partes"]:
                if parte["tabla"] in TABLAS_RESTRINGIDAS:
                    riesgos.append(Riesgo("R3", "ALTO",
                                          "UNION hacia la tabla no permitida "
                                          f"'{parte['tabla']}'"))

    # R4: más de una sentencia
    if len(sentencias) > 1:
        riesgos.append(Riesgo("R4", "ALTO",
                              f"{len(sentencias)} sentencias separadas por ';'"))

    return riesgos

# =============================== URL ====================================


def dominio_principal(etiquetas):
    """'www.bbva.com.mx' -> ['bbva', 'com', 'mx']"""
    if len(etiquetas) >= 3 and ".".join(etiquetas[-2:]) in SUFIJOS_DOBLES:
        return etiquetas[-3:]
    return etiquetas[-2:]


def _palabras(texto):
    """Parte un texto en palabras: 'bbva-seguro.mx' -> {'bbva', 'seguro', 'mx'}.
    Se compara por palabra completa para que 'sat' no coincida con
    'satelite'."""
    return set(p for p in re.split(r"[^a-z0-9]+", texto.lower()) if p)


def reglas_url(datos):
    riesgos = []
    usuario = datos["usuario"]
    etiquetas = datos["etiquetas"]

    # R5: usuario con @ antes del host
    if usuario is not None:
        riesgos.append(Riesgo("R5", "ALTO",
                              f"usuario con '@' antes del host; el sitio real "
                              f"es {datos['host']}"))

    # R6: marca en usuario o subdominio, pero no en el dominio principal
    if not datos["es_ip"]:
        principal = dominio_principal(etiquetas)
        subdominios = etiquetas[:len(etiquetas) - len(principal)]
        palabras_principal = _palabras(".".join(principal))
        palabras_fuera = _palabras(".".join(subdominios))
        if usuario:
            palabras_fuera |= _palabras(usuario)
        for marca in MARCAS:
            if marca in palabras_fuera and marca not in palabras_principal:
                riesgos.append(Riesgo("R6", "ALTO",
                                      f"la marca '{marca}' aparece fuera del "
                                      f"dominio principal ({'.'.join(principal)})"))
    elif usuario:
        for marca in MARCAS:
            if marca in _palabras(usuario):
                riesgos.append(Riesgo("R6", "ALTO",
                                      f"la marca '{marca}' aparece en el usuario "
                                      "y el host es una IP"))

    # R7: señales de riesgo medio (una por señal)
    if datos["es_ip"]:
        riesgos.append(Riesgo("R7", "MEDIO",
                              f"IPv4 {datos['host']} en lugar de dominio"))
    if datos["punycode"]:
        riesgos.append(Riesgo("R7", "MEDIO", "dominio con prefijo punycode xn--"))
    if datos["esquema"] == "http":
        riesgos.append(Riesgo("R7", "MEDIO", "esquema http sin cifrado"))
    if datos["puerto"] is not None and datos["puerto"] not in (80, 443):
        riesgos.append(Riesgo("R7", "MEDIO", f"puerto inusual {datos['puerto']}"))

    return riesgos

# ============================ R8 y dictamen ==============================


def regla_origen(origen):
    if origen in ORIGENES_EXTERNOS:
        return [Riesgo("R8", "MIN_CONFIRMAR", f"origen externo [{origen}]")]
    return []


def dictamen(riesgos):
    """El dictamen más severo de todas las reglas que se cumplieron."""
    resultado = "PERMITIR"
    for r in riesgos:
        if r.nivel == "ALTO":
            resultado = mas_severo(resultado, "BLOQUEAR")
        else:  # MEDIO o MIN_CONFIRMAR
            resultado = mas_severo(resultado, "CONFIRMAR")
    return resultado
