"""
Lenguaje 3: analizador sintáctico de las URL (PLY yacc).

Gramática (G_URL)
-----------------
Terminales:
  ESQUEMA SEP USUARIO ETIQUETA NUMERO PUNYCODE DOT COLON SLASH QUESTION
  AMP EQUALS HASH PCT TEXTO

No terminales:
  url, autoridad, host, etiqueta, puerto_opt, ruta_opt, ruta, segmento_opt,
  piezas, pieza, query_opt, parametros, parametro, valor_opt, piezas_q,
  pieza_q, fragmento_opt, piezas_f_opt, piezas_f, pieza_f, empty

Símbolo inicial: url

Producciones:
  url           -> ESQUEMA SEP autoridad ruta_opt query_opt fragmento_opt
  autoridad     -> USUARIO host puerto_opt
                 | host puerto_opt
  host          -> etiqueta DOT etiqueta
                 | host DOT etiqueta
  etiqueta      -> ETIQUETA | NUMERO | PUNYCODE
  puerto_opt    -> COLON NUMERO | empty

  ruta_opt      -> ruta | empty
  ruta          -> SLASH segmento_opt
                 | ruta SLASH segmento_opt
  segmento_opt  -> piezas | empty
  piezas        -> pieza | piezas pieza
  pieza         -> TEXTO | PCT

  query_opt     -> QUESTION parametros | QUESTION | empty
  parametros    -> parametro | parametros AMP parametro
  parametro     -> piezas_q EQUALS valor_opt | piezas_q
  valor_opt     -> piezas_q | empty
  piezas_q      -> pieza_q | piezas_q pieza_q
  pieza_q       -> TEXTO | PCT | SLASH | QUESTION

  fragmento_opt -> HASH piezas_f_opt | empty
  piezas_f_opt  -> piezas_f | empty
  piezas_f      -> pieza_f | piezas_f pieza_f
  pieza_f       -> TEXTO | PCT | SLASH | QUESTION | EQUALS | AMP

  empty         -> ε

¿Por qué la URL "casi" cabe en una expresión regular?
  Ninguna parte de la URL se anida: es una secuencia de componentes
  opcionales. Por eso el lenguaje es regular (se podría describir con una
  sola ER): la gramática anterior no tiene autoanidamiento (ningún no
  terminal se deriva a sí mismo con símbolos a ambos lados, A =>* xAy).
  Lo único que la ER no controla bien son los RANGOS numéricos (octeto
  0-255, puerto 0-65535); eso se valida en la capa semántica.
  Usamos yacc para tener una estructura (host, usuario, puerto...) sobre la
  cual aplicar R5-R7, igual que en SQL.

El host se reconoce como IPv4 cuando tiene exactamente 4 etiquetas NUMERO.
"""

import ply.yacc as yacc

from errores import ErrorSintactico, ErrorSemantico
from ply_comun import LexerDeLista, tokens_esperados
from url_lexer import tokens, tokenizar_url  # noqa: F401

LENGUAJE = "URL"


def p_url(p):
    "url : ESQUEMA SEP autoridad ruta_opt query_opt fragmento_opt"
    usuario, host, puerto = p[3]
    p[0] = {
        "esquema": p[1],
        "usuario": usuario,
        "host": host,                # lista de etiquetas
        "puerto": puerto,
        "ruta": p[4],
        "parametros": p[5],          # lista de (clave, valor)
        "fragmento": p[6],
    }


def p_autoridad(p):
    """autoridad : USUARIO host puerto_opt
                 | host puerto_opt"""
    if len(p) == 4:
        p[0] = (p[1], p[2], p[3])
    else:
        p[0] = (None, p[1], p[2])


def p_host(p):
    """host : etiqueta DOT etiqueta
            | host DOT etiqueta"""
    p[0] = (p[1] if isinstance(p[1], list) else [p[1]]) + [p[3]]


def p_etiqueta(p):
    """etiqueta : ETIQUETA
                | NUMERO
                | PUNYCODE"""
    p[0] = {"tipo": p.slice[1].type, "v": p[1]}


def p_puerto_opt(p):
    """puerto_opt : COLON NUMERO
                  | empty"""
    p[0] = int(p[2]) if len(p) == 3 else None

# ------------------------------- ruta -----------------------------------


def p_ruta_opt(p):
    """ruta_opt : ruta
                | empty"""
    p[0] = p[1]


def p_ruta(p):
    """ruta : SLASH segmento_opt
            | ruta SLASH segmento_opt"""
    if len(p) == 3:
        p[0] = "/" + (p[2] or "")
    else:
        p[0] = p[1] + "/" + (p[3] or "")


def p_segmento_opt(p):
    """segmento_opt : piezas
                    | empty"""
    p[0] = p[1]


def p_piezas(p):
    """piezas : pieza
              | piezas pieza"""
    p[0] = p[1] if len(p) == 2 else p[1] + p[2]


def p_pieza(p):
    """pieza : TEXTO
             | PCT"""
    p[0] = p[1]

# ----------------------------- parámetros -------------------------------


def p_query_opt(p):
    """query_opt : QUESTION parametros
                 | QUESTION
                 | empty"""
    if len(p) == 3:
        p[0] = p[2]
    elif p[1] == "?":
        p[0] = []
    else:
        p[0] = None


