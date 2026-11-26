"""
Lenguaje 3: analizador léxico de las URL (PLY lex).

Forma simplificada del proyecto (recorte de RFC 3986, sección 3 / apéndice A):

    esquema://[usuario@]host[:puerto][/ruta][?parametros][#fragmento]

El lexer usa DOS ESTADOS, porque los mismos caracteres significan cosas
distintas según la parte de la URL:

  * 'autoridad' (exclusivo): desde '://' hasta el primer '/', '?' o '#'.
    Aquí se reconocen el usuario, las etiquetas del host y el puerto.
  * 'INITIAL': ruta, parámetros y fragmento.

Tokens y expresiones regulares
------------------------------
Estado INITIAL (inicio, ruta, parámetros, fragmento)
  ESQUEMA   [A-Za-z][A-Za-z0-9+.-]*(?=://)      solo http / https
  SEP       ://                                  -> entra a 'autoridad'
  SLASH     /         QUESTION  \\?        AMP  &       EQUALS  =
  HASH      \\#
  PCT       %[0-9A-Fa-f]{2}                      codificación %XX
  TEXTO     [A-Za-z0-9._~!$'()*+,;:@-]+          (RFC 3986: unreserved,
                                                 sub-delims, ':' y '@')
Estado 'autoridad'
  USUARIO   [^/?#@\\s]+@                          "todo lo que va antes de @"
  ETIQUETA  [A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?
            -> se reclasifica como NUMERO  si son solo dígitos
            -> se reclasifica como PUNYCODE si empieza con xn--
  DOT       \\.        COLON  :
  SLASH / QUESTION / HASH  -> regresan al estado INITIAL

Los RANGOS (octetos 0-255, puerto 0-65535) no se controlan aquí: una ER
que los controle sería enorme e ilegible; se validan en la capa semántica.
"""

import ply.lex as lex

from errores import ErrorLexico

LENGUAJE = "URL"

ESQUEMAS_PERMITIDOS = ("http", "https")

states = (("autoridad", "exclusive"),)

tokens = (
    "ESQUEMA", "SEP",
    "USUARIO", "ETIQUETA", "NUMERO", "PUNYCODE", "DOT", "COLON",
    "SLASH", "QUESTION", "AMP", "EQUALS", "HASH", "PCT", "TEXTO",
)

# ------------------------------ INITIAL ---------------------------------


def t_ESQUEMA(t):
    r"[A-Za-z][A-Za-z0-9+.-]*(?=://)"
    t.value = t.value.lower()
    if t.value not in ESQUEMAS_PERMITIDOS:
        raise ErrorLexico(f"esquema no permitido '{t.value}' "
                          "(solo http y https)", LENGUAJE)
    return t


def t_SEP(t):
    r"://"
    t.lexer.begin("autoridad")
    return t


t_SLASH = r"/"
t_QUESTION = r"\?"
t_AMP = r"&"
t_EQUALS = r"="
t_HASH = r"\#"


def t_PCT(t):
    r"%[0-9A-Fa-f]{2}"
    t.value = t.value.upper()
    return t


t_TEXTO = r"[A-Za-z0-9._~!$'()*+,;:@-]+"


def t_error(t):
    if t.value[0] == "%":
        raise ErrorLexico(f"codificación %XX inválida '{t.value[:3]}'", LENGUAJE)
    raise ErrorLexico(f"carácter no válido '{t.value[0]}' en la URL "
                      f"(posición {t.lexpos})", LENGUAJE)

# ----------------------------- autoridad --------------------------------


def t_autoridad_USUARIO(t):
    r"[^/?\#@\s]+@"
    t.value = t.value[:-1]
    return t


def t_autoridad_ETIQUETA(t):
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    t.value = t.value.lower()
    if t.value.isdigit():
        t.type = "NUMERO"
    elif t.value.startswith("xn--"):
        t.type = "PUNYCODE"
    return t


t_autoridad_DOT = r"\."
t_autoridad_COLON = r":"


def t_autoridad_SLASH(t):
    r"/"
    t.lexer.begin("INITIAL")
    return t


def t_autoridad_QUESTION(t):
    r"\?"
    t.lexer.begin("INITIAL")
    return t


def t_autoridad_HASH(t):
    r"\#"
    t.lexer.begin("INITIAL")
    return t


def t_autoridad_error(t):
    raise ErrorLexico(f"carácter no válido '{t.value[0]}' en el host "
                      f"(posición {t.lexpos})", LENGUAJE)


t_ignore = ""
t_autoridad_ignore = ""

_lexer = lex.lex()


def tokenizar_url(texto):
    _lexer.begin("INITIAL")
    _lexer.input(texto)
    return list(iter(_lexer.token, None))


if __name__ == "__main__":
    for tok in tokenizar_url("https://bbva.mx@acceso-seguro.xyz:8081/login?id=8821#x"):
        print(f"{tok.type:<10} {tok.value!r}")
