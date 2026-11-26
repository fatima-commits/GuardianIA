
import re

MARCAS = [
    "bbva",
    "banorte",
    "santander",
    "banamex",
    "iteso",
    "sat",
    "imss"
]

def severidad_actual(dictamen):
    niveles = {
        "PERMITIR": 0,
        "CONFIRMAR": 1,
        "BLOQUEAR": 2
    }

    return niveles[dictamen]


def combinar_dictamen(actual, nuevo):
    if severidad_actual(nuevo) > severidad_actual(actual):
        return nuevo

    return actual


# Reglas SQL
def analizar_sql_semantico(ast, modo, texto):

    riesgos = []

    tipo = ast['tipo']
    tabla = ast.get('tabla')
    condicion = ast.get('condicion')

    # R1: DROP, DELETE o UPDATE sin WHERE
    if tipo == 'DROP':
        riesgos.append("R1: DROP TABLE")

    if tipo in ('DELETE', 'UPDATE') and condicion is None:
        riesgos.append("R1: operación sin WHERE")

    # R1: modo congelado
    if modo == 'congelado' and tipo != 'SELECT':
        riesgos.append(
            "R1: operación distinta de SELECT en modo congelado"
        )

    # R2: tautologías
    def buscar_tautologia(nodo):

        if not isinstance(nodo, dict):
            return False

        if nodo.get('tipo') == 'COMPARACION':

            izquierda = nodo.get('izquierda')
            derecha = nodo.get('derecha')
            operador = nodo.get('operador')

            if operador == 'EQ' and izquierda == derecha:
                return isinstance(izquierda, (int, float, str))

        if nodo.get('tipo') in ('AND', 'OR'):
            return (
                buscar_tautologia(nodo.get('izquierda')) or
                buscar_tautologia(nodo.get('derecha'))
            )

        if nodo.get('tipo') == 'NOT':
            return buscar_tautologia(nodo.get('valor'))

        return False

    if buscar_tautologia(condicion):
        riesgos.append("R2: tautología en la condición")

    # R3: UNION hacia admins
    if re.search(
        r'\bUNION\b[\s\S]*?\bFROM\s+admins\b',
        texto,
        re.IGNORECASE
    ):
        riesgos.append("R3: UNION consulta la tabla admins")

    # R4: varias sentencias
    if len([x for x in texto.split(';') if x.strip()]) > 1:
        riesgos.append("R4: varias sentencias SQL")

    return riesgos


# Reglas URL
def analizar_url_semantico(datos):

    riesgos_altos = []
    riesgos_medios = []

    esquema = datos['esquema']
    usuario = datos['usuario']
    host = datos['host']
    puerto = datos['puerto']
    es_ip = datos['es_ip']

    etiquetas = host.split('.')

    # R5: usuario antes de @
    if usuario is not None:
        riesgos_altos.append(
            "R5: existe un usuario antes de @"
        )

    # R6: marcas en usuario o subdominio
    host_principal = '.'.join(etiquetas[-2:])
    subdominios = etiquetas[:-2]

    for marca in MARCAS:

        marca_en_usuario = (
            usuario is not None and
            marca in usuario.lower()
        )

        marca_en_subdominio = any(
            marca in etiqueta.lower()
            for etiqueta in subdominios
        )

        marca_en_dominio_principal = (
            marca in host_principal.lower()
        )

        if (
            (marca_en_usuario or marca_en_subdominio)
            and not marca_en_dominio_principal
        ):
            riesgos_altos.append(
                f"R6: marca sospechosa '{marca}' fuera "
                "del dominio principal"
            )

    # R7: señales de riesgo medio
    if es_ip:
        riesgos_medios.append("R7: utiliza una dirección IPv4")

    if any(etiqueta.startswith('xn--') for etiqueta in etiquetas):
        riesgos_medios.append("R7: dominio con prefijo xn--")

    if esquema == 'http':
        riesgos_medios.append("R7: utiliza HTTP sin cifrado")

    if puerto is not None and puerto not in (80, 443):
        riesgos_medios.append(
            f"R7: puerto inusual ({puerto})"
        )

    return riesgos_altos, riesgos_medios


def dictamen_url(datos, origen):

    altos, medios = analizar_url_semantico(datos)

    dictamen = "PERMITIR"

    if medios:
        dictamen = "CONFIRMAR"

    if altos:
        dictamen = "BLOQUEAR"

    # R8
    if origen in ("documento", "mensaje"):
        dictamen = combinar_dictamen(
            dictamen,
            "CONFIRMAR"
        )

    return dictamen, altos + medios
