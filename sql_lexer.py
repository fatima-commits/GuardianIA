"""
Lenguaje 2: analizador léxico de las consultas SQL (PLY lex).

Tokens y sus expresiones regulares
----------------------------------
  Palabras reservadas  SELECT FROM WHERE UPDATE SET DELETE DROP TABLE UNION
                       ORDER BY ASC DESC LIMIT AND OR NOT
                       (sin distinguir mayúsculas y minúsculas)
  ID       [a-zA-Z_][a-zA-Z0-9_]*     letra o guion bajo al inicio
  NUMBER   \\d+(\\.\\d+)?               enteros o decimales con punto
  STRING   '[^'\\n]*'                  entre comillas simples
  LE <=   GE >=   NE <>   EQ =   LT <   GT >
  STAR *  COMMA ,  LPAREN (  RPAREN )  SEMICOLON ;

¿Cómo evitamos que ID absorba las palabras reservadas?
  Las palabras reservadas NO tienen su propia ER. Hay una sola regla t_ID
  que reconoce cualquier identificador y, después, busca el lexema (en
  minúsculas) en el diccionario `reserved`. Si está, cambia el tipo del
  token a la palabra reservada; si no, se queda como ID.
  Así 'SELECT', 'select' y 'SeLeCt' dan el token SELECT, mientras que
  'selection' sigue siendo ID.

Los operadores de dos caracteres (<=, >=, <>) se declaran como cadenas;
PLY ordena esas reglas por longitud decreciente de la ER, así que '<=' se
prueba antes que '<'.
"""

import ply.lex as lex

from errores import ErrorLexico

LENGUAJE = "SQL"

reserved = {
    "select": "SELECT",
    "from": "FROM",
    "where": "WHERE",
    "update": "UPDATE",
    "set": "SET",
    "delete": "DELETE",
    "drop": "DROP",
    "table": "TABLE",
    "union": "UNION",
    "order": "ORDER",
    "by": "BY",
    "asc": "ASC",
    "desc": "DESC",
    "limit": "LIMIT",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
}

tokens = [
    "ID", "NUMBER", "STRING",
    "EQ", "NE", "LT", "GT", "LE", "GE",
    "STAR", "COMMA", "LPAREN", "RPAREN",
    "SEMICOLON",
] + sorted(set(reserved.values()))

t_LE = r"<="
t_GE = r">="
t_NE = r"<>"
t_EQ = r"="
t_LT = r"<"
t_GT = r">"

t_STAR = r"\*"
t_COMMA = r","
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_SEMICOLON = r";"

t_ignore = " \t\r\n"


def t_STRING(t):
    r"'[^'\n]*('|$)"
    # La ER también acepta una cadena que llega al final sin cerrarse
    # para reportarla como "cadena sin cerrar".
    if len(t.value) < 2 or not t.value.endswith("'"):
        raise ErrorLexico(f"la cadena {t.value.rstrip(';')} nunca se cierra",
                          LENGUAJE)
    t.value = t.value[1:-1]
    return t


def t_NUMBER(t):
    r"\d+(\.\d+)?"
    t.value = float(t.value) if "." in t.value else int(t.value)
    return t


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    t.type = reserved.get(t.value.lower(), "ID")
    if t.type == "ID":
        t.value = t.value.lower()
    return t


def t_error(t):
    raise ErrorLexico(f"'{t.value[0]}' no es un símbolo del lenguaje "
                      f"(posición {t.lexpos})", LENGUAJE)


_lexer = lex.lex()


def tokenizar_sql(texto):
    """Regresa la lista de tokens o lanza ErrorLexico."""
    _lexer.input(texto)
    return list(iter(_lexer.token, None))


if __name__ == "__main__":
    for tok in tokenizar_sql("SELECT nombre FROM empleos WHERE ciudad = 'GDL';"):
        print(f"{tok.type:<10} {tok.value!r}")
