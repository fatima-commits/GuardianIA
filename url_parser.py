
import re
import ipaddress

URL_PATTERN = re.compile(
    r'^(https?)://'
    r'([^/@?#]+@)?'
    r'([^/:?#]+)'
    r'(?::(\d+))?'
    r'(/[^?#]*)?'
    r'(\?[^#]*)?'
    r'(#[^\s]*)?$',
    re.IGNORECASE
)

def analizar_url(url):

    coincidencia = URL_PATTERN.fullmatch(url)

    if not coincidencia:
        raise ValueError("Error sintáctico: URL mal formada")

    esquema, usuario, host, puerto, ruta, parametros, fragmento = (
        coincidencia.groups()
    )

    # Validar si el host es IPv4
    es_ip = False

    try:
        ipaddress.IPv4Address(host)
        es_ip = True
    except ValueError:
        # Si contiene puntos y solo números, podría ser
        # una IPv4 fuera del rango permitido.
        if re.fullmatch(r'[0-9.]+', host):
            raise ValueError("IPv4 inválida")

    # Validar dominio
    if not es_ip:
        etiquetas = host.split('.')

        if len(etiquetas) < 2:
            raise ValueError("Dominio inválido")

        patron_etiqueta = re.compile(
            r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)$'
        )

        if not all(patron_etiqueta.fullmatch(e) for e in etiquetas):
            raise ValueError("Dominio inválido")

    # Validar puerto
    if puerto is not None:
        numero_puerto = int(puerto)

        if not 0 <= numero_puerto <= 65535:
            raise ValueError("Puerto fuera de rango")

    return {
        'esquema': esquema.lower(),
        'usuario': usuario[:-1] if usuario else None,
        'host': host.lower(),
        'puerto': int(puerto) if puerto else None,
        'ruta': ruta,
        'parametros': parametros,
        'fragmento': fragmento,
        'es_ip': es_ip
    }
