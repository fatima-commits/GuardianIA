"""
Lenguaje 1: la llamada a herramienta.

    [origen]   herramienta("argumento")

Ejemplo:
    [usuario]    consultar_bd("SELECT nombre FROM empleos;")

Tokens (expresiones regulares)
------------------------------
  ORIGEN       \\[(usuario|documento|mensaje)\\]
  HERRAMIENTA  consultar_bd | abrir_enlace      (palabras reservadas)
  LPAREN       \\(
  RPAREN       \\)
  COMMA        ,
  CADENA       "[^"\\n]*"   (si llega al final sin '"' -> cadena sin cerrar)
  ID           [A-Za-z_][A-Za-z0-9_]*           (solo para dar buenos
                                                mensajes de error)

Gramática (G_llamada)
---------------------
  Terminales:     ORIGEN, HERRAMIENTA, LPAREN, RPAREN, CADENA, COMMA, ID
  No terminales:  accion
  Símbolo inicial: accion
  Producciones:
      accion -> ORIGEN HERRAMIENTA LPAREN CADENA RPAREN

COMMA e ID no aparecen en ninguna producción a propósito: si aparecen en la
entrada provocan un error sintáctico ("varios argumentos", "argumento con
nombre") en lugar de un error léxico, que es la clasificación correcta.
"""

import ply.lex as lex
import ply.yacc as yacc

from errores import ErrorLexico, ErrorSintactico
from automata import validar_anidamiento
from ply_comun import LexerDeLista, LogSinTokensNoUsados, tokens_esperados

LENGUAJE = "llamada"

ORIGENES = ("usuario", "documento", "mensaje")

reserved = {
    "consultar_bd": "HERRAMIENTA",
    "abrir_enlace": "HERRAMIENTA",
}

tokens = ("ORIGEN", "HERRAMIENTA", "LPAREN", "RPAREN", "COMMA", "CADENA", "ID")

t_ignore = " \t\r\n"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_COMMA = r","


def t_ORIGEN(t):
    r"\[[^\]\s]*\]"
    nombre = t.value[1:-1].lower()
    if nombre not in ORIGENES:
        raise ErrorLexico(f"origen no reconocido '{t.value}' "
                          "(se esperaba [usuario], [documento] o [mensaje])",
                          LENGUAJE)
    t.value = nombre
    return t


def t_CADENA(t):
    r'"[^"\n]*("|$)'
    # La ER acepta también la cadena que llega al final sin cerrarse, para
    # poder reportarla con un mensaje claro en vez de "carácter no válido".
    if len(t.value) < 2 or not t.value.endswith('"'):
        raise ErrorLexico("el argumento entre comillas dobles nunca se cierra",
                          LENGUAJE)
    t.value = t.value[1:-1]
    return t


def t_ID(t):
    r"[A-Za-z_][A-Za-z0-9_]*"
    if t.value in reserved:
        t.type = "HERRAMIENTA"
        return t
    # Un identificador seguido de '(' intenta ser una herramienta
    resto = t.lexer.lexdata[t.lexer.lexpos:].lstrip()
    if resto.startswith("("):
        raise ErrorLexico(f"herramienta no reconocida '{t.value}'", LENGUAJE)
    return t


def t_error(t):
    raise ErrorLexico(f"carácter no válido '{t.value[0]}' "
                      f"(posición {t.lexpos})", LENGUAJE)


_lexer = lex.lex()

# --------------------------- gramática ---------------------------------

def p_accion(p):
    "accion : ORIGEN HERRAMIENTA LPAREN CADENA RPAREN"
    p[0] = {"origen": p[1], "herramienta": p[2], "argumento": p[4]}


NOMBRES = {
    "ORIGEN": "la etiqueta de origen ([usuario], [documento] o [mensaje])",
    "HERRAMIENTA": "una herramienta (consultar_bd o abrir_enlace)",
    "LPAREN": "'('",
    "RPAREN": "')'",
    "CADENA": "un argumento entre comillas dobles",
}


def p_error(tok):
    if tok is None:
        raise ErrorSintactico("la acción está incompleta; se esperaba "
                              + tokens_esperados(_parser, NOMBRES), LENGUAJE)
    if tok.type == "COMMA":
        raise ErrorSintactico("la herramienta recibe un solo argumento", LENGUAJE)
    if tok.type == "HERRAMIENTA" and _anterior_es_paren(tok):
        raise ErrorSintactico("llamadas anidadas no permitidas", LENGUAJE)
    if tok.type == "ID":
        raise ErrorSintactico(f"se encontró '{tok.value}' pero se esperaba "
                              + tokens_esperados(_parser, NOMBRES)
                              + " (no se permiten argumentos con nombre)",
                              LENGUAJE)
    raise ErrorSintactico(f"se encontró '{tok.value}' pero se esperaba "
                          + tokens_esperados(_parser, NOMBRES), LENGUAJE)


def _anterior_es_paren(tok):
    return tok.lexer.lexdata[:tok.lexpos].rstrip().endswith("(")


_parser = yacc.yacc(debug=False, write_tables=False,
                     errorlog=LogSinTokensNoUsados())

# --------------------------- API ---------------------------------------


def tokenizar_llamada(texto):
    _lexer.input(texto)
    return list(iter(_lexer.token, None))


def analizar_llamada(texto):
    """
    Regresa {'origen', 'herramienta', 'argumento'} o lanza
    ErrorLexico / ErrorSintactico.
    """
    toks = tokenizar_llamada(texto)

    if not toks or toks[0].type != "ORIGEN":
        raise ErrorSintactico("falta la etiqueta de origen al inicio de la línea",
                              LENGUAJE)

    ok, _traza, msg = validar_anidamiento([t.type for t in toks])
    if not ok:
        raise ErrorSintactico(msg, LENGUAJE)

    return _parser.parse(lexer=LexerDeLista(toks))