def p_parametros(p):
    """parametros : parametro
                  | parametros AMP parametro"""
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_parametro(p):
    """parametro : piezas_q EQUALS valor_opt
                 | piezas_q"""
    p[0] = (p[1], p[3] or "") if len(p) == 4 else (p[1], None)


def p_valor_opt(p):
    """valor_opt : piezas_q
                 | empty"""
    p[0] = p[1]


def p_piezas_q(p):
    """piezas_q : pieza_q
                | piezas_q pieza_q"""
    p[0] = p[1] if len(p) == 2 else p[1] + p[2]


def p_pieza_q(p):
    """pieza_q : TEXTO
               | PCT
               | SLASH
               | QUESTION"""
    p[0] = p[1]

# ------------------------------ fragmento -------------------------------


def p_fragmento_opt(p):
    """fragmento_opt : HASH piezas_f_opt
                     | empty"""
    p[0] = (p[2] or "") if len(p) == 3 else None


def p_piezas_f_opt(p):
    """piezas_f_opt : piezas_f
                    | empty"""
    p[0] = p[1]


def p_piezas_f(p):
    """piezas_f : pieza_f
                | piezas_f pieza_f"""
    p[0] = p[1] if len(p) == 2 else p[1] + p[2]


def p_pieza_f(p):
    """pieza_f : TEXTO
               | PCT
               | SLASH
               | QUESTION
               | EQUALS
               | AMP"""
    p[0] = p[1]


def p_empty(p):
    "empty :"
    p[0] = None

# ------------------------------ errores ---------------------------------


NOMBRES = {
    "ESQUEMA": "el esquema (http o https)", "SEP": "'://'",
    "USUARIO": "usuario@", "ETIQUETA": "una etiqueta de dominio",
    "NUMERO": "un número", "PUNYCODE": "una etiqueta xn--", "DOT": "'.'",
    "COLON": "':'", "SLASH": "'/'", "QUESTION": "'?'", "AMP": "'&'",
    "EQUALS": "'='", "HASH": "'#'", "PCT": "%XX", "TEXTO": "texto",
}


def p_error(tok):
    if tok is None:
        raise ErrorSintactico("la URL está incompleta; se esperaba "
                              + tokens_esperados(_parser, NOMBRES), LENGUAJE)

    # Caso 8 del PDF: "https//bbva.mx"
    if tok.lexpos == 0 and tok.type == "TEXTO":
        v = tok.value.lower()
        if v in ("http", "https"):
            raise ErrorSintactico("falta ':' después del esquema", LENGUAJE)
        if v in ("http:", "https:"):
            raise ErrorSintactico(f"falta '//' después de '{v}'", LENGUAJE)
        raise ErrorSintactico("la URL debe iniciar con http:// o https://",
                              LENGUAJE)

    if tok.type == "USUARIO":
        raise ErrorSintactico("solo puede haber un usuario con '@' antes del host",
                              LENGUAJE)

    raise ErrorSintactico(f"se encontró '{tok.value}' pero se esperaba "
                          + tokens_esperados(_parser, NOMBRES), LENGUAJE)


_parser = yacc.yacc(debug=False, write_tables=False)

# -------------------------------- API -----------------------------------


def analizar_url(texto):
    """
    Lexer -> parser -> validación de rangos.
    Regresa un diccionario con la estructura de la URL:
      esquema, usuario, host (str), etiquetas (list[str]), es_ip,
      puerto, ruta, parametros, fragmento, punycode (bool), pct (bool)
    """
    toks = tokenizar_url(texto)
    if not toks:
        raise ErrorSintactico("la URL está vacía", LENGUAJE)

    datos = _parser.parse(lexer=LexerDeLista(toks))

    etiquetas = datos["host"]
    numericas = [e["tipo"] == "NUMERO" for e in etiquetas]

    # ---- validación de rangos (lo que la ER no controla) ----
    es_ip = all(numericas)
    if es_ip:
        if len(etiquetas) != 4:
            raise ErrorSemantico(f"IPv4 mal formada: tiene {len(etiquetas)} "
                                 "octetos (se esperaban 4)", LENGUAJE)
        for e in etiquetas:
            if not 0 <= int(e["v"]) <= 255:
                raise ErrorSemantico(f"octeto {e['v']} fuera de rango (0 a 255)",
                                     LENGUAJE)
    elif numericas[-1]:
        raise ErrorSemantico("el dominio de nivel superior no puede ser numérico",
                             LENGUAJE)

    puerto = datos["puerto"]
    if puerto is not None and not 0 <= puerto <= 65535:
        raise ErrorSemantico(f"puerto {puerto} fuera de rango (0 a 65535)",
                             LENGUAJE)

    nombres = [e["v"] for e in etiquetas]
    datos.update({
        "etiquetas": nombres,
        "host": ".".join(nombres),
        "es_ip": es_ip,
        "punycode": any(e["tipo"] == "PUNYCODE" for e in etiquetas),
        "pct": any(t.type == "PCT" for t in toks)
                or "%" in (datos["usuario"] or ""),
    })
    return datos


if __name__ == "__main__":
    import pprint
    pprint.pprint(analizar_url("https://bbva.mx@acceso-seguro.xyz/login?id=8821"))
